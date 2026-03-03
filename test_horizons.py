import requests
import re
from datetime import datetime, timezone, timedelta


def parse_xyz(result_text):
    """Extract X, Y, Z position values from Horizons response text."""

    # Find the $$SOE (Start Of Ephemeris) section
    soe_index = result_text.find("$$SOE")
    eoe_index = result_text.find("$$EOE")

    if soe_index == -1 or eoe_index == -1:
        print("❌ Couldn't find ephemeris data block")
        return None

    # Grab just the data between $$SOE and $$EOE
    data_block = result_text[soe_index:eoe_index]
    print(f"\n--- Data block ---\n{data_block}\n")

    # Extract X, Y, Z using regex
    x = re.search(r"X\s*=\s*([-\d.E+]+)", data_block)
    y = re.search(r"Y\s*=\s*([-\d.E+]+)", data_block)
    z = re.search(r"Z\s*=\s*([-\d.E+]+)", data_block)

    if x and y and z:
        return {
            "x_au": float(x.group(1)),
            "y_au": float(y.group(1)),
            "z_au": float(z.group(1))
        }
    else:
        print("❌ Couldn't parse X Y Z values")
        return None


def test_horizons(planet_name, command_id):
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

    print(f"🔭 Querying NASA Horizons for {planet_name}...")
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        coords = parse_xyz(data["result"])

        if coords:
            print(f"✅ {planet_name} position (AU from Sun):")
            print(f"   X: {coords['x_au']}")
            print(f"   Y: {coords['y_au']}")
            print(f"   Z: {coords['z_au']}")

            # Distance from Sun (pythagorean theorem in 3D)
            dist = (coords['x_au']**2 + coords['y_au']
                    ** 2 + coords['z_au']**2) ** 0.5
            print(f"   📏 Distance from Sun: {dist:.3f} AU")
    else:
        print(f"❌ Error: {response.status_code}")


test_horizons("Mars", "499")
