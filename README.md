---
title: TransitSight
emoji: 🚆
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# 🚆 TransitSight — Smart Public Transport Crowd Predictor

A web-based smart public transport crowd predictor for Malaysian transit. Integrates **data.gov.my** APIs (GTFS Static, GTFS Realtime, Weather) with **Google AI Studio (Gemini API)** to deliver real-time crowd level predictions for urban commuters.

Built as a Software Engineering course project (UiTM), Group I.

**SDG 11 Relevance:** Promotes sustainable cities by encouraging public transit usage through data-driven mobility insights.

---

## ✨ Features

### 👥 Commuter Dashboard
- **Live Route List** — View all transit routes with real-time crowd predictions
- **Color-Coded Badges** — 🟢 Low, 🟡 Medium, 🔴 Full at a glance
- **Search Routes** — Find routes by name, ID, or agency
- **Route Detail View** — Detailed AI prediction with confidence score, weather context, and feedback options
- **Travel Recommendations** — Compare 5 time slots to find the least crowded travel window

### 🤖 AI-Powered Predictions
- **Gemini API Integration** — Structured prompts with live GTFS schedule data, weather, and user feedback
- **Rule-Based Fallback** — Intelligent rules based on time, day, weather, and route-specific profiles
- **Context-Aware** — Considers: time, day, weather, temperature, GTFS schedules, active vehicles, user feedback

### 📝 Crowd Feedback System
- **Report Crowd** — Users submit actual crowd levels to validate predictions
- **Badge Gamification** — 5 tiers: 🌱 Newcomer → 🥉 Bronze → 🥈 Silver → 🥇 Gold → 💎 Platinum → 👑 Diamond
- **Personal Profile** — View feedback history, streak, accuracy stats, and badge progress
- **Self-Calibration** — User feedback blends (30%) into future predictions

### 🏛️ Authority Analytics (Public)
- **Route-Level Summaries** — Crowd scores and latest predictions per route
- **Peak Hour Patterns** — Congestion heatmap by hour (last 7 days)
- **Crowd Distribution** — Low/Medium/Full breakdown
- **Accuracy Trends** — 14-day prediction accuracy tracking

### 🛠️ Admin Dashboard
- **Live Stats** — Total predictions, feedback, routes, users
- **API Health Monitor** — Live status of data.gov.my and Gemini API connections
- **System Configuration** — Update Gemini model and admin credentials
- **Audit Logging** — All external API calls logged with response times
- **Route Refresh** — Pull latest GTFS data on demand

### 🚇 Supported Routes (Live from data.gov.my GTFS)

| Route | Agency | Type |
|-------|--------|------|
| Kelana Jaya Line (KJ) | Rapid KL | LRT |
| Ampang Line (AG) | Rapid KL | LRT |
| Sri Petaling Line (PH) | Rapid KL | LRT |
| Kajang Line (KGL) | Rapid KL | MRT |
| Putrajaya Line (PYL) | Rapid KL | MRT |
| Monorail Line (MR) | Rapid KL | Monorail |
| BRT Sunway Line (BRT) | Rapid KL | BRT |
| Batu Caves – Pulau Sebang (KC05_KB18) | KTMB | Komuter |
| Tanjung Malim – Pel. Klang (KA15_KD19) | KTMB | Komuter |
| Butterworth – Padang Besar (100_47300) | KTMB | Komuter |
| Butterworth – Ipoh (100_9000) | KTMB | Komuter |
| Tumpat – Gemas (SH) | KTMB | Intercity |
| Tumpat – JB Sentral (ERT) | KTMB | Intercity |
| Gemas – JB Sentral (ES) | KTMB | Intercity |
| JB Sentral – Woodlands (ST) | KTMB | Shuttle |
| Padang Besar – Gemas (ETS) | KTMB | ETS |

---

## 🏗️ Architecture

```
┌──────────────┐     HTTPS      ┌───────────────────┐     HTTPS     ┌─────────────────┐
│  User Device │ ────────────▶  │  TransitSight    │ ────────────▶ │  data.gov.my    │
│  (Browser)   │                │  Web Server       │               │  (GTFS/Weather) │
└──────────────┘                │  (Python/FastAPI) │               └─────────────────┘
                                │                   │
                                │  ┌─────────────┐  │     HTTPS     ┌─────────────────┐
                                │  │  SQLite DB  │  │               │  Google AI      │
                                │  │  (feedback, │  │ ────────────▶ │  Studio        │
                                │  │   config)   │  │               │  (Gemini API)   │
                                │  └─────────────┘  │               └─────────────────┘
                                └───────────────────┘
```

**3-Tier Architecture:**
- **Presentation** — Responsive HTML/CSS/JS (vanilla JS, mobile-optimized)
- **Application** — Python FastAPI backend with modular services
- **Data** — SQLite database + external APIs (data.gov.my, Gemini)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- (Optional) Google AI Studio API key for AI predictions

### Installation

```bash
# Clone the repo
git clone https://github.com/zakir-my/transitsight.git
cd transitsight

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (optional but recommended)
```

### Run the App

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

