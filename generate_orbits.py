import requests
import re
import csv
from datetime import datetime, timezone

KM_PER_AU = 149_597_870.7

PLANETS = {
    "Mercury": ("199", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Venus":   ("299", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Earth":   ("399", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Mars":    ("499", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Jupiter": ("599", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Saturn":  ("699", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Uranus":  ("799", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Neptune": ("899", "1995-Jan-01", "2026-Jan-01", "20d"),
}

COMETS = {
    "Halley":           ("90000030", "1995-Jan-01", "2062-Jan-01", "20d"),
    "Hale-Bopp":        ("90000765", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Churyumov-Geras.": ("90000772", "1995-Jan-01", "2026-Jan-01", "20d"),
    "Encke":            ("90000035", "1995-Jun-01", "2026-Jan-01", "20d"),
}


def query_orbit(name, command_id, start, stop, step):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    params = {
        "format":     "json",
        "COMMAND":    command_id,
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER":     "500@10",
        "START_TIME": f"'{start}'",
        "STOP_TIME":  f"'{stop}'",
        "STEP_SIZE":  step,
        "OBJ_DATA":   "NO",
        "VEC_TABLE":  "2"
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    return None


def parse_all_positions(result_text, name, object_type):

    soe_index = result_text.find("$$SOE")
    eoe_index = result_text.find("$$EOE")
    if soe_index == -1 or eoe_index == -1:
        return []

    block = result_text[soe_index:eoe_index]
    lines = block.split("\n")
    records = []
    date_str = None

    for line in lines:
        # Date line looks like: 2461103.5 = A.D. 2026-Mar-04 ...
        if "A.D." in line:
            try:
                raw_date = line.split("A.D.")[1].strip().split()[0]
                try:
                    date_str = datetime.strptime(
                        raw_date, "%Y-%b-%d").strftime("%m/%d/%Y")
                except:
                    date_str = raw_date
            except:
                date_str = None

        # Position line
        if "X =" in line and "Y =" in line:
            x = re.search(r"X\s*=\s*([-\d.E+]+)", line)
            y = re.search(r"Y\s*=\s*([-\d.E+]+)", line)
            z = re.search(r"Z\s*=\s*([-\d.E+]+)", line)
            if x and y and z and date_str:
                x_au = float(x.group(1)) / KM_PER_AU
                y_au = float(y.group(1)) / KM_PER_AU
                z_au = float(z.group(1)) / KM_PER_AU
                dist = (x_au**2 + y_au**2 + z_au**2) ** 0.5
                records.append({
                    "target_name":       name,
                    "object_type":       object_type,
                    "date":              date_str,
                    "x_au":              round(x_au, 6),
                    "y_au":              round(y_au, 6),
                    "z_au":              round(z_au, 6),
                    "dist_from_sun_au":  round(dist, 6),
                })
    return records


def generate_orbit_data():
    all_records = []

    print("🪐 Fetching planet orbits...")
    for name, (cmd, start, stop, step) in PLANETS.items():
        print(f"  fetching {name} ({start} → {stop}, every {step})...")
        data = query_orbit(name, cmd, start, stop, step)
        if data and "result" in data:
            records = parse_all_positions(data["result"], name, "planet")
            all_records.extend(records)
            print(f"  ✅ {name} — {len(records)} points")
        else:
            print(f"  ❌ {name} failed")

    print("\n☄️  Fetching comet orbits...")
    for name, (cmd, start, stop, step) in COMETS.items():
        print(f"  fetching {name} ({start} → {stop}, every {step})...")
        data = query_orbit(name, cmd, start, stop, step)
        if data and "result" in data:
            records = parse_all_positions(data["result"], name, "comet")
            all_records.extend(records)
            print(f"  ✅ {name} — {len(records)} points")
        else:
            print(f"  ❌ {name} failed")

    # Save to CSV
    if all_records:
        filename = "orbit_data_past.csv"
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
            writer.writeheader()
            writer.writerows(all_records)
        print(f"\n✅ Saved {len(all_records)} orbit points to {filename}!")

    return all_records


if __name__ == "__main__":
    generate_orbit_data()
