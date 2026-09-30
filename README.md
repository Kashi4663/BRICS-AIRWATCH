# BRICS AIRWATCH
### Federated AI Climate & Pollution Intelligence Platform (prototype)

Django + DRF command-center prototype that fuses citizen photo/voice reports, sensor readings, satellite
observations and weather to detect hyper-local pollution hotspots, forecast spikes, project plume movement
and raise authority alerts.

> **DEMO ENVIRONMENT.** All data is synthetic (`is_demo=True`) and labelled **DEMO DATA** / **SIMULATED PREDICTION** /
> **AI ASSESSMENT** in the UI. No government feeds are connected and no official alerts or enforcement actions are produced.

## Quick start (Windows)
```
run.bat
```
## Quick start (macOS / Linux)
```
./run.sh
```
Manual:
```
pip install -r requirements.txt
copy .env.example .env        # or cp
python manage.py migrate
python manage.py seed_demo     # --reset to regenerate
python manage.py runserver
```
Open http://127.0.0.1:8000

Demo accounts (created by `seed_demo`):

| user | password | role |
|---|---|---|
| authority | authority123 | Authority — acknowledge / resolve alerts |
| citizen | citizen123 | Citizen |
| admin | admin12345 | Superuser — /admin/ |

Needs internet in the browser for fonts, Leaflet, Chart.js (cdnjs) and the CARTO dark basemap.

## Demo flow (hackathon script)
1. `/overview/` — metrics (AQI 184, 27 hotspots, 14 predicted, 03 cross-border, 1,284 reports, 92%).
2. `/map/` — glowing hotspots, heatmap, plumes, wind, fires, industrial zones, reports, predicted movement. Click **IN-GJ-0926-018**.
3. Panel → **AI Investigate** → agent runs 9 steps → evidence chain → result (89%, REQUIRES AUTHORITY VERIFICATION) → sensor trace + projected movement map → linked CRITICAL alert.
4. `/report/` — upload a photo, choose *Crop burning*, submit → processing animation → AI ASSESSMENT “Possible agricultural burning 87%, awaiting multi-source verification”. **Speak Report** uses the browser's speech recognition (Chrome) in 9 Indian languages, then translation + intent detection.
5. `/forecast/` — 142 → 168 → 193 → 221, spike probability 72/84/91%.
6. `/alerts/` — sign in as `authority` → Acknowledge / Mark resolved (audit-logged).
7. `/cross-border/` — FEDERATED ARCHITECTURE DEMONSTRATION: trajectories, country nodes, federated concept.
8. Floating **AIRWATCH AI** — ask “Summarize today's major climate anomalies.”

## Pages
Landing · Overview · Live Map · Hotspots · AI Investigate · Forecast · Cross-Border · Citizen Reports · Report Pollution · Alerts · Data Explorer · Climate Analytics · AI Assistant · Settings (integration status, architecture, BigQuery schema).

## REST API
| Method | Endpoint |
|---|---|
| GET | /api/dashboard/ · /api/status/ |
| GET | /api/hotspots/ (?country=IN&status=HIGH&q=) · /api/hotspots/<code>/ |
| GET | /api/map/layers/ |
| GET/POST | /api/reports/ (multipart: image, pollution_type, lat, lng, description, language, voice_transcript) |
| POST | /api/voice/process/ |
| POST | /api/ai/analyze-image/ · /api/ai/investigate/ |
| GET | /api/forecast/ (?hotspot= or ?city=) |
| GET | /api/cross-border/ |
| GET | /api/alerts/ · POST /api/alerts/<code>/acknowledge/ · /api/alerts/<code>/resolve/ (authority) |
| GET | /api/data/ (?country&city&days&pollutant&source&confidence&event_type) |
| POST | /api/assistant/ |

## Architecture
```
config/           settings, urls, api_urls
dashboard/        pages, roles (Profile), permissions, context processor
pollution/        Country, City, Hotspot, SensorReading, WeatherObservation, SatelliteObservation, IndustrialZone, HistoricalAQI, CrossBorderEvent
citizen_reports/  CitizenReport + reporting / voice API
alerts/           AuthorityAlert, AuditLog + alert API
ai_engine/        image analysis, investigation agent, assistant API
forecasting/      ForecastResult + forecast API
geospatial/       map layers + cross-border API
data_engine/      data explorer API, seed_demo & bigquery_schema commands
services/         gemini_service, vertex_service, earth_engine_service, speech_service,
                  bigquery_service, firebase_service, intelligence, validators, demo_data, config
templates/ static/
```
Every external service has a real integration path and a clearly labelled fallback:

| Service | Env var(s) | Without credentials |
|---|---|---|
| Gemini (vision, investigation, summaries, assistant) | GEMINI_API_KEY | Deterministic mock, labelled `MOCK AI (DEMO)` |
| Vertex AI forecasting | VERTEX_PROJECT_ID, VERTEX_ENDPOINT_ID (+ google-cloud-aiplatform) | Deterministic mock model, `SIMULATED PREDICTION` |
| Earth Engine (FIRMS fires) | EARTH_ENGINE_PROJECT (+ earthengine-api) | Stored demo observations |
| Cloud Translation | GOOGLE_TRANSLATE_API_KEY | Text passes through, flagged |
| BigQuery | BIGQUERY_PROJECT_ID (+ google-cloud-bigquery) | Django DB with BigQuery-ready schemas |
| Firebase (Firestore live reports, FCM alerts) | FIREBASE_PROJECT_ID (+ firebase-admin) | Local only |
| Google Maps | GOOGLE_MAPS_API_KEY | Map renders with Leaflet + CARTO dark tiles (key hook present; renderer is Leaflet) |

## Security
Session auth + CSRF (DRF SessionAuthentication), role-based access (citizen / authority / admin), authority-only alert actions
with AuditLog + audit logger, DRF rate limiting (reports 12/min, AI 30/min), upload checks (≤5 MB, JPG/PNG/WEBP, Pillow
verification, server-generated file names), input length/range validation, API keys only in environment variables and never
sent to the browser, X-Frame-Options DENY, nosniff, secure cookies when DEBUG=False.

## Deploy (Cloud Run)
Set `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, run `collectstatic`, serve with gunicorn
(`gunicorn config.wsgi`), and swap SQLite for Cloud SQL / BigQuery-backed storage.