### Admin Login
- URL: http://localhost:8000/admin
- Default credentials: `admin` / `admin123`

---

## 📁 Project Structure

```
transitsight/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLite setup, models, and audit logging
│   ├── services/
│   │   ├── transit_service.py   # GTFS Static/Realtime + context extraction
│   │   ├── weather_service.py   # Weather data with 60s cache + audit logging
│   │   ├── ai_service.py        # Gemini API + rule-based fallback + badge-aware
│   │   ├── feedback_service.py  # Feedback, streaks, badge tiers
│   │   └── route_service.py     # Route CRUD and search
│   └── routers/
│       ├── prediction.py     # Prediction, routes, travel recommendation
│       ├── feedback.py       # Feedback, user profile, streaks
│       ├── authority.py      # Public transit authority analytics
│       └── admin.py          # Admin dashboard, API health, config
├── static/
│   ├── index.html           # Landing page
│   ├── dashboard.html       # Commuter dashboard
│   ├── route.html           # Route detail + prediction + feedback
│   ├── authority.html       # Public authority analytics
│   ├── profile.html         # User profile + badge + history
│   ├── admin.html           # Admin panel with config
│   ├── css/style.css        # Dark theme, responsive
│   └── js/
│       ├── main.js           # Shared utilities + API helpers
│       ├── dashboard.js      # Dashboard + lazy prediction loading
│       ├── route-detail.js   # Prediction, feedback, travel recommendation
│       ├── authority.js      # Authority analytics
│       ├── profile.js        # Profile, badge display, history
│       └── admin.js          # Admin login, dashboard, config
├── scripts/
│   └── hf-sync.py           # Hugging Face Spaces auto-sync + rebuild
├── .env.example
├── .dockerignore
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/routes` | List all routes | — |
| GET | `/api/routes?search=` | Search routes | — |
| GET | `/api/routes/{id}` | Route details + recent predictions | — |
| GET | `/api/predict?route_id=` | Crowd prediction with GTFS + weather | — |
| GET | `/api/recommend?route_id=` | Travel recommendation (5 time slots) | — |
| POST | `/api/feedback` | Submit crowd validation feedback | — |
| GET | `/api/feedback/stats/{id}` | Feedback stats per route | — |
| GET | `/api/feedback/user/{id}` | User streak | — |
| GET | `/api/profile/{user_id}` | User profile, badge, history | — |
| GET | `/api/authority/dashboard` | Public authority analytics | — |
| GET | `/api/authority/routes/{id}/trends` | Route trend data | — |
| GET | `/api/admin/dashboard` | Admin dashboard data | Basic Auth |
| GET | `/api/admin/api-health` | External API health check | Basic Auth |
| GET | `/api/admin/config` | System configuration | Basic Auth |
| POST | `/api/admin/config` | Update configuration | Basic Auth |
| POST | `/api/admin/routes/refresh` | Refresh from GTFS API | Basic Auth |
| GET | `/api/admin/debug/config` | Debug environment config | Basic Auth |

---

## 🔧 Configuration

All configuration is via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google AI Studio API key (for AI predictions) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `ADMIN_USERNAME` | `admin` | Admin login username |
| `ADMIN_PASSWORD` | `admin123` | Admin login password |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

**Note:** data.gov.my APIs are free-tier and don't require API keys. The app works without a Gemini API key using rule-based fallback predictions.

---

## 🧪 Test the Setup

```bash
# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test routes endpoint
curl http://localhost:8000/api/routes

# Test prediction (use a real route ID from /api/routes)
curl "http://localhost:8000/api/predict?route_id=KJ"

# Test travel recommendation
curl "http://localhost:8000/api/recommend?route_id=KJ"

# Test feedback (includes badge in response)
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"route_id":"KJ","predicted_level":"Medium","reported_level":"Low"}'

# Test public authority dashboard
curl http://localhost:8000/api/authority/dashboard

# Test admin (requires auth)
curl -u admin:admin123 http://localhost:8000/api/admin/dashboard

# Test API health
curl -u admin:admin123 http://localhost:8000/api/admin/api-health
```

---

## 👥 Team (Group I)

| Name | ID | Role |
|------|-----|------|
| Muhammad Zakir Bin Yunos | 2024381311 | Team Leader |
| Abdullah Shuib Bin Mohd Mazri | 2021889154 | Software Analyst |
| Meor Muhammad Hakim Bin Meor Abdul Razak | 2021613446 | Software Developer |
| Muhammad Zulhelmi Bin Jamalulil | 2024113303 | Software Tester |
| Ahmad Faiz Bin Muhammad | 2025756991 | Software Designer |

---

## 📚 References

- [data.gov.my GTFS Static API](https://developer.data.gov.my/realtime-api/gtfs-static)
- [data.gov.my GTFS Realtime API](https://developer.data.gov.my/realtime-api/gtfs-realtime)
- [data.gov.my Weather API](https://developer.data.gov.my/realtime-api/weather)
- [Google AI Studio / Gemini API](https://ai.google.dev/gemini-api/docs)
- [SDG 11: Sustainable Cities and Communities](https://sdgs.un.org/goals/goal11)
