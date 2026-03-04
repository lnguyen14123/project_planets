import numpy as np
import json
import boto3

# Orbital elements (a in AU, e = eccentricity, i/omega/Omega in degrees)
# Source: NASA JPL fact sheets
ORBITAL_ELEMENTS = {
    # name:        (a,      e,      i,      Omega,   omega)
    "Mercury":     (0.387,  0.2056, 7.005,  48.331,  29.124),
    "Venus":       (0.723,  0.0068, 3.395,  76.680,  54.884),
    "Earth":       (1.000,  0.0167, 0.000,  0.000,   102.94),
    "Mars":        (1.524,  0.0934, 1.850,  49.558,  286.50),
    "Jupiter":     (5.203,  0.0489, 1.303,  100.46,  273.87),
    "Saturn":      (9.537,  0.0565, 2.485,  113.66,  339.39),
    "Uranus":      (19.191, 0.0472, 0.773,  74.006,  96.998),
    "Neptune":     (30.069, 0.0086, 1.770,  131.78,  273.19),

    "Halley":      (17.834, 0.9671, 162.26, 58.420,  111.33),
    "Hale-Bopp":   (186.0,  0.9951, 89.43,  282.47,  130.59),
    "Churyumov-Geras.": (3.463, 0.6412, 7.043, 50.147, 12.780),
    "Encke":       (2.217,  0.8483, 11.78,  334.57,  186.54),
}


def compute_orbit(a, e, i, Omega, omega, n_points=300):
    """
    Compute x,y coordinates of an orbit from Keplerian elements.
    Returns arrays of x, y in AU (heliocentric ecliptic plane).
    """
    # Eccentric anomaly from 0 to 2pi
    E = np.linspace(0, 2 * np.pi, n_points)

    # Position in orbital plane
    x_orb = a * (np.cos(E) - e)
    y_orb = a * np.sqrt(1 - e**2) * np.sin(E)

    # Convert angles to radians
    i_r = np.radians(i)
    Omega_r = np.radians(Omega)
    omega_r = np.radians(omega)

    # Rotation matrices — orbital plane → ecliptic plane
    cos_O, sin_O = np.cos(Omega_r), np.sin(Omega_r)
    cos_o, sin_o = np.cos(omega_r), np.sin(omega_r)
    cos_i, sin_i = np.cos(i_r),     np.sin(i_r)

    # Full rotation
    x = ((cos_O*cos_o - sin_O*sin_o*cos_i) * x_orb +
         (-cos_O*sin_o - sin_O*cos_o*cos_i) * y_orb)

    y = ((sin_O*cos_o + cos_O*sin_o*cos_i) * x_orb +
         (-sin_O*sin_o + cos_O*cos_o*cos_i) * y_orb)

    return x.tolist(), y.tolist()


def generate_and_upload():
    orbit_data = {}

    for name, (a, e, i, Omega, omega) in ORBITAL_ELEMENTS.items():
        x, y = compute_orbit(a, e, i, Omega, omega)
        orbit_data[name] = {"x": x, "y": y}
        print(f"✅ {name:<25} a={a} AU, e={e}")

    # Upload to S3
    boto3.client("s3", region_name="us-west-2").put_object(
        Bucket="solar-tracker-lnguyen",
        Key="orbits/orbit_elements.json",
        Body=json.dumps(orbit_data)
    )
    print(f"\n✅ Uploaded orbital elements data to S3!")
    print(f"📦 {len(orbit_data)} objects, {300} points each = {len(orbit_data)*300} total points")
    print(f"   (vs ~1061 uneven data points before)")


if __name__ == "__main__":
    generate_and_upload()
