import requests
import re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime, timezone, timedelta

KM_PER_AU = 149_597_870.7

PLANETS = {
    "Mercury": ("199", "#b5b5b5", 4),
    "Venus":   ("299", "#e8cda0", 6),
    "Earth":   ("399", "#4fa3e0", 6),
    "Mars":    ("499", "#c1440e", 5),
    "Jupiter": ("599", "#c88b3a", 12),
    "Saturn":  ("699", "#e4d191", 10),
    "Uranus":  ("799", "#7de8e8", 8),
    "Neptune": ("899", "#4b70dd", 8),
}

COMETS = {
    "Halley":           ("90000030", "#e8f4e8", 5),
    "Hale-Bopp":        ("90000765", "#ffe0a0", 5),
    "Churyumov-Geras.": ("90000772", "#f0c0ff", 5),
    "Encke":            ("90000035", "#c0ffc0", 5),
}


def parse_xyz(result_text):
    soe_index = result_text.find("$$SOE")
    eoe_index = result_text.find("$$EOE")
    if soe_index == -1 or eoe_index == -1:
        return None
    data_block = result_text[soe_index:eoe_index]
    x = re.search(r"X\s*=\s*([-\d.E+]+)", data_block)
    y = re.search(r"Y\s*=\s*([-\d.E+]+)", data_block)
    vx = re.search(r"VX\s*=\s*([-\d.E+]+)", data_block)
    vy = re.search(r"VY\s*=\s*([-\d.E+]+)", data_block)
    if x and y:
        return {
            "x_au": float(x.group(1)) / KM_PER_AU,
            "y_au": float(y.group(1)) / KM_PER_AU,
            "vx_kms": float(vx.group(1)) if vx else None,
            "vy_kms": float(vy.group(1)) if vy else None,
        }
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


def fetch_objects(objects):
    results = {}
    for name, (cmd, color, size) in objects.items():
        data = query_horizons(cmd)
        if data and "result" in data and "error" not in data:
            coords = parse_xyz(data["result"])
            if coords:
                results[name] = {"coords": coords,
                                 "color": color, "size": size}
                print(f"  ✅ {name}")
            else:
                print(f"  ❌ {name} — parse failed")
        else:
            print(f"  ❌ {name} — API failed")
    return results


def draw_orrery():
    print("🔭 Fetching planets...")
    planet_data = fetch_objects(PLANETS)
    print("☄️  Fetching comets...")
    comet_data = fetch_objects(COMETS)

    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    fig.patch.set_facecolor("#0a0a1a")

    titles = ["🔭 Inner Solar System (0–6 AU)", "🌌 Full Solar System (0–32 AU)"]
    limits = [6, 32]
    all_data = {**planet_data, **comet_data}

    for ax, title, lim in zip(axes, titles, limits):
        ax.set_facecolor("#0a0a1a")

        # Background stars
        np.random.seed(42)
        sx = np.random.uniform(-lim, lim, 400)
        sy = np.random.uniform(-lim, lim, 400)
        ax.scatter(sx, sy, s=0.3, color="white", alpha=0.4, zorder=0)

        # Sun
        ax.scatter(0, 0, s=250, color="#FDB813", zorder=5)
        ax.annotate("☀", (0, 0), textcoords="offset points",
                    xytext=(6, 6), color="#FDB813", fontsize=10)

        for name, obj in all_data.items():
            x = obj["coords"]["x_au"]
            y = obj["coords"]["y_au"]
            color = obj["color"]
            size = obj["size"]
            dist = (x**2 + y**2) ** 0.5

            # Skip if outside this panel's range
            if dist > lim * 1.1:
                continue

            # Orbit ring
            orbit = plt.Circle((0, 0), dist, color=color, fill=False,
                               alpha=0.12, linewidth=0.7, linestyle="--")
            ax.add_patch(orbit)

            # Is it a comet?
            is_comet = name in comet_data

            if is_comet:
                # Draw comet as a star marker with a little tail
                ax.scatter(x, y, s=size**2, color=color,
                           marker="*", zorder=6)
                # Tail — opposite to velocity direction
                vx = obj["coords"].get("vx_kms") or 0
                vy = obj["coords"].get("vy_kms") or 0
                speed = (vx**2 + vy**2) ** 0.5 or 1
                tail_len = dist * 0.08
                ax.annotate("", xy=(x - (vx/speed)*tail_len, y - (vy/speed)*tail_len),
                            xytext=(x, y),
                            arrowprops=dict(arrowstyle="-", color=color,
                                            alpha=0.5, lw=1.5))
            else:
                ax.scatter(x, y, s=size**2, color=color, zorder=6)

            ax.annotate(name, (x, y), textcoords="offset points",
                        xytext=(6, 5), color=color,
                        fontsize=7.5, fontweight="bold")

        # Formatting
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.set_title(title, color="white", fontsize=12, pad=10)
        ax.set_xlabel("X (AU)", color="#aaaacc", fontsize=9)
        ax.set_ylabel("Y (AU)", color="#aaaacc", fontsize=9)
        ax.tick_params(colors="#aaaacc")
        for spine in ax.spines.values():
            spine.set_edgecolor("#222244")
        ax.grid(color="#111133", linewidth=0.5, alpha=0.5)

    # Legend
    planet_patch = mpatches.Patch(color="#4fa3e0", label="🪐 Planets")
    comet_patch = mpatches.Patch(
        color="#e8f4e8", label="☄️  Comets (★ with tail)")
    fig.legend(handles=[planet_patch, comet_patch],
               loc="lower center", ncol=2,
               facecolor="#0a0a1a", edgecolor="#333355",
               labelcolor="white", fontsize=10)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fig.suptitle(f"Solar System Live — {now_str}",
                 color="white", fontsize=15, y=0.98)

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    plt.savefig("orrery.png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print("\n✅ Saved to orrery.png!")
    plt.show()


if __name__ == "__main__":
    draw_orrery()
