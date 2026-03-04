import requests
import re
import boto3
import json
from datetime import datetime, timezone, timedelta

KM_PER_AU = 149_597_870.7
REGION = "us-west-2"
STREAM = "solar-system-positions"
BUCKET = "solar-tracker-lnguyen"

PLANETS = {
    "Mercury": "199",
    "Venus":   "299",
    "Earth":   "399",
    "Mars":    "499",
    "Jupiter": "599",
    "Saturn":  "699",
    "Uranus":  "799",
    "Neptune": "899"
}

COMETS = {
    "Halley":            "90000030",
    "Hale-Bopp":         "90000765",
    "Churyumov-Geras.":  "90000772",
    "Encke":             "90000035",
}

# AWS clients
kinesis = boto3.client("kinesis", region_name=REGION)
s3 = boto3.client("s3",      region_name=REGION)


def parse_xyz(result_text):
    soe_index = result_text.find("$$SOE")
    eoe_index = result_text.find("$$EOE")
    if soe_index == -1 or eoe_index == -1:
        return None
    data_block = result_text[soe_index:eoe_index]
    x = re.search(r"X\s*=\s*([-\d.E+]+)",  data_block)
    y = re.search(r"Y\s*=\s*([-\d.E+]+)",  data_block)
    z = re.search(r"Z\s*=\s*([-\d.E+]+)",  data_block)
    vx = re.search(r"VX\s*=\s*([-\d.E+]+)", data_block)
    vy = re.search(r"VY\s*=\s*([-\d.E+]+)", data_block)
    vz = re.search(r"VZ\s*=\s*([-\d.E+]+)", data_block)
    if x and y and z:
        coords = {
            "x_au": float(x.group(1)) / KM_PER_AU,
            "y_au": float(y.group(1)) / KM_PER_AU,
            "z_au": float(z.group(1)) / KM_PER_AU,
        }
        if vx and vy and vz:
            coords["vx_kms"] = float(vx.group(1))
            coords["vy_kms"] = float(vy.group(1))
            coords["vz_kms"] = float(vz.group(1))
            coords["speed_kms"] = round(
                (coords["vx_kms"]**2 + coords["vy_kms"]
                 ** 2 + coords["vz_kms"]**2) ** 0.5, 3
            )
        return coords
    return None


def query_horizons(command_id):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    now = datetime.now(timezone.utc)
    start = now.strftime("%Y-%m-%d %H:%M")
    stop = (now + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
    params = {
        "format":     "json",
        "COMMAND":    command_id,
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER":     "500@10",
        "START_TIME": f"'{start}'",
        "STOP_TIME":  f"'{stop}'",
        "STEP_SIZE":  "1m",
        "OBJ_DATA":   "NO",
        "VEC_TABLE":  "2"
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    return None


def build_record(name, object_type, coords):
    """Build a clean record dict ready for Kinesis + S3."""
    dist = (coords["x_au"]**2 + coords["y_au"]**2 + coords["z_au"]**2) ** 0.5
    return {
        "target_name":       name,
        "object_type":       object_type,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "x_au":              round(coords["x_au"],   6),
        "y_au":              round(coords["y_au"],   6),
        "z_au":              round(coords["z_au"],   6),
        "dist_from_sun_au":  round(dist,             6),
        "speed_kms":         coords.get("speed_kms", None)
    }


def push_to_kinesis(record):
    """Send one record to Kinesis stream."""
    kinesis.put_record(
        StreamName=STREAM,
        Data=json.dumps(record),
        PartitionKey=record["target_name"]
    )


def save_to_s3(all_records):
    """Save all records as a JSON file to S3."""
    now = datetime.now(timezone.utc)
    key = f"raw/{now.strftime('%Y/%m/%d/%H%M')}/snapshot.json"
    payload = json.dumps(all_records)

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=payload,
        ContentType="application/json"
    )
    print(f"💾 Saved to s3://{BUCKET}/{key}")


def poll_and_push():
    print(
        f"🚀 Starting pipeline — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("─" * 55)

    all_records = []

    # Poll planets
    print("🪐 Planets:")
    for name, cmd in PLANETS.items():
        data = query_horizons(cmd)
        if data and "result" in data and "error" not in data:
            coords = parse_xyz(data["result"])
            if coords:
                record = build_record(name, "planet", coords)
                push_to_kinesis(record)
                all_records.append(record)
                print(
                    f"  ✅ {name:<12} | {record['dist_from_sun_au']:.3f} AU | {record['speed_kms']} km/s → Kinesis ✅")
            else:
                print(f"  ❌ {name:<12} | parse failed")
        else:
            print(f"  ❌ {name:<12} | API failed")

    # Poll comets
    print("☄️  Comets:")
    for name, cmd in COMETS.items():
        data = query_horizons(cmd)
        if data and "result" in data and "error" not in data:
            coords = parse_xyz(data["result"])
            if coords:
                record = build_record(name, "comet", coords)
                push_to_kinesis(record)
                all_records.append(record)
                print(
                    f"  ✅ {name:<22} | {record['dist_from_sun_au']:.3f} AU | {record['speed_kms']} km/s → Kinesis ✅")
            else:
                print(f"  ❌ {name:<22} | parse failed")
        else:
            print(f"  ❌ {name:<22} | API failed")

    # Save full snapshot to S3
    print("─" * 55)
    save_to_s3(all_records)
    print(
        f"🌌 Done! {len(all_records)} objects pushed to Kinesis + saved to S3")


def lambda_handler(event, context):
    """Entry point for EventBridge scheduled trigger."""
    poll_and_push()
    return {"statusCode": 200, "body": "Pipeline complete!"}


# if __name__ == "__main__":
#     poll_and_push()
