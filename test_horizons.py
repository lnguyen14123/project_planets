import requests
import re
from datetime import datetime, timezone, timedelta

KM_PER_AU = 149_597_870.7

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
    "Churyumov–Geras.":  "90000772",  # Rosetta mission comet
    "Encke":             "90000035",
}


def parse_xyz(result_text):
    soe_index = result_text.find("$$SOE")
    eoe_index = result_text.find("$$EOE")
    if soe_index == -1 or eoe_index == -1:
        return None
    data_block = result_text[soe_index:eoe_index]

    x = re.search(r"X\s*=\s*([-\d.E+]+)", data_block)
    y = re.search(r"Y\s*=\s*([-\d.E+]+)", data_block)
    z = re.search(r"Z\s*=\s*([-\d.E+]+)", data_block)
    vx = re.search(r"VX\s*=\s*([-\d.E+]+)", data_block)
    vy = re.search(r"VY\s*=\s*([-\d.E+]+)", data_block)
    vz = re.search(r"VZ\s*=\s*([-\d.E+]+)", data_block)

    if x and y and z:
        coords = {
            "x_au":  float(x.group(1)) / KM_PER_AU,
            "y_au":  float(y.group(1)) / KM_PER_AU,
            "z_au":  float(z.group(1)) / KM_PER_AU,
        }
        # Velocity is already in km/s, no conversion needed
        if vx and vy and vz:
            coords["vx_kms"] = float(vx.group(1))
            coords["vy_kms"] = float(vy.group(1))
            coords["vz_kms"] = float(vz.group(1))
            # Total speed
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

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None


def poll_objects(objects, object_type):
    """Poll any dict of {name: command_id} from Horizons."""
    results = []
    for name, cmd in objects.items():
        data = query_horizons(cmd)
        if data and "result" in data:
            # Check for error in response
            if "error" in data:
                print(f"❌ {name:<25} | API error")
                continue

            coords = parse_xyz(data["result"])
            if coords:
                dist = (coords["x_au"]**2 + coords["y_au"]
                        ** 2 + coords["z_au"]**2) ** 0.5
                record = {
                    "target_name":      name,
                    "object_type":      object_type,
                    "timestamp":        datetime.now(timezone.utc).isoformat(),
                    "x_au":             round(coords["x_au"], 6),
                    "y_au":             round(coords["y_au"], 6),
                    "z_au":             round(coords["z_au"], 6),
                    "dist_from_sun_au": round(dist, 6),
                    "speed_kms":        coords.get("speed_kms", None)
                }
                results.append(record)
                speed_str = f"{coords['speed_kms']} km/s" if coords.get(
                    "speed_kms") else "n/a"
                print(f"✅ {name:<25} | {dist:.3f} AU | 🚀 {speed_str}")
            else:
                print(f"❌ {name:<25} | Failed to parse")
        else:
            print(f"❌ {name:<25} | API call failed")
    return results


def test_object(name, cmd):
    data = query_horizons(cmd)
    if data and "result" in data:
        print(f"\n--- {name} ({cmd}) ---")
        # Print the target body line
        for line in data["result"].split("\n"):
            if "Target body name" in line:
                print(line)
                break


def search_horizons(name):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    params = {
        "format":   "json",
        "COMMAND":  f"'{name}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "NO"
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        print(f"\n--- Search: {name} ---")
        print(r.json().get("result", "")[:800])


if __name__ == "__main__":
    # print("🪐 Planets\n" + "─"*50)
    # planets = poll_objects(PLANETS, "planet")

    # print("\n☄️  Comets\n" + "─"*50)
    # comets = poll_objects(COMETS, "comet")

    # all_objects = planets + comets
    # print(f"\n🌌 Total: {len(all_objects)} objects pulled successfully!")

    # # Print speed leaderboard
    # sorted_by_speed = sorted(
    #     [o for o in all_objects if o["speed_kms"]],
    #     key=lambda x: x["speed_kms"], reverse=True
    # )
    # print("\n🏆 Speed Leaderboard (km/s):")
    # print("─"*40)
    # for obj in sorted_by_speed:
    #     bar = "█" * int(obj["speed_kms"] / 3)
    #     print(f"  {obj['target_name']:<25} {obj['speed_kms']:>7} km/s  {bar}")

    search_horizons("Hale-Bopp")
    search_horizons("Churyumov-Gerasimenko")
