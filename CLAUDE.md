# GDF-AutoMon Development Guide

## Project
Goat & Dairy Farm Automated Monitoring Platform — real-time IoT sensor PWA.
Stack: React 18 + TypeScript PWA · FastAPI (Python 3.12) · TimescaleDB · EMQX 5.x · Socket.io · Redis

## Architecture
```
ESP32/RPi → EMQX 5.x (MQTT) → FastAPI → TimescaleDB
                              ↓         ↓
                         Redis Pub/Sub  Alert/Plan engine
                              ↓
                       Node.js Socket.io → React PWA
                              ↓
                    Web Push / Twilio SMS+Call → Users
```
MQTT topic: `gdf/{sensor_id}/{channel}` (e.g. `gdf/abc-123/temperature`)

## Quick Start
```bash
cd infra && cp .env.example .env && bash scripts/gen-vapid-keys.sh
docker compose up -d timescaledb redis emqx
bash scripts/init-db.sh
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd realtime && npm install && npm run dev
cd frontend && npm install && npm run dev   # → http://localhost:5173
```

## RBAC Roles
| Role | Access |
|------|--------|
| `super_admin` | Everything; user/permission management |
| `admin` | Assigned locations + all sensors in them; create tasks/plans |
| `operator` | Permitted locations/sensors only; view + complete tasks |

## Feature Modules
| Module | Backend | Frontend |
|--------|---------|---------|
| Auth | `api/auth.py` | `pages/Login.tsx`, `contexts/AuthContext.tsx` |
| Locations | `api/locations.py` | `pages/Locations.tsx` |
| Users + Permissions | `api/users.py` | `pages/Users.tsx` |
| Sensors + RBAC | `api/sensors.py` | `pages/SensorManagement.tsx` |
| Telemetry | `api/telemetry.py` | `components/dashboard/HistoricalChart.tsx` |
| Alerts | `api/alerts.py` | `pages/Dashboard.tsx` |
| Planning | `api/plans.py` | `pages/Planning.tsx` |
| Tasks/Goals | `api/tasks.py` | `pages/Tasks.tsx`, `pages/TaskDetail.tsx` |
| Push + Notifs | `api/push.py`, `api/notifications.py` | `pages/Settings.tsx` |

## Planning Module
Plans define metric targets for a sensor channel. Each plan can have multiple **actions** that fire when the sensor value breaches the target range:
- `notification` — Web Push to permitted users
- `sms` — Twilio SMS (requires `TWILIO_*` env vars)
- `call` — Twilio voice call (stub; requires `TWILIO_*` env vars)
- `reminder` — stored as in-app notification

Model: `plans` → `plan_actions` (one-to-many).
Evaluation runs in `services/plan_action_service.py`, called by `alert_engine.evaluate_rules()`.

## Tasks Module
Admin creates tasks/goals with deadline, description, and media attachments. Users are tagged (assigned) to a task — only they see it.

Status flow: `open` → `submitted` (user marks done) → `done` (admin approves) | `rejected` (admin rejects → back to open).

Reminders fire automatically via background scheduler when deadline is ≤ 24h away.
Files stored in `backend/uploads/`, served at `/api/tasks/{id}/attachments/{filename}`.

## Sensor Plugin System
```
backend/app/plugins/base.py      — SensorAdapter ABC
backend/app/plugins/registry.py  — auto-discovers plugins/types/
backend/app/plugins/types/       — one file per sensor type
backend/app/plugins/adapters/    — protocol adapters (MQTT, Modbus, Serial, RTSP)
```
Add new type: create `plugins/types/{name}.py` → define `sensor_type`, `config_schema`, `data_channels`, implement `connect/stream/disconnect`. Frontend auto-discovers via `GET /api/sensors/types`. No frontend changes needed.

## Key Conventions
- UTC timestamps, `TIMESTAMPTZ` in DB
- Sensor config in JSONB — never add per-type columns to `sensors`
- MQTT QoS 1 for all readings
- Alert+plan thresholds evaluated in `alert_engine.py` on every ingested reading (<5ms)
- TimescaleDB: 7-day chunks, 90-day compression on `sensor_readings`
- Push only to users with RBAC access + `push_enabled` preference for severity/sensor

## Environment Variables (critical)
```
DATABASE_URL          asyncpg TimescaleDB connection
MQTT_HOST / MQTT_PORT EMQX broker
VAPID_PRIVATE_KEY / VAPID_PUBLIC_KEY  Web Push
SECRET_KEY            JWT signing key
TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER  SMS+Call (optional)
UPLOAD_DIR            File upload path (default: ./uploads)
```

## Slash Commands
| Command | Description |
|---------|-------------|
| `/add-sensor` | Wizard: type → config → test → save |
| `/gen-sensor-type` | Scaffold new sensor type boilerplate |
| `/test-sensor` | Stream live readings from a sensor config |
| `/db-migrate` | `alembic upgrade head` |
| `/deploy` | Build frontend + docker compose up with health checks |

## MCP Servers (`.claude/settings.json`)
| Server | Purpose |
|--------|---------|
| `postgres` | Inspect TimescaleDB schema / run SELECT queries |
| `fetch` | Sensor datasheets, EMQX docs |
| `filesystem` | Read sensor-edge/ firmware |

## Useful Commands
```bash
docker exec -it gdf-timescaledb psql -U gdf gdfautomon   # DB shell
docker logs -f gdf-backend                                 # Backend logs
docker exec -it gdf-emqx bin/emqx_ctl publish gdf/test/temperature 22.5  # Test MQTT
cd backend && pytest
cd frontend && npm run build   # TypeScript check + bundle
```
