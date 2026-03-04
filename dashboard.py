import numpy as np
import streamlit as st
import boto3
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────
BUCKET = "solar-tracker-lnguyen"
REGION = "us-west-2"

st.set_page_config(
    page_title="🔭 Solar System Live Tracker",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Dark theme styling ─────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0a0a1a; color: white; }
    .metric-card {
        background: #111133;
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
        border: 1px solid #222255;
    }
    h1, h2, h3 { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ── Load latest data from S3 ───────────────────────────────


@st.cache_data(ttl=600)  # refresh every 10 min
def load_latest_data():
    s3 = boto3.client("s3", region_name=REGION)

    # List all snapshots and get the latest
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix="raw/")
    files = sorted([obj["Key"] for obj in response.get("Contents", [])
                   if obj["Key"].endswith("snapshot.json")])

    if not files:
        return pd.DataFrame()

    # Load the latest snapshot
    latest = files[-1]
    obj = s3.get_object(Bucket=BUCKET, Key=latest)
    data = json.loads(obj["Body"].read().decode("utf-8"))

    df = pd.DataFrame(data)
    df["light_travel_min"] = round(df["dist_from_sun_au"] * 8.317, 2)

    # Earth's approximate position
    earth_x, earth_y = -0.948, 0.289
    df["dist_from_earth_au"] = round(
        ((df["x_au"] - earth_x)**2 + (df["y_au"] - earth_y)**2) ** 0.5, 6
    )

    # Heliocentric longitude
    df["helio_longitude_deg"] = round(
        np.degrees(np.arctan2(df["y_au"], df["x_au"])) % 360, 3
    )

    return df, latest

# ── Load orbit data from S3 ────────────────────────────────


@st.cache_data(ttl=3600)  # refresh every hour
def load_orbit_data():
    s3 = boto3.client("s3", region_name=REGION)
    try:
        obj = s3.get_object(Bucket=BUCKET, Key="orbits/orbit_data.json")
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()


