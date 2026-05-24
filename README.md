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

### 🤖 AI-Powered Predictions
- **Gemini API Integration** — Structured prompts fed to Google AI Studio for crowd classification
- **Rule-Based Fallback** — If Gemini API is unavailable, intelligent rules based on time, day, and weather
- **Context-Aware** — Considers: time of day, day of week, weather condition, temperature, route type

### 📝 Crowd Feedback System
- **Report Crowd** — Users submit actual crowd levels to validate predictions
- **Gamification** — Streak tracking to encourage engagement
- **Accuracy Analytics** — Track prediction accuracy over time

### 🛠️ Admin Dashboard
- **Live Stats** — Total predictions, feedback count, unique users, routes tracked
- **Crowd Distribution** — Visual breakdown of Low/Medium/Full predictions
- **API Health Monitor** — Status of data.gov.my and Gemini API connections
- **Recent Feedback** — Table of crowd validation submissions
- **Accuracy Trends** — 7-day prediction accuracy chart

### 🚇 Supported Routes (10 Default)
| Route | Agency | Color |
|-------|--------|-------|
| LRT Kelana Jaya Line | Rapid KL | 🔴 |
| LRT Ampang Line | Rapid KL | 🟢 |
| LRT Sri Petaling Line | Rapid KL | 🟣 |
| MRT Kajang Line | Rapid KL | 🟠 |
| MRT Putrajaya Line | Rapid KL | 🔵 |
| KTM Komuter (Port Klang) | KTMB | 🔴 |
| KTM Komuter (Seremban) | KTMB | 🟦 |
| KTM ETS (KL-Butterworth) | KTMB | 🟠 |
| KL Monorail | Rapid KL | 🔵 |
| BRT Sunway Line | Rapid KL | 🟢 |

---

## 🏗️ Architecture

```
┌──────────────┐     HTTPS     ┌──────────────────┐     HTTPS     ┌─────────────────┐
│  User Device  │ ────────────▶ │  TransitSight     │ ────────────▶ │  data.gov.my     │
│  (Browser)    │              │  Web Server       │              │  (GTFS/Weather)  │
└──────────────┘              │  (Python/FastAPI) │              └─────────────────┘
                                │                   │
                                │  ┌─────────────┐  │     HTTPS     ┌─────────────────┐
                                │  │  SQLite DB   │  │              │  Google AI       │
                                │  │  (feedback,  │  │ ────────────▶│  Studio          │
                                │  │   config)    │  │              │  (Gemini API)    │
                                │  └─────────────┘  │              └─────────────────┘
                                └──────────────────┘
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
│   ├── database.py          # SQLite setup and models
│   ├── services/
│   │   ├── transit_service.py   # GTFS Static/Realtime data (data.gov.my)
│   │   ├── weather_service.py   # Weather data (data.gov.my)
│   │   ├── ai_service.py        # Gemini API integration & fallback logic
│   │   ├── feedback_service.py  # Crowd validation feedback management
│   │   └── route_service.py     # Route data management
│   └── routers/
│       ├── prediction.py     # Prediction & route API endpoints
│       ├── feedback.py       # Feedback API endpoints
│       └── admin.py          # Admin API endpoints
├── static/
│   ├── index.html           # Landing page
│   ├── dashboard.html       # Commuter dashboard
│   ├── route.html           # Route detail view
│   ├── admin.html           # Admin dashboard
│   ├── css/style.css        # Dark theme styles
│   └── js/
│       ├── main.js           # Shared utilities
│       ├── dashboard.js      # Dashboard logic
│       ├── route-detail.js   # Route detail logic
│       └── admin.js          # Admin dashboard logic
├── docs/
│   └── SDD-TransitSight-v1.0.docx   # Software Design Description
├── .env.example
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
| GET | `/api/predict?route_id=` | Get crowd prediction for a route | — |
| POST | `/api/feedback` | Submit crowd validation feedback | — |
| GET | `/api/feedback/stats/{id}` | Feedback stats per route | — |
| GET | `/api/feedback/user/{id}` | User feedback streak | — |
| GET | `/api/admin/dashboard` | Admin dashboard data | Basic Auth |
| GET | `/api/admin/api-health` | External API health check | Basic Auth |
| POST | `/api/admin/routes/refresh` | Refresh from GTFS API | Basic Auth |

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

# Test prediction
curl "http://localhost:8000/api/predict?route_id=KJL001"

# Test feedback
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"route_id":"KJL001","predicted_level":"Medium","reported_level":"Low"}'

# Test admin (requires auth)
curl -u admin:admin123 http://localhost:8000/api/admin/dashboard
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
