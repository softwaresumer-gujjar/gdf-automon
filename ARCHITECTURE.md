# GDF-AutoMon — System Architecture

Goat & Dairy Farm Automated Monitoring Platform. Full reference for hardware deployment, firmware configuration, backend services, real-time data flow, notifications, and mobile PWA delivery.

---

## Table of Contents

1. [Full System Overview](#1-full-system-overview)
2. [Physical Sensor Deployment Map](#2-physical-sensor-deployment-map)
3. [Hardware Wiring & Firmware Configuration](#3-hardware-wiring--firmware-configuration)
4. [MQTT Data Flow](#4-mqtt-data-flow)
5. [Backend Services Architecture](#5-backend-services-architecture)
6. [Real-Time Update Flow](#6-real-time-update-flow)
7. [Notification & Alert Pipeline](#7-notification--alert-pipeline)
8. [Frontend PWA Architecture & Mobile Install](#8-frontend-pwa-architecture--mobile-install)
9. [Tech Stack Roles](#9-tech-stack-roles)
10. [Wireless Network Setup](#10-wireless-network-setup)
11. [Docker Compose Deployment Reference](#11-docker-compose-deployment-reference)

---

## 1. Full System Overview

Every layer from physical sensors to browser pixel, with ports, protocols, and technology names.

```mermaid
graph TD
    subgraph FIELD["Field / Farm Edge"]
        ESP32_A["ESP32 Node\n(SHT31 Temp+Humidity)\nWiFi + MQTT"]
        ESP32_B["ESP32 Node\n(HX711 Weight Scale)\nWiFi + MQTT"]
        RPI_A["Raspberry Pi 4\n(Lactoscan RS-232 Bridge)\nSerial → MQTT"]
        RPI_B["Raspberry Pi 4\n(IP Camera HLS Bridge)\nRTSP → ffmpeg → HLS + MQTT"]
        CAM["IP Camera\n(RTSP stream)\nPoE / WiFi"]
    end

    subgraph NET["Farm Network (LAN / WiFi)"]
        AP["Ubiquiti UniFi AP\n802.11ac/ax\nSSID: GDF-Farm"]
        SW["PoE Switch\n(cameras + RPi wired)"]
    end

    subgraph SERVER["Application Server (Docker)"]
        EMQX["EMQX 5.x\nMQTT Broker\n:1883 / :8883 TLS\n:18083 Dashboard"]
        FASTAPI["FastAPI\n(Python 3.12)\n:8001\nREST API + MQTT Bridge\n+ Alert Engine"]
        TSDB["TimescaleDB\n(PostgreSQL 16)\n:5432\nHypertable sensor_readings\n7-day chunks · 90-day compression"]
        REDIS["Redis 7\n:6379\nPub/Sub · Session cache"]
        SOCKETIO["Socket.io Gateway\n(Node.js 20 + Fastify)\n:3001\nWebSocket fan-out"]
        NGINX["Nginx\n:80 / :443 TLS\nReverse proxy + static files"]
    end

    subgraph PUSH["External Push Services"]
        VAPID["Web Push (VAPID)\nBrowser Service Worker"]
        TWILIO["Twilio\nSMS · Voice Call"]
        SMTP["SMTP\nEmail alerts"]
    end

    subgraph CLIENT["Client Devices"]
        BROWSER["Desktop Browser\nReact 18 PWA"]
        MOBILE["Mobile Browser\n(Add to Home Screen)\nStandalone PWA"]
        SW_WORKER["Service Worker\n(Workbox)\nOffline cache · Push receiver"]
    end

    ESP32_A -- "WiFi 2.4 GHz" --> AP
    ESP32_B -- "WiFi 2.4 GHz" --> AP
    RPI_A -- "WiFi / Ethernet" --> AP
    RPI_B -- "Ethernet (PoE Switch)" --> SW
    CAM -- "RTSP / PoE" --> SW
    SW --> AP
    AP -- "LAN" --> EMQX

    EMQX -- "MQTT subscribe\ngdf/#" --> FASTAPI
    FASTAPI -- "asyncpg\nINSERT hypertable" --> TSDB
    FASTAPI -- "PUBLISH sensor:reading" --> REDIS
    REDIS -- "SUBSCRIBE sensor:reading" --> SOCKETIO
    SOCKETIO -- "WebSocket\n/socket.io" --> NGINX

    FASTAPI -- "REST /api/**" --> NGINX
    NGINX -- "serves dist/" --> BROWSER
    NGINX -- "serves dist/" --> MOBILE

    FASTAPI -- "pywebpush VAPID" --> VAPID
    FASTAPI -- "Twilio REST" --> TWILIO
    FASTAPI -- "smtplib" --> SMTP

    VAPID --> SW_WORKER
    SW_WORKER --> BROWSER
    SW_WORKER --> MOBILE

    BROWSER -- "HTTPS :443" --> NGINX
    MOBILE -- "HTTPS :443" --> NGINX
```

---

## 2. Physical Sensor Deployment Map

Where each sensor type is physically installed across farm zones.

```mermaid
graph LR
    subgraph BARN["Main Barn (Barn A & B)"]
        B1["ESP32 #1\nTemp + Humidity\n(SHT31)\nCeiling mount"]
        B2["ESP32 #2\nTemp + Humidity\n(SHT31)\nNorth wall"]
        B3["ESP32 #3\nWeight Scale\n(HX711 + load cell)\nFeed trough"]
        B4["IP Camera #1\nRTSP • PoE\nPTZ overview"]
        B5["IP Camera #2\nRTSP • PoE\nMilking stalls"]
        SOLAR_B["12V Solar Panel\n→ TP4056 → 18650\n→ 3.3V LDO → ESP32\n(deep-sleep mode)"]
    end

    subgraph PARLOUR["Milking Parlour"]
        P1["Lactoscan MA\nMilk Analyzer\nRS-232 → RPi #1"]
        P2["RPi #1\n(Lactoscan Bridge)\nSerial /dev/ttyUSB0\n9600 8N1"]
        P3["Milk Tank Scale\n(HX711 × 4 cells)\n→ ESP32"]
        P4["IP Camera #3\nRTSP • PoE\nMilking overview"]
    end

    subgraph PASTURE["Outdoor Pasture"]
        PA1["ESP32 #4\nWeatherproof enclosure\nIP67 box\nTemp + Humidity"]
        PA2["ESP32 #5\nWeight scale\n(outdoor trough)"]
        PA3["Solar Node\n12V 20W panel\n→ charge controller\n→ LiFePO4 battery\n→ ESP32 deep-sleep 25s/wake 5s"]
        PA4["IP Camera #4\nSolar powered\nFence line PTZ"]
    end

    subgraph FEED["Feed Store"]
        F1["ESP32 #6\nSilo weight\n(HX711 + column load cell)"]
        F2["ESP32 #7\nHay loft Temp\n(fire risk monitoring)\nSHT31"]
        F3["IP Camera #5\nFeed store overview"]
    end

    subgraph VET["Vet Bay"]
        V1["Precision Scale\n(HX711 high-res)\n→ ESP32"]
        V2["ESP32 #8\nTemp + Humidity\n(treatment room)"]
        V3["IP Camera #6\nIsolation monitoring"]
    end

    subgraph PROCESSING["Processing Plant"]
        PR1["RPi #2\nLactoscan QC\n(RS-232 Bridge)"]
        PR2["ESP32 #9\nBottle fill scale\n(HX711)"]
        PR3["ESP32 #10\nCarton checkweigher\n(HX711)"]
        PR4["IP Camera #7\nProduction line"]
        PR5["RPi #3\n(Camera HLS Bridge)\nRTSP → ffmpeg → HLS"]
    end

    subgraph UTILITIES["Water & Utilities"]
        U1["ESP32 #11\nWater tank level\n(ultrasonic + HX711)"]
        U2["ESP32 #12\nDiesel tank\n(weight / dipstick analog)"]
        U3["ESP32 #13\nBoiler temp\n(SHT31 + PT100 via MAX31865)"]
    end

    subgraph SERVER_ROOM["Server Room"]
        SRV["Application Server\nDocker Compose stack\nTimescaleDB · EMQX · FastAPI\nRedis · Socket.io · Nginx"]
        UPS["UPS + PoE Switch\n(camera backbone)"]
    end

    B1 & B2 & B3 -.->|"WiFi 2.4 GHz\nMQTT QoS 1"| SRV
    PA1 & PA2 -.->|"WiFi (long-range AP)"| SRV
    F1 & F2 -.->|"WiFi"| SRV
    V1 & V2 -.->|"WiFi"| SRV
    PR2 & PR3 -.->|"WiFi"| SRV
    U1 & U2 & U3 -.->|"WiFi"| SRV
    P2 & P3 -.->|"WiFi / Ethernet"| SRV
    PR1 & PR5 -.->|"Ethernet (PoE Switch)"| UPS
    UPS --> SRV
    B4 & B5 & P4 & PA4 & F3 & V3 & PR4 -.->|"RTSP → RPi Bridge\nor direct to Nginx"| UPS
```

---

## 3. Hardware Wiring & Firmware Configuration

Exact GPIO pins, serial config, and firmware setup for each node type.

```mermaid
graph TD
    subgraph ESP32_TEMP["ESP32 — Temperature & Humidity Node (SHT31)"]
        E1_MCU["ESP32-DevKitC\n3.3V · GND · GPIO21 · GPIO22"]
        E1_SHT31["SHT31 Sensor\n(I2C Address: 0x44)"]
        E1_PWR["3.3V Power Source\n(USB or solar LDO)"]
        E1_MCU -- "SDA → GPIO21\nSCL → GPIO22\n3.3V · GND" --> E1_SHT31
        E1_PWR --> E1_MCU
        E1_FW["Firmware (C++/Arduino)\n- WiFi SSID + password\n- MQTT broker LAN IP:1883\n- sensor_id = 'barn-a-temp-01'\n- topic: gdf/barn-a-temp-01/temperature\n- topic: gdf/barn-a-temp-01/humidity\n- deep-sleep: 25s sleep / 5s wake\n- QoS: 1"]
        E1_MCU --> E1_FW
    end

    subgraph ESP32_WEIGHT["ESP32 — Weight Scale Node (HX711)"]
        E2_MCU["ESP32-DevKitC"]
        E2_HX711["HX711 ADC Module\n24-bit precision"]
        E2_LC["Load Cell\n(50kg / 100kg / 500kg)"]
        E2_MCU -- "DOUT → GPIO4\nSCK  → GPIO5\n3.3V · GND" --> E2_HX711
        E2_HX711 -- "E+ E- A+ A-\n(Wheatstone bridge)" --> E2_LC
        E2_FW["Firmware config\n- capacity_kg: 500\n- unit: 'kg'\n- topic: gdf/{sensor_id}/weight\n- publish every 10s\n- tare offset: calibrate at startup"]
        E2_MCU --> E2_FW
    end

    subgraph RPI_LACTOSCAN["Raspberry Pi 4 — Lactoscan Bridge"]
        R1_RPI["Raspberry Pi 4\n(Raspberry Pi OS Lite)"]
        R1_USB["USB-to-RS-232 Adapter\n(CP2102 / FTDI)"]
        R1_LACT["Lactoscan MA\nMilk Analyzer\nRS-232: 9600 baud 8N1"]
        R1_RPI -- "/dev/ttyUSB0\n(pyserial)\n9600 8N1" --> R1_USB
        R1_USB -- "DB-9 Null-modem\nor straight cable" --> R1_LACT
        R1_FW["lactoscan_bridge.py\n- reads NMEA-style frames\n- parses fat / protein / lactose\n  somatic_cells / milk_temp\n- publishes to EMQX via paho-mqtt\n- topic: gdf/{sensor_id}/{channel}\n- runs as systemd service"]
        R1_RPI --> R1_FW
    end

    subgraph RPI_CAM["Raspberry Pi 4 — IP Camera HLS Bridge"]
        R2_RPI["Raspberry Pi 4"]
        R2_CAM["IP Camera\n(RTSP stream)\n192.168.1.x:554"]
        R2_RPI -- "Ethernet LAN\nffmpeg pull" --> R2_CAM
        R2_FW["camera_hls_bridge.py\n- ffmpeg: RTSP → HLS segments (.m3u8)\n- serves via http on :8888\n- publishes online/offline status\n  to gdf/{sensor_id}/status\n- runs as systemd service"]
        R2_RPI --> R2_FW
        R2_HLS["HLS output\nhttp://rpi-ip:8888/{sensor_id}/index.m3u8\n(consumed by frontend video player)"]
        R2_FW --> R2_HLS
    end

    subgraph SOLAR["Outdoor Solar Power Circuit"]
        SOL_PANEL["12V 20W Solar Panel"]
        SOL_CTRL["TP4056 Charge Controller\nor MPPT controller"]
        SOL_BAT["18650 / LiFePO4 Battery\n3.7V 3000mAh"]
        SOL_LDO["3.3V LDO Regulator\n(AMS1117-3.3)"]
        SOL_ESP["ESP32 Node"]
        SOL_PANEL --> SOL_CTRL --> SOL_BAT --> SOL_LDO --> SOL_ESP
        SOL_NOTE["Deep sleep firmware:\nwake → read sensor → publish MQTT\n→ sleep 25s\nBattery life: ~14 days without sun"]
        SOL_ESP --> SOL_NOTE
    end
```

### Firmware Environment Variables (flashed to ESP32 NVS)

| Variable | Example | Purpose |
|---|---|---|
| `WIFI_SSID` | `GDF-Farm` | Farm WiFi network |
| `WIFI_PASS` | `secret` | WiFi password |
| `MQTT_HOST` | `192.168.1.5` | EMQX broker LAN IP |
| `MQTT_PORT` | `1883` | MQTT port (1883 plain, 8883 TLS) |
| `SENSOR_ID` | `barn-a-temp-01` | Unique sensor identifier (matches DB) |
| `PUBLISH_INTERVAL_MS` | `10000` | How often to read and publish |

### Raspberry Pi systemd Service Setup

```bash
# /etc/systemd/system/lactoscan-bridge.service
[Unit]
Description=Lactoscan MQTT Bridge
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/gdf/lactoscan_bridge.py
Environment="MQTT_HOST=192.168.1.5"
Environment="SENSOR_ID=parlour-lactoscan-01"
Restart=always

[Install]
WantedBy=multi-user.target

# Enable:
sudo systemctl enable --now lactoscan-bridge
```

---

## 4. MQTT Data Flow

Exact path from sensor to stored time-series reading.

```mermaid
sequenceDiagram
    participant ESP32 as ESP32 Node
    participant AP as WiFi AP (LAN)
    participant EMQX as EMQX 5.x Broker<br/>:1883
    participant BRIDGE as FastAPI MQTT Bridge<br/>(aiomqtt subscriber)
    participant ENGINE as Alert Engine<br/>(in-process)
    participant TSDB as TimescaleDB<br/>sensor_readings hypertable
    participant REDIS as Redis Pub/Sub<br/>channel: sensor:reading

    ESP32->>AP: WiFi connect (2.4 GHz)
    AP->>EMQX: LAN route
    ESP32->>EMQX: CONNECT (client_id=barn-a-temp-01, keepalive=60s)
    EMQX-->>ESP32: CONNACK

    loop Every 10 seconds
        ESP32->>EMQX: PUBLISH QoS 1<br/>topic: gdf/barn-a-temp-01/temperature<br/>payload: {"value": 22.4, "unit": "°C", "ts": "2026-04-28T08:00:00Z"}
        EMQX-->>ESP32: PUBACK
        EMQX->>BRIDGE: Delivers message (subscribed to gdf/#)
        BRIDGE->>BRIDGE: Parse topic → sensor_id + channel<br/>Parse payload → value + ts
        BRIDGE->>TSDB: INSERT INTO sensor_readings<br/>(sensor_id, channel, value, unit, recorded_at)
        BRIDGE->>ENGINE: evaluate_rules(sensor_id, channel, value)
        ENGINE->>TSDB: SELECT alert_rules WHERE sensor_id + channel
        ENGINE->>TSDB: INSERT INTO active_alerts (if triggered)
        ENGINE->>REDIS: PUBLISH sensor:reading JSON
        REDIS-->>BRIDGE: (async, non-blocking)
    end

    Note over ESP32,REDIS: MQTT topic format: gdf/{sensor_id}/{channel}<br/>Examples: gdf/abc-123/temperature · gdf/abc-123/humidity · gdf/abc-123/weight
```

### MQTT Topic Reference

| Sensor Type | Example Topic | Payload Keys |
|---|---|---|
| Temperature/Humidity | `gdf/{id}/temperature` + `gdf/{id}/humidity` | `value`, `unit`, `ts` |
| Weight Scale | `gdf/{id}/weight` | `value` (kg), `unit`, `ts` |
| Milk Analyzer | `gdf/{id}/fat`, `/protein`, `/lactose`, `/somatic_cells`, `/milk_temp` | `value`, `unit`, `ts` |
| Camera (status) | `gdf/{id}/status` | `value` (1=online/0=offline), `ts` |

---

## 5. Backend Services Architecture

All FastAPI background services and their database/cache interactions.

```mermaid
graph TD
    subgraph FASTAPI_PROC["FastAPI Process (uvicorn :8001)"]
        REST["REST API Routers\n/api/sensors\n/api/telemetry\n/api/alerts\n/api/tasks\n/api/plans\n/api/users\n/api/push\n/api/auth"]

        subgraph BACKGROUND["Background Services (asyncio tasks)"]
            MQTT_BRIDGE["MQTT Bridge\n(aiomqtt)\nSubscribes gdf/#\nIngests readings"]
            ALERT_ENG["Alert Engine\nalert_engine.py\nEvaluates gt/lt/eq/outside_range\non every reading (<5ms)"]
            PLAN_SVC["Plan Action Service\nplan_action_service.py\nFires on threshold breach:\nnotification · sms · call · reminder"]
            TASK_SCHED["Task Reminder Scheduler\n(APScheduler every 30min)\nChecks deadline ≤ 24h\nSends push reminder"]
        end

        PLUGIN_REG["Sensor Plugin Registry\nplugins/registry.py\nauto-discovers plugins/types/\ntemperature_humidity\nweight_hx711\nmilk_analyzer_lactoscan\nip_camera_rtsp"]

        PUSH_SVC["Push Service\npush.py\npywebpush VAPID\nFilters by RBAC + push_enabled"]
        TWILIO_SVC["Twilio Service\ntwilio_service.py\nSMS via REST API\nVoice via TwiML"]
        EMAIL_SVC["Email Service\nsmtplib / aiosmtplib\nSMTP alert emails"]
    end

    subgraph DB["TimescaleDB :5432"]
        SENSORS["sensors\n(id, name, sensor_type,\nprotocol, location_id,\nconfig JSONB, is_active)"]
        READINGS["sensor_readings (hypertable)\n(sensor_id, channel, value,\nunit, recorded_at)\n7-day chunks\n90-day compression\ncontinuous aggregates"]
        ALERTS_TBL["alert_rules + alert_rule_actions\n(sensor_id, channel, condition,\nthreshold, severity, actions)"]
        ACTIVE_ALERTS["active_alerts\n(rule_id, triggered_value,\nmessage, triggered_at)"]
        TASKS_TBL["tasks + task_attachments\ntask_assignees\n(title, deadline, status,\nassignee_ids, files)"]
        PLANS_TBL["plans + plan_actions\n(sensor_id, channel, target,\nmin_val, max_val, actions)"]
        USERS_TBL["users + user_location_permissions\n+ user_sensor_permissions\n+ push_subscriptions\n(RBAC: super_admin/admin/operator)"]
        NOTIFS["notifications\n(user_id, title, body,\nread_at, created_at)"]
    end

    subgraph CACHE["Redis :6379"]
        PUBSUB["Pub/Sub channels\nsensor:reading\nalert:triggered"]
        SESSION["JWT blocklist\n(token revocation)"]
    end

    MQTT_BRIDGE -->|"every reading"| ALERT_ENG
    MQTT_BRIDGE --> READINGS
    ALERT_ENG --> PLAN_SVC
    ALERT_ENG --> ACTIVE_ALERTS
    PLAN_SVC --> PUSH_SVC
    PLAN_SVC --> TWILIO_SVC
    PLAN_SVC --> EMAIL_SVC
    PLAN_SVC --> NOTIFS
    TASK_SCHED --> PUSH_SVC
    TASK_SCHED --> NOTIFS
    MQTT_BRIDGE --> PUBSUB
    REST --> SENSORS & READINGS & ALERTS_TBL & TASKS_TBL & PLANS_TBL & USERS_TBL & NOTIFS
    REST --> SESSION
    PLUGIN_REG -.->|"GET /api/sensors/types"| REST
```

### TimescaleDB Hypertable Config

```sql
-- sensor_readings is the hypertable:
SELECT create_hypertable('sensor_readings', 'recorded_at', chunk_time_interval => INTERVAL '7 days');

-- 90-day compression:
ALTER TABLE sensor_readings SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'sensor_id, channel'
);
SELECT add_compression_policy('sensor_readings', INTERVAL '90 days');

-- Continuous aggregate (hourly averages):
CREATE MATERIALIZED VIEW readings_hourly
WITH (timescaledb.continuous) AS
SELECT sensor_id, channel,
       time_bucket('1 hour', recorded_at) AS bucket,
       AVG(value) AS avg_value, MIN(value), MAX(value)
FROM sensor_readings
GROUP BY sensor_id, channel, bucket;
```

---

## 6. Real-Time Update Flow

Full pipeline from sensor reading to React component re-render.

```mermaid
sequenceDiagram
    participant MQTT as EMQX Broker
    participant BRIDGE as FastAPI MQTT Bridge
    participant TSDB as TimescaleDB
    participant REDIS as Redis Pub/Sub<br/>channel: sensor:reading
    participant GW as Socket.io Gateway<br/>(Node.js :3001)
    participant NGINX as Nginx :443
    participant WS as WebSocket<br/>(browser)
    participant STORE as Zustand Store<br/>useSensorStore
    participant COMP as React Component<br/>(Monitoring page)

    MQTT->>BRIDGE: deliver gdf/{sensor_id}/{channel} payload
    BRIDGE->>TSDB: INSERT reading (async, awaited)
    BRIDGE->>REDIS: PUBLISH sensor:reading<br/>{"sensor_id":"...","channel":"temperature","value":22.4,"unit":"°C","ts":"..."}
    REDIS->>GW: delivers to subscriber (ioredis)
    GW->>GW: parse JSON, emit to room sensor:{sensor_id}
    GW->>WS: socket.emit('reading', payload)<br/>(all clients subscribed to that sensor)
    WS->>NGINX: WebSocket over /socket.io path
    Note over WS,NGINX: Nginx proxies /socket.io → :3001

    WS->>STORE: socket.on('reading', (data) => {<br/>  useSensorStore.getState().updateReading(data)<br/>})
    STORE->>COMP: Zustand selector triggers re-render<br/>component shows new value instantly

    Note over BRIDGE,COMP: Total latency sensor→pixel: ~100–300ms over LAN
    Note over WS,STORE: TanStack Query polls /api/telemetry every 60s as fallback<br/>Socket.io delivers live updates between polls
```

### Socket.io Room Strategy

```
Client subscribes: socket.emit('subscribe', { sensor_id: 'barn-a-temp-01' })
Server joins room:  socket.join(`sensor:barn-a-temp-01`)
Server broadcasts:  io.to(`sensor:barn-a-temp-01`).emit('reading', payload)

Alert room:  socket.join('alerts')
Server:      io.to('alerts').emit('alert', { rule_id, severity, message })
```

---

## 7. Notification & Alert Pipeline

Every path from a rule breach to a human being notified.

```mermaid
flowchart TD
    READ["Sensor Reading Ingested\nvalue=35.2°C sensor=barn-a-temp-01"]

    subgraph ENGINE["Alert Engine (alert_engine.py)"]
        LOAD["Load alert_rules WHERE\nsensor_id = 'barn-a-temp-01'\nAND channel = 'temperature'\nAND enabled = true"]
        EVAL{{"Evaluate condition\ngt · lt · eq · outside_range"}}
        PASS["Rule NOT triggered\n→ skip"]
        TRIG["Rule triggered!\nSeverity: critical\nthreshold: 34°C, actual: 35.2°C"]
        INSERT_ALERT["INSERT INTO active_alerts\n(rule_id, triggered_value, message, triggered_at)"]
    end

    subgraph PLAN_SVC["Plan Action Service (plan_action_service.py)"]
        LOAD_ACTIONS["Load alert_rule_actions\nfor this rule_id"]
        RBAC["Filter: users with\nRBAC access to sensor\n+ push_enabled for severity"]
    end

    subgraph PATHS["Notification Paths (parallel)"]
        WEB_PUSH["notification action\n→ push_service.send_push()\n→ pywebpush VAPID POST\n→ Browser Push API\n→ Service Worker\n→ showNotification()"]

        SMS["sms action\n→ twilio_service.send_sms()\n→ Twilio REST API\n→ SMS to user.phone"]

        CALL["call action\n→ twilio_service.make_call()\n→ Twilio TwiML Voice\n→ Automated voice call\n→ reads alert message aloud"]

        EMAIL["email action\n→ aiosmtplib\n→ SMTP server\n→ Email to user.email\nwith sensor details + value"]

        REMINDER["reminder action\n→ INSERT INTO notifications\n(in-app bell icon)\n→ delivered via Socket.io\n'notification' event\n+ next poll"]
    end

    subgraph MOBILE["Mobile / Desktop"]
        SW_NOTE["Service Worker\nonpush event\n→ self.registration.showNotification()\n(works when browser is closed)"]
        BELL["In-app bell icon\nNotifications page\n/notifications"]
        PHONE_SMS["SMS inbox\n(native phone app)"]
        PHONE_CALL["Incoming voice call\n(Twilio reads message)"]
        EMAIL_BOX["Email inbox"]
    end

    READ --> LOAD --> EVAL
    EVAL -- "not triggered" --> PASS
    EVAL -- "triggered" --> TRIG --> INSERT_ALERT --> LOAD_ACTIONS --> RBAC

    RBAC --> WEB_PUSH --> SW_NOTE
    RBAC --> SMS --> PHONE_SMS
    RBAC --> CALL --> PHONE_CALL
    RBAC --> EMAIL --> EMAIL_BOX
    RBAC --> REMINDER --> BELL

    SW_NOTE -->|"tap notification"| BELL

    style WEB_PUSH fill:#065f46,color:#fff
    style SMS fill:#1e3a5f,color:#fff
    style CALL fill:#4a1942,color:#fff
    style EMAIL fill:#3b2f00,color:#fff
    style REMINDER fill:#1a1a2e,color:#fff
```

### Task Deadline Reminder Flow

```
APScheduler (every 30 min):
  → SELECT tasks WHERE deadline BETWEEN now() AND now() + 24h
     AND status IN ('open', 'rejected')
  → for each assignee:
      INSERT INTO notifications (user_id, title='Task due soon', body=task.title)
      push_service.send_push(user_id, title, body)
```

---

## 8. Frontend PWA Architecture & Mobile Install

From Vite build to installable standalone app on any device.

```mermaid
graph TD
    subgraph BUILD["Build Pipeline (CI/CD)"]
        SRC["React 18 + TypeScript\nsrc/ components, pages, hooks"]
        VITE["Vite 5\n(vite.config.ts)\nVitePWA plugin\n+ Workbox"]
        DIST["dist/\nindex.html\nassets/ (hashed chunks)\nmanifest.webmanifest\nsw.js (Service Worker)\nicons/"]
        SRC --> VITE --> DIST
    end

    subgraph NGINX_SERVE["Nginx (serves built frontend)"]
        NGINX2["nginx.conf\nroot /usr/share/nginx/html (= dist/)\nlocation /api → proxy :8001\nlocation /socket.io → proxy :3001\ntry_files $uri /index.html (SPA routing)\ngzip + Cache-Control headers"]
    end

    subgraph SW_LAYER["Service Worker (sw.js via Workbox)"]
        SW_INSTALL["install event\n→ precache hashed assets\n(JS, CSS, icons, fonts)"]
        SW_FETCH["fetch event\nNetworkFirst: /api/**\nCacheFirst: assets/**\nStaleWhileRevalidate: index.html"]
        SW_PUSH["push event\n→ parse JSON payload\n→ self.registration.showNotification()\n   title, body, icon, badge, data.url\n→ tapping opens /notifications"]
        SW_INSTALL --> SW_FETCH
        SW_INSTALL --> SW_PUSH
    end

    subgraph REACT_APP["React App (runtime)"]
        AUTH["AuthContext\nJWT from localStorage gdf_token\n→ injected by apiFetch()\nRefreshes on 401"]
        ROUTER["React Router v6\n/ Dashboard\n/monitoring\n/sensors\n/tasks/:id\n/planning\n/alerts\n/notifications\n/settings\n/users\n/locations"]
        QUERY["TanStack Query v5\nuseQuery + refetchInterval\nStale-while-revalidate\nBackground refetch on focus"]
        ZUSTAND["Zustand Store\nsensorStore — live readings\nupdated by Socket.io events\n→ Monitoring page cards"]
        SOCKET["Socket.io Client\nauto-reconnect\nsubscribes sensor rooms\non('reading') → sensorStore\non('alert') → toast + bell"]
        PUSH_REG["Push Registration\nnavigator.serviceWorker\n.pushManager.subscribe(VAPID_KEY)\n→ POST /api/push/subscribe"]
    end

    subgraph PWA_INSTALL["PWA Install (mobile + desktop)"]
        MANIFEST["manifest.webmanifest\nname: GDF-AutoMon\nshort_name: GDF\ndisplay: standalone\ntheme_color: #059669\nstart_url: /\nicons: 192px + 512px"]
        PROMPT["Browser install prompt\n(beforeinstallprompt event)\nor iOS: Share → Add to Home Screen"]
        HOME_SCREEN["Icon on Home Screen\nLaunches in standalone mode\n(no browser chrome)\nFull-screen PWA experience"]
        OFFLINE["Offline mode\nCached pages load instantly\nStale data shown\nAPI calls queue (or fail gracefully)"]
        MANIFEST --> PROMPT --> HOME_SCREEN --> OFFLINE
    end

    DIST --> NGINX2
    NGINX2 -- "serves sw.js" --> SW_LAYER
    NGINX2 -- "serves index.html + assets" --> REACT_APP
    NGINX2 -- "serves manifest.webmanifest" --> PWA_INSTALL
    REACT_APP --> AUTH & ROUTER & QUERY & ZUSTAND & SOCKET & PUSH_REG
    SW_LAYER --> OFFLINE
```

### PWA Install — Step by Step

| Step | Desktop Chrome | iOS Safari | Android Chrome |
|---|---|---|---|
| 1 | Visit `https://farm.yourdomain.com` | Visit site | Visit site |
| 2 | Address bar shows install icon | Tap Share button | Chrome shows banner |
| 3 | Click "Install GDF-AutoMon" | Tap "Add to Home Screen" | Tap "Add to Home Screen" |
| 4 | App opens in own window | App icon on home screen | App icon on home screen |
| 5 | No browser chrome, standalone | Launches in standalone | Launches in standalone |
| 6 | Push notifications work | Push notifications work* | Push notifications work |

*iOS 16.4+ supports Web Push for installed PWAs.

---

## 9. Tech Stack Roles

### EMQX 5.x — MQTT Broker
**Role:** Message hub that receives all sensor readings from ESP32/RPi nodes and delivers them to the FastAPI subscriber.
- **Why MQTT?** Lightweight 2-4 byte protocol header vs HTTP's 200+ bytes — critical for battery-powered ESP32 nodes on 2.4 GHz WiFi
- **QoS 1:** "At least once" delivery guarantees no readings are silently dropped when the broker is briefly unreachable
- **Fan-out:** Multiple consumers can subscribe to `gdf/#` without the sensor knowing how many listeners exist
- **EMQX features used:** topic ACLs (per-sensor auth), dashboard, retained messages (last known value), built-in WebSocket MQTT bridge

### TimescaleDB — Time-Series Database
**Role:** Stores every sensor reading with nanosecond-precision timestamps; powers historical charts and aggregated dashboards.
- **Why time-series?** Standard PostgreSQL tables degrade on time-range queries at millions of rows; hypertables partition by time automatically
- **Hypertable:** `sensor_readings` partitioned into 7-day chunks — each chunk is an independent PostgreSQL table, queries only scan relevant chunks
- **Continuous aggregates:** Pre-computed hourly/daily averages served in milliseconds instead of scanning raw data
- **90-day compression:** Older chunks compressed ~10:1 while remaining queryable; disk usage stays manageable
- **asyncpg:** Python async PostgreSQL driver — no thread pool needed, plays well with FastAPI's async event loop

### Redis 7 — Pub/Sub & Cache
**Role:** Decouples the FastAPI MQTT bridge from the Socket.io gateway; allows horizontal scaling of either without coupling.
- **Why Pub/Sub?** FastAPI publishes one message; every Socket.io instance (however many) subscribes and receives it — true fan-out
- **Why not call Socket.io directly?** That would create a hard dependency between the Python process and the Node.js process; Redis makes them independently restartable
- **Session use:** JWT blocklist — tokens added here on logout; checked on every authenticated request

### FastAPI (Python 3.12) — Backend API + Engine
**Role:** REST API for the frontend, MQTT data ingestion, alert evaluation, plan execution, push delivery, and task scheduling.
- **Async throughout:** `async def` handlers + `await` DB calls = thousands of concurrent connections without threads
- **RBAC middleware:** `get_current_user` dependency checks JWT, `require_permission` checks `user_location_permissions` / `user_sensor_permissions`
- **Plugin registry:** `plugins/registry.py` auto-discovers `plugins/types/*.py` — adding a new sensor type requires zero changes to any existing file
- **Background tasks:** `aiomqtt` subscriber, `APScheduler` for deadline reminders — all run inside the same uvicorn process

### Socket.io Gateway (Node.js 20 + Fastify)
**Role:** WebSocket server that fans out real-time sensor readings to browser clients.
- **Why separate from FastAPI?** WebSocket connections are long-lived; Python's asyncio handles them but Node.js's event loop is battle-tested for 10,000+ concurrent WebSocket connections
- **ioredis subscriber:** Listens to Redis `sensor:reading` channel; delivers to the relevant `sensor:{id}` Socket.io room
- **Room isolation:** Clients only receive readings for sensors they subscribe to — no RBAC bypass possible at the WebSocket layer
- **Auto-reconnect:** Socket.io client reconnects with exponential backoff when the server restarts

### React 18 + Vite PWA — Frontend
**Role:** The user interface — dashboards, sensor management, tasks, alerts, planning, notifications, and settings.
- **TanStack Query v5:** Manages all server state with stale-while-revalidate; `refetchInterval` provides automatic background polling as a Socket.io fallback
- **Zustand:** Holds live sensor readings updated by Socket.io events; components subscribe to individual slices without re-rendering unrelated parts
- **VitePWA + Workbox:** Generates Service Worker and web manifest at build time; `NetworkFirst` strategy keeps API data fresh while serving cached assets instantly
- **Offline mode:** Cached shell loads immediately; stale telemetry shown from Workbox cache; critical for farm environments with patchy coverage

### ESP32 — Edge Sensor Node
**Role:** Reads sensors and publishes MQTT messages over WiFi. Costs ~$4, runs on 3.3V, has I2C + SPI + UART.
- **Deep-sleep:** Powers down all peripherals between reads; ~2mA active → µA sleep — months of battery life from 18650 cell
- **Arduino SDK:** `WiFi.h` + `PubSubClient.h` = 200 lines of C++ per node type
- **Configuration:** SSID, password, MQTT broker IP, and `sensor_id` flashed once into NVS (Non-Volatile Storage)

### Raspberry Pi 4 — Edge Bridge Node
**Role:** Handles serial protocols (Lactoscan RS-232) and computationally heavy tasks (ffmpeg RTSP transcoding to HLS) that ESP32 cannot do.
- **Why RPi?** Full Linux OS needed for USB serial drivers, Python parsing of proprietary analyzer protocols, and ffmpeg
- **systemd services:** Each bridge runs as a service with `Restart=always` — survives crashes and reboots automatically
- **Wired Ethernet preferred:** For camera HLS bridges — ffmpeg needs sustained ~2 Mbps, WiFi may drop frames

### VAPID Web Push — Browser Notifications
**Role:** Delivers push notifications to users even when the browser tab is closed.
- **Why VAPID?** Does not require Google FCM or Apple APNs — works directly with browser push services using standard W3C Web Push API
- **Flow:** Server signs payload with VAPID private key → sends to browser-specific push endpoint → browser decrypts and wakes Service Worker
- **iOS support:** iOS 16.4+ supports Web Push for PWAs added to home screen
- **RBAC filtering:** `push_service.py` only sends to users with access to the sensor's location + `push_enabled` preference matching the alert severity

### Twilio — SMS & Voice Calls
**Role:** Reaches users who are not at a computer — field workers, night-shift staff, or on-call personnel.
- **SMS:** Instant text message with sensor name, value, and alert severity; no app needed to receive
- **Voice call:** Twilio TwiML reads the alert message aloud — used for `critical` severity when the user may not see their phone screen
- **Fallback hierarchy:** notification → SMS → call, escalating based on `alert_rule_actions` configuration

### Nginx — Reverse Proxy
**Role:** Single entry point for all HTTPS traffic; terminates TLS, serves static frontend, proxies API and WebSocket.
- **TLS termination:** Let's Encrypt cert or self-signed for LAN; backend services never handle TLS
- **SPA routing:** `try_files $uri /index.html` — all non-asset URLs return `index.html`, letting React Router handle routing
- **Proxy:** `/api/` → FastAPI `:8001`; `/socket.io/` → Socket.io gateway `:3001` with WebSocket upgrade headers

---

## 10. Wireless Network Setup

### Recommended Farm Network Layout

```
Internet (optional)
      │
   Router / Firewall
      │
  Core PoE Switch (24-port)
   ├── Ubiquiti UniFi AP (Barn A)
   ├── Ubiquiti UniFi AP (Barn B)
   ├── Ubiquiti UniFi AP (Parlour)
   ├── Ubiquiti UniFi AP (Processing Plant)
   ├── Ubiquiti UAP-AC-M (outdoor, Pasture)
   ├── IP Camera #1 (PoE)
   ├── IP Camera #2 (PoE)
   ├── ... (all cameras on PoE)
   └── Application Server (wired Gigabit)
```

### WiFi Configuration

| Setting | Value |
|---|---|
| SSID | `GDF-Farm` (5 GHz for RPi), `GDF-Farm-IoT` (2.4 GHz for ESP32) |
| Security | WPA2-Personal (WPA3 if all devices support it) |
| MQTT broker IP | Static LAN IP, e.g. `192.168.1.5` |
| MQTT port | `1883` (plain LAN), `8883` (TLS if exposed) |
| DHCP reservations | Assign static IPs to all RPi + server by MAC address |
| VLANs (optional) | IoT VLAN isolated from office; server in management VLAN |

### Outdoor / Pasture Nodes

```
12V 20W Solar Panel
    → MPPT Charge Controller (e.g. Victron 75/10)
    → 12V LiFePO4 Battery (10Ah)
    → 12V→3.3V Buck Converter
    → ESP32 in IP67 weatherproof enclosure

Deep-sleep firmware cycle:
  1. Wake from deep-sleep (GPIO 0 or timer)
  2. Connect WiFi (~500ms)
  3. Connect MQTT (~100ms)
  4. Read sensor (~50ms)
  5. Publish reading (~100ms)
  6. Disconnect WiFi
  7. Deep-sleep 25 seconds

Battery life estimate: 10Ah / (20mA avg) ≈ 21 days without sun
```

### Long-Range Coverage

For pastures >100m from the nearest AP:
- **Ubiquiti UAP-AC-M** (mesh, outdoor rated) — 300m range
- **Ubiquiti AirMax NanoStation** (point-to-point bridge) — up to 5km
- **4G/LTE fallback** — SIM800L module on ESP32 for isolated fields; publishes MQTT over cellular

---

## 11. Docker Compose Deployment Reference

### Services, Ports, and Startup Order

```mermaid
graph LR
    TSDB2["timescaledb\n:5432\nVolume: tsdb_data\nenv: POSTGRES_*"]
    REDIS2["redis\n:6379\nVolume: redis_data\nno auth on LAN"]
    EMQX2["emqx\n:1883 MQTT\n:8883 MQTT TLS\n:18083 Dashboard\nVolume: emqx_data"]
    BACKEND["backend (FastAPI)\n:8001\nDepends: timescaledb, redis, emqx\nenv: DATABASE_URL, MQTT_HOST,\nVAPID_*, SECRET_KEY, TWILIO_*"]
    REALTIME["realtime (Socket.io)\n:3001\nDepends: redis\nenv: REDIS_URL, PORT=3001"]
    NGINX2["nginx\n:80 → redirect HTTPS\n:443 TLS\nDepends: backend, realtime\nVolume: dist/ (built frontend)"]

    TSDB2 --> BACKEND
    REDIS2 --> BACKEND
    EMQX2 --> BACKEND
    REDIS2 --> REALTIME
    BACKEND --> NGINX2
    REALTIME --> NGINX2
```

### docker-compose.yml Summary

```yaml
version: "3.9"
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: gdf
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: gdfautomon
    volumes: [tsdb_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]

  emqx:
    image: emqx/emqx:5
    ports: ["1883:1883", "8883:8883", "18083:18083"]
    volumes: [emqx_data:/opt/emqx/data]

  backend:
    build: ./backend
    ports: ["8001:8001"]
    depends_on: [timescaledb, redis, emqx]
    env_file: ./infra/.env
    volumes: [./backend/uploads:/app/uploads]

  realtime:
    build: ./realtime
    ports: ["3001:3001"]
    depends_on: [redis]
    environment:
      REDIS_URL: redis://redis:6379
      PORT: 3001

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [backend, realtime]
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./infra/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./infra/certs:/etc/nginx/certs:ro

volumes:
  tsdb_data:
  redis_data:
  emqx_data:
```

### Environment Variables Reference

```bash
# infra/.env (copy from .env.example, never commit)
DATABASE_URL=postgresql+asyncpg://gdf:password@timescaledb:5432/gdfautomon
MQTT_HOST=emqx
MQTT_PORT=1883
REDIS_URL=redis://redis:6379
SECRET_KEY=<64-char random hex>
VAPID_PRIVATE_KEY=<base64url from gen-vapid-keys.sh>
VAPID_PUBLIC_KEY=<base64url from gen-vapid-keys.sh>
VAPID_EMAIL=admin@yourdomain.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx        # optional
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx           # optional
TWILIO_FROM_NUMBER=+1234567890              # optional
SMTP_HOST=smtp.gmail.com                     # optional
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=app-password
UPLOAD_DIR=/app/uploads
```

### First-Time Deployment

```bash
# 1. Clone and configure
git clone https://github.com/yourorg/GDF-AutoMon
cd GDF-AutoMon/infra
cp .env.example .env
bash scripts/gen-vapid-keys.sh   # generates VAPID key pair into .env

# 2. Start infrastructure
docker compose up -d timescaledb redis emqx
sleep 10  # wait for DB to be ready

# 3. Run migrations
bash scripts/init-db.sh          # runs alembic upgrade head inside backend container

# 4. Build frontend
cd ../frontend && npm ci && npm run build
cp -r dist/ ../infra/            # or docker build copies it

# 5. Start all services
cd ../infra && docker compose up -d

# 6. Seed demo data (optional)
docker exec -it gdf-backend python scripts/seed.py

# 7. Verify
curl https://localhost/api/sensors   # should return sensor list
docker logs -f gdf-backend           # watch MQTT ingestion logs
# Open https://localhost → login with seeded admin user
```

---

*Architecture version: April 2026 · GDF-AutoMon v1.x*