# ── Header ─────────────────────────────────────────────────
st.title("🔭 Solar System Live Tracker")
st.caption(
    f"Data from NASA Horizons API • Updates every 10 minutes • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

# ── Load data ──────────────────────────────────────────────
try:
    df, latest_file = load_latest_data()
    st.caption(f"📦 Latest snapshot: `{latest_file}`")
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

if df.empty:
    st.warning("No data found in S3 yet. Run pipeline.py first!")
    st.stop()

planets = df[df["object_type"] == "planet"]
comets = df[df["object_type"] == "comet"]

# ── Metric cards ───────────────────────────────────────────
st.subheader("📊 Current Snapshot")
cols = st.columns(4)
with cols[0]:
    st.metric("🪐 Planets tracked", len(planets))
with cols[1]:
    st.metric("☄️ Comets tracked", len(comets))
with cols[2]:
    fastest = df.loc[df["speed_kms"].idxmax()]
    st.metric("🏆 Fastest object",
              f"{fastest['target_name']} — {fastest['speed_kms']} km/s")
with cols[3]:
    farthest = df.loc[df["dist_from_sun_au"].idxmax()]
    st.metric("🌌 Farthest object",
              f"{farthest['target_name']} — {farthest['dist_from_sun_au']:.1f} AU")

st.divider()

# ── Orrery ─────────────────────────────────────────────────
st.subheader("🌌 Live Orrery")

COLORS = {
    "Mercury": "#b5b5b5", "Venus": "#e8cda0", "Earth": "#4fa3e0",
    "Mars": "#c1440e", "Jupiter": "#c88b3a", "Saturn": "#e4d191",
    "Uranus": "#7de8e8", "Neptune": "#4b70dd",
    "Halley": "#e8f4e8", "Hale-Bopp": "#ffe0a0",
    "Churyumov-Geras.": "#f0c0ff", "Encke": "#c0ffc0"
}

fig_orrery = go.Figure()

# Sun
fig_orrery.add_trace(go.Scatter(
    x=[0], y=[0],
    mode="markers+text",
    marker=dict(size=20, color="#FDB813", symbol="circle"),
    text=["☀️"], textposition="top center",
    name="Sun", hoverinfo="name"
))

# Orbit rings
for _, row in df.iterrows():
    import numpy as np
    r = row["dist_from_sun_au"]
    theta = np.linspace(0, 2*np.pi, 100)
    fig_orrery.add_trace(go.Scatter(
        x=r*np.cos(theta), y=r*np.sin(theta),
        mode="lines",
        line=dict(color=COLORS.get(
            row["target_name"], "white"), width=0.5, dash="dot"),
        opacity=0.2,
        showlegend=False,
        hoverinfo="skip"
    ))

# Planet/comet positions
for _, row in df.iterrows():
    color = COLORS.get(row["target_name"], "white")
    symbol = "circle" if row["object_type"] == "planet" else "star"
    size = 12 if row["object_type"] == "planet" else 10
    fig_orrery.add_trace(go.Scatter(
        x=[row["x_au"]], y=[row["y_au"]],
        mode="markers+text",
        marker=dict(size=size, color=color, symbol=symbol),
        text=[row["target_name"]],
        textposition="top center",
        textfont=dict(color=color, size=10),
        name=row["target_name"],
        hovertemplate=(
            f"<b>{row['target_name']}</b><br>"
            f"Distance from Sun: {row['dist_from_sun_au']:.3f} AU<br>"
            f"Speed: {row['speed_kms']} km/s"
            "<extra></extra>"
        )))

fig_orrery.update_layout(
    paper_bgcolor="#0a0a1a",
    plot_bgcolor="#0a0a1a",
    font=dict(color="white"),
    xaxis=dict(range=[-35, 35], showgrid=False,
               zeroline=False, title="X (AU)"),
    yaxis=dict(range=[-35, 35], showgrid=False,
               zeroline=False, title="Y (AU)"),
    height=600,
    showlegend=False,
    margin=dict(l=0, r=0, t=0, b=0)
)

st.plotly_chart(fig_orrery, use_container_width=True)

st.divider()

# ── Two columns: speed + light travel ─────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Speed Leaderboard")
    df_sorted = df.sort_values("speed_kms", ascending=True)
    fig_speed = px.bar(
        df_sorted, x="speed_kms", y="target_name",
        orientation="h",
        color="speed_kms",
        color_continuous_scale="Plasma",
        labels={"speed_kms": "Speed (km/s)", "target_name": ""}
    )
    fig_speed.update_layout(
        paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a",
        font=dict(color="white"), coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=0, b=0), height=400
    )
    st.plotly_chart(fig_speed, use_container_width=True)

with col2:
    st.subheader("⏱️ Light Travel Time from Sun")
    df_sorted2 = df.sort_values("light_travel_min", ascending=True)
    fig_light = px.bar(
        df_sorted2, x="light_travel_min", y="target_name",
        orientation="h",
        color="light_travel_min",
        color_continuous_scale="Viridis",
        labels={"light_travel_min": "Minutes", "target_name": ""}
    )
    fig_light.update_layout(
        paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a",
        font=dict(color="white"), coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=0, b=0), height=400
    )
    st.plotly_chart(fig_light, use_container_width=True)

st.divider()

# ── Stats table ────────────────────────────────────────────
st.subheader("📋 Full Stats Table")
display_df = df[[
    "target_name", "object_type", "dist_from_sun_au",
    "speed_kms", "dist_from_earth_au", "light_travel_min",
    "helio_longitude_deg"
]].sort_values("dist_from_sun_au")

display_df.columns = [
    "Object", "Type", "Dist from Sun (AU)",
    "Speed (km/s)", "Dist from Earth (AU)",
    "Light Travel (min)", "Longitude (°)"
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# ── Auto refresh button ────────────────────────────────────
st.divider()
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.caption(
        "Data auto-refreshes every 10 minutes • Click button to force refresh")
