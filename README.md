# 🔭 Solar System Live Tracker

A real-time data pipeline that pulls live planetary and comet positions from 
NASA's Horizons API, streams them through AWS, and visualizes them on an 
interactive dashboard.

Check it out here! https://projectplanets.streamlit.app/

I also created a Tableau Public dashboard you can check out here! https://public.tableau.com/app/profile/luc.nguyen6635/viz/planets_17726414911280/Dashboard1?publish=yes

![Solar System Orrery](orrery.png)

---

## 🚀 What It Does

Every 10 minutes, this pipeline:
1. Queries **NASA Horizons API** for positions of 8 planets + 4 comets
2. Streams data through **AWS Kinesis**
3. Processes + enriches it with **AWS Lambda**
4. Stores snapshots in **AWS S3**
5. Makes it queryable via **AWS Athena**
6. Displays it live on a **Streamlit dashboard**

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Source | NASA JPL Horizons API |
| Ingestion | AWS Kinesis |
| Processing | AWS Lambda (Python 3.11) |
| Storage | AWS S3 |
| Query | AWS Athena (SQL) |
| Automation | AWS EventBridge (every 10 min) |
| Dashboard | Streamlit + Plotly |
| Language | Python 3.10+ |

---

## 📊 Dashboard Features

- 🌌 **Live Orrery** — real orbital paths with current positions overlaid
- 🏆 **Speed Leaderboard** — see Mercury blazing at 52 km/s vs Halley crawling at 0.9 km/s
- ⏱️ **Light Travel Time** — how long light takes to reach each object right now
- 📋 **Stats Table** — distance, speed, longitude for all tracked objects
- 🔄 **Auto-refresh** — data updates every 10 minutes automatically

---

## 🪐 Tracked Objects

**Planets:** Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune

**Comets:** Halley's Comet, Hale-Bopp, Churyumov-Gerasimenko, Encke

---

## 🏗️ Architecture
```
NASA Horizons API
      ↓
pipeline Lambda (every 10 min via EventBridge)
      ↓
AWS Kinesis Stream
      ↓
processor Lambda (auto-triggered)
      ↓
AWS S3
  ├── raw/YYYY/MM/DD/HHMM/snapshot.json
  └── processed/planet|comet/name/timestamp.json
      ↓
AWS Athena (SQL)
      ↓
Streamlit Dashboard
```

---

## 📦 Project Structure
```
solar-tracker/
├── pipeline.py           # polls NASA Horizons + pushes to Kinesis
├── lambda_function.py    # processor Lambda (Kinesis → S3)
├── dashboard.py          # Streamlit live dashboard
├── orrery.py             # local matplotlib orrery visualization
├── generate_orbits.py    # generates historical orbit trace data
├── test_horizons.py      # API testing scripts
└── requirements.txt
```

---

## 🚀 How to Run Locally

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/solar-tracker.git
cd solar-tracker
```

**2. Install dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Configure AWS credentials**
```bash
aws configure
# Enter your access key, secret, and set region to us-west-2
```

**4. Run the pipeline manually**
```bash
python pipeline.py
```

**5. Launch the dashboard**
```bash
streamlit run dashboard.py
```

---

## ☁️ AWS Infrastructure Setup
```bash
# Create Kinesis stream
aws kinesis create-stream \
  --stream-name solar-system-positions \
  --shard-count 1 --region us-west-2

# Create S3 bucket
aws s3 mb s3://your-bucket-name --region us-west-2

# Deploy processor Lambda
zip lambda_function.zip lambda_function.py
aws lambda create-function \
  --function-name solar-tracker-processor \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/solar-tracker-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --region us-west-2

# Deploy pipeline Lambda
cd lambda_package && zip -r ../pipeline_lambda.zip .
aws lambda create-function \
  --function-name solar-tracker-pipeline \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/solar-tracker-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://pipeline_lambda.zip \
  --timeout 300 --memory-size 256 \
  --region us-west-2

# Schedule with EventBridge
aws events put-rule \
  --name solar-tracker-schedule \
  --schedule-expression "rate(10 minutes)" \
  --state ENABLED --region us-west-2
```

---

## 📡 Data Source

All positional data comes from **NASA JPL Horizons** — the same system used 
by professional astronomers and mission planners at NASA's Jet Propulsion 
Laboratory. Positions are accurate to within kilometers.

---

## 📝 License

MIT License — free to use, modify, and share.

---
