import json
import base64
import boto3
import math
from datetime import datetime, timezone

s3 = boto3.client("s3")
BUCKET = "solar-tracker-lnguyen"


def enrich_record(record):
    """Add computed fields to each position record."""

    # Distance from Sun (already computed but recalculate to verify)
    dist = math.sqrt(
        record["x_au"]**2 +
        record["y_au"]**2 +
        record["z_au"]**2
    )

    # Heliocentric longitude (angle in degrees around the Sun, top-down view)
    longitude = math.degrees(math.atan2(record["y_au"], record["x_au"]))
    if longitude < 0:
        longitude += 360

    # Rough distance from Earth
    earth_x, earth_y = -0.948, 0.289  # approximate, good enough
    dist_from_earth = math.sqrt(
        (record["x_au"] - earth_x)**2 +
        (record["y_au"] - earth_y)**2
    )

    # Light travel time from Sun (light takes 8.3 min to reach Earth at 1 AU)
    light_travel_min = round(dist * 8.317, 2)

    record["dist_from_sun_au"] = round(dist, 6)
    record["helio_longitude_deg"] = round(longitude, 3)
    record["dist_from_earth_au"] = round(dist_from_earth, 6)
    record["light_travel_min"] = light_travel_min
    record["processed_at"] = datetime.now(timezone.utc).isoformat()

    return record


def lambda_handler(event, context):
    processed = []
    errors = []

    for kinesis_record in event["Records"]:
        try:
            # Decode base64 Kinesis payload
            raw = base64.b64decode(kinesis_record["kinesis"]["data"])
            record = json.loads(raw)

            # Enrich it
            enriched = enrich_record(record)
            processed.append(enriched)

            # Save to S3 under processed/
            now = datetime.now(timezone.utc)
            key = (
                f"processed/"
                f"{enriched['object_type']}/"
                f"{enriched['target_name'].replace(' ', '_')}/"
                f"{now.strftime('%Y/%m/%d/%H%M%S')}.json"
            )
            s3.put_object(
                Bucket=BUCKET,
                Key=key,
                Body=json.dumps(enriched),
                ContentType="application/json"
            )

        except Exception as e:
            errors.append(str(e))

    print(f"✅ Processed: {len(processed)} | ❌ Errors: {len(errors)}")
    if errors:
        print(f"Errors: {errors}")

    return {
        "statusCode": 200,
        "processed":  len(processed),
        "errors":     len(errors)
    }
