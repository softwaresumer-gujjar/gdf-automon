# GDF-AutoMon

**Goat & Dairy Farm Automated Monitoring Platform**

Real-time IoT sensor dashboard as a Progressive Web App (PWA).

## Features

- **Generic sensor architecture** — add any sensor type without frontend changes
- **Real-time dashboard** — live charts powered by TradingView Lightweight Charts + Apache ECharts
- **PWA** — installable on any device, works offline, native push notifications
- **Sensor management** — add, remove, pause, resume, configure sensors from the UI
- **Alert engine** — configurable threshold rules with browser/mobile push notifications
- **Phase 1 sensors:** Temperature/Humidity (SHT31), Weight (HX711), Milk Analyzer (Lactoscan), IP Camera (RTSP)

## Quick Start

```bash
# 1. Clone and prepare
cp infra/.env.example infra/.env
# Edit infra/.env with your passwords

# 2. Generate VAPID keys for push notifications
bash infra/scripts/gen-vapid-keys.sh

# 3. Start the stack
cd infra && docker compose up -d

# 4. Initialize database
bash infra/scripts/init-db.sh

# 5. Start frontend dev server
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

## Architecture

```
ESP32/RPi sensors → EMQX 5.x (MQTT) → FastAPI → TimescaleDB
                                      ↓
                                Node.js Socket.io → React PWA
                                      ↓
                                Web Push / FCM → Notifications
```

See [CLAUDE.md](CLAUDE.md) for the full development guide.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + shadcn/ui + Tailwind |
| Charts | Apache ECharts + TradingView Lightweight Charts |
| Real-time | Socket.io (Node.js gateway) + MQTT.js |
| PWA | vite-plugin-pwa + Workbox + Web Push API |
| Backend | FastAPI (Python 3.12) + asyncio-mqtt |
| Database | TimescaleDB (PostgreSQL 16 hypertables) |
| MQTT broker | EMQX 5.x |
| Deployment | Docker Compose + Nginx |

## Adding a New Sensor Type

See [CLAUDE.md](CLAUDE.md#adding-a-new-sensor-type) or run `/gen-sensor-type` in Claude Code.

## Cloud Scaling

| Scale | Infrastructure | Est. Cost/month |
|-------|---------------|-----------------|
| <100 sensors | Single VPS + Docker Compose | $20–40 |
| <1,000 sensors | EMQX Cloud Serverless + VPS | $50–120 |
| <10,000 sensors | EMQX Cloud Dedicated + Timescale Cloud | $250–450 |
| 10,000+ sensors | EMQX Enterprise cluster + QuestDB + Kafka | $1,000+ |
