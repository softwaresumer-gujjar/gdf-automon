# GDF-AutoMon — Layer & Data Flow Diagrams

Each diagram zooms into a single layer or a specific end-to-end scenario. Read them in order for the full picture, or jump to the scenario you care about.

---

## Contents

**Layers (what exists at rest)**
- [L1 — Physical Sensor Layer](#l1--physical-sensor-layer)
- [L2 — Edge Firmware Layer](#l2--edge-firmware-layer)
- [L3 — Wireless Network Layer](#l3--wireless-network-layer)
- [L4 — MQTT Broker Layer](#l4--mqtt-broker-layer)
- [L5 — Application Server Layer](#l5--application-server-layer)
- [L6 — Host & Infrastructure Layer](#l6--host--infrastructure-layer)
- [L7 — Client Delivery Layer](#l7--client-delivery-layer)

**Data Flows (what moves at runtime)**
- [F1 — Sensor Reading → Live Dashboard](#f1--sensor-reading--live-dashboard)
- [F2 — Alert Threshold Breach → Push Notification](#f2--alert-threshold-breach--push-notification)
- [F3 — Alert Breach → Twilio SMS & Voice Call](#f3--alert-breach--twilio-sms--voice-call)
- [F4 — User Opens Historical Chart](#f4--user-opens-historical-chart)
- [F5 — Task Deadline Reminder](#f5--task-deadline-reminder)
- [F6 — PWA Install & First Offline Load](#f6--pwa-install--first-offline-load)
- [F7 — New Sensor Registered (Admin Flow)](#f7--new-sensor-registered-admin-flow)
- [F8 — Full End-to-End: Sensor Spike to Resolved Alert](#f8--full-end-to-end-sensor-spike-to-resolved-alert)

---

## L1 — Physical Sensor Layer

What sensors are physically attached to what hardware, and how.

```mermaid
graph TD
    subgraph ESP32_NODE["ESP32 Node (3.3V, 240 MHz dual-core)"]
        direction TB
        MCU["ESP32-WROOM-32\n─────────────────\nGPIO 21 SDA\nGPIO 22 SCL\nGPIO  4 DOUT\nGPIO  5 SCK\nGPIO 34 ADC\n3.3V · GND"]
    end

    subgraph I2C_BUS["I2C Bus (SDA=21, SCL=22, 100 kHz)"]
        SHT31["SHT31-DIS\nTemp + Humidity\nAddr 0x44\n±0.3°C · ±2% RH"]
        BMP280["BMP280 (optional)\nAtmos. Pressure\nAddr 0x76"]
    end

    subgraph SPI_HX["SPI-like (DOUT=4, SCK=5)"]
        HX711["HX711 24-bit ADC\nGain 128× (channel A)\n80 SPS / 10 SPS"]
        LC["Load Cell\nWheatstone bridge\nE+ E− A+ A−\n50 kg / 200 kg / 500 kg"]
        HX711 <--> LC
    end

    subgraph ANALOG["ADC GPIO34 (0–3.3V)"]
        FLOAT["Float sensor\n(water tank level)\nresistive divider"]
        SOIL["Soil moisture\ncapacitive probe"]
    end

    subgraph POWER["Power Supply"]
        USB["USB 5V → onboard LDO → 3.3V\n(bench / wall adapter)"]
        SOLAR_CHAIN["Solar panel 12V\n→ MPPT controller\n→ LiFePO4 3.7V\n→ ME6206 LDO 3.3V"]
    end

    MCU <-- "I2C" --> I2C_BUS
    MCU <-- "pseudo-SPI" --> SPI_HX
    MCU <-- "ADC" --> ANALOG
    POWER --> MCU

    subgraph RPI_NODE["Raspberry Pi 4 (Linux, 1.5 GHz ARM)"]
        RPI_CPU["BCM2711\n─────────────────\nUSB 2/3 ports\nGigabit Ethernet\nGPIO header (40-pin)\n4 GB RAM"]
    end

    subgraph USB_SERIAL["USB Serial (pyserial)"]
        ADAPTER["CP2102 / FTDI\nUSB-to-RS-232\n/dev/ttyUSB0"]
        LACTOSCAN["Lactoscan MA\nMilk Analyzer\nRS-232 DB-9\n9600 8N1\nOutputs: fat% protein%\nlactose% SCC milk_temp"]
        ADAPTER <-- "DB-9 cable" --> LACTOSCAN
    end

    subgraph NETWORK_ETH["Ethernet (GbE)"]
        IPCAM["IP Camera\nRTSP stream\n1920×1080 H.264\n15–30 FPS\n192.168.x.x:554"]
    end

    RPI_CPU <-- "USB" --> USB_SERIAL
    RPI_CPU <-- "Ethernet / WiFi" --> NETWORK_ETH
```

---

## L2 — Edge Firmware Layer

The code running on each edge device — what it does step by step.

```mermaid
flowchart TD
    subgraph ESP32_FW["ESP32 Firmware (C++ / Arduino SDK)"]
        direction TB
        BOOT["Power ON / Wake from deep-sleep"]
        WIFI_INIT["WiFi.begin(SSID, PASS)\nWait for IP (timeout 10s)"]
        MQTT_CONN["PubSubClient.connect()\nbroker=192.168.1.5 port=1883\nclient_id=sensor_id\nkeepAlive=60s"]
        READ_SENSOR{{"Sensor type?"}}

        READ_SHT31["Wire.begin(21,22)\nsht31.readTemperature()\nsht31.readHumidity()"]
        READ_HX711["HX711.begin(4,5)\nHX711.get_units(5) → avg 5 readings\napply tare offset + calibration factor"]
        READ_ADC["analogRead(GPIO34)\nmap(0,4095, 0, 100) → percentage"]

        BUILD_MSG["Build JSON payload:\n{value: X, unit: '°C', ts: ISO8601}\nor {value: X, unit: 'kg', ts: ...}"]
        PUBLISH["client.publish(\n  'gdf/{sensor_id}/{channel}',\n  payload,\n  QoS=1,\n  retain=false\n)"]
        SLEEP{{"Deep sleep\nenabled?"}}
        DELAY["delay(publish_interval_ms)\n→ loop"]
        DEEPSLEEP["esp_sleep_enable_timer_wakeup\n  (25_000_000 µs = 25s)\nesp_deep_sleep_start()"]

        BOOT --> WIFI_INIT --> MQTT_CONN --> READ_SENSOR
        READ_SENSOR -- "SHT31" --> READ_SHT31
        READ_SENSOR -- "HX711" --> READ_HX711
        READ_SENSOR -- "ADC" --> READ_ADC
        READ_SHT31 & READ_HX711 & READ_ADC --> BUILD_MSG --> PUBLISH
        PUBLISH --> SLEEP
        SLEEP -- "No (mains power)" --> DELAY --> READ_SENSOR
        SLEEP -- "Yes (battery/solar)" --> DEEPSLEEP --> BOOT
    end

    subgraph RPI_LACT["RPi: lactoscan_bridge.py (systemd service)"]
        direction TB
        L_INIT["ser = serial.Serial('/dev/ttyUSB0', 9600)\nmqtt = paho.mqtt.Client()"]
        L_CONNECT["mqtt.connect(MQTT_HOST, 1883)\nmqtt.loop_start()"]
        L_READ["line = ser.readline().decode()\n# Lactoscan outputs CSV frames:\n# FAT=3.85,PROT=3.20,LACT=4.71,SCC=185,TEMP=38.2"]
        L_PARSE["parse_frame(line)\n→ {'fat':3.85,'protein':3.20,\n   'lactose':4.71,'somatic_cells':185,\n   'milk_temp':38.2}"]
        L_PUB["for channel, value in parsed:\n  mqtt.publish(\n    f'gdf/{SENSOR_ID}/{channel}',\n    json.dumps({'value':value,'unit':unit,'ts':now_iso()}),\n    qos=1\n  )"]
        L_INIT --> L_CONNECT --> L_READ --> L_PARSE --> L_PUB --> L_READ
    end

    subgraph RPI_CAM["RPi: camera_hls_bridge.py (systemd service)"]
        direction TB
        C_INIT["ffmpeg_cmd = [\n  'ffmpeg', '-i', RTSP_URL,\n  '-c:v', 'copy',\n  '-hls_time', '2',\n  '-hls_list_size', '5',\n  '-hls_flags', 'delete_segments',\n  f'{OUTPUT_DIR}/{SENSOR_ID}/index.m3u8'\n]"]
        C_START["subprocess.Popen(ffmpeg_cmd)\nServe HLS via http.server on :8888"]
        C_HEALTH["Watchdog thread (every 30s):\n  check ffmpeg alive\n  publish gdf/{SENSOR_ID}/status\n  payload: {value:1,unit:'bool',ts:...}"]
        C_RESTART["If ffmpeg died:\n  restart process\n  publish status=0 briefly"]
        C_INIT --> C_START --> C_HEALTH --> C_RESTART --> C_HEALTH
    end
```

---

## L3 — Wireless Network Layer

How every device connects, what protocol runs over which medium.

```mermaid
graph TD
    subgraph INTERNET["Internet (optional)"]
        WAN["ISP / 4G Router\nPublic IP or CGNAT"]
        DNS["DNS: farm.yourdomain.com\n→ Server public IP"]
    end

    subgraph FARM_LAN["Farm LAN — 192.168.1.0/24"]
        CORE_SW["Core PoE Switch\n24-port Gigabit\n(all cameras + server wired)"]
        SERVER_NIC["Application Server\n192.168.1.5\nGigabit NIC"]
        UPS_POWER["UPS (1500VA)\nPowers switch + server"]

        subgraph WIFI_INFRA["WiFi Infrastructure (Ubiquiti UniFi)"]
            CTRL["UniFi Controller\n(runs on server)\n:8443 dashboard"]
            AP_BARN_A["UAP-AC-Pro\nBarn A ceiling\n192.168.1.10\n2.4 GHz + 5 GHz"]
            AP_BARN_B["UAP-AC-Pro\nBarn B ceiling\n192.168.1.11"]
            AP_PARLOUR["UAP-AC-Pro\nParlour\n192.168.1.12"]
            AP_PROCESS["UAP-AC-Pro\nProcessing Plant\n192.168.1.13"]
            AP_OUTDOOR["UAP-AC-M\n(outdoor, weatherproof)\nPasture / yard\n192.168.1.14\nLong-range 300m"]
        end

        subgraph WIRED_DEVICES["Wired Devices (GbE)"]
            RPI_1["RPi #1 (Lactoscan)\n192.168.1.20"]
            RPI_2["RPi #2 (Camera HLS)\n192.168.1.21"]
            CAM_1["IP Camera #1\n192.168.1.30 PoE"]
            CAM_2["IP Camera #2\n192.168.1.31 PoE"]
            CAM_N["IP Camera …N\n192.168.1.3x PoE"]
        end

        subgraph WIFI_DEVICES_24["WiFi 2.4 GHz (ESP32 nodes — IoT SSID)"]
            ESP_1["ESP32 Barn-A-Temp-01\n192.168.1.100 DHCP reserved\nMQTT → 192.168.1.5:1883"]
            ESP_2["ESP32 Barn-A-Weight-01\n192.168.1.101"]
            ESP_3["ESP32 Pasture-Temp-01\n192.168.1.102\n(via outdoor AP)"]
            ESP_N["ESP32 … (all nodes)\n192.168.1.10x"]
        end

        subgraph CELLULAR["4G LTE (fallback for remote nodes)"]
            SIM800["ESP32 + SIM800L\n(isolated pasture)\nPublishes MQTT over\ncellular data to server\npublic IP / DDNS"]
        end
    end

    subgraph PROTOCOLS["Protocol Stack on each link"]
        P1["ESP32 ↔ AP:\n  PHY: 802.11n 2.4 GHz\n  Network: IP/TCP\n  App: MQTT 3.1.1 QoS 1\n  Port: 1883"]
        P2["RPi ↔ Switch:\n  PHY: GbE 1000Base-T\n  Network: IP/TCP\n  App: MQTT + ffmpeg RTSP pull\n  Port: 1883 + 554"]
        P3["Camera ↔ Switch:\n  PHY: PoE 802.3af\n  Network: IP/TCP\n  App: RTSP H.264\n  Port: 554"]
        P4["Browser ↔ Nginx:\n  PHY: any (WiFi/4G)\n  Network: IP/TCP\n  App: HTTPS (TLS 1.3)\n  Port: 443\n  + WebSocket /socket.io"]
    end

    WAN --> CORE_SW
    CORE_SW --> SERVER_NIC
    CORE_SW --> AP_BARN_A & AP_BARN_B & AP_PARLOUR & AP_PROCESS & AP_OUTDOOR
    CORE_SW --> RPI_1 & RPI_2 & CAM_1 & CAM_2 & CAM_N
    AP_BARN_A --> ESP_1 & ESP_2
    AP_OUTDOOR --> ESP_3 & ESP_N
    CTRL -.->|"manages"| AP_BARN_A & AP_BARN_B & AP_PARLOUR & AP_PROCESS & AP_OUTDOOR
    UPS_POWER --> CORE_SW & SERVER_NIC
    SIM800 -.->|"cellular data\n(backup)"| WAN
```

---

## L4 — MQTT Broker Layer

Inside EMQX — topic routing, subscriber management, QoS guarantees.

```mermaid
graph TD
    subgraph PUBLISHERS["Publishers (sensors)"]
        PUB1["ESP32 barn-a-temp-01\nPUBLISH gdf/barn-a-temp-01/temperature\nQoS 1 payload={value:22.4,...}"]
        PUB2["ESP32 barn-a-temp-01\nPUBLISH gdf/barn-a-temp-01/humidity\nQoS 1 payload={value:67.2,...}"]
        PUB3["RPi lactoscan-01\nPUBLISH gdf/lactoscan-01/fat\nQoS 1 payload={value:3.85,...}"]
        PUBN["... 91 sensors\npublishing to their topics"]
    end

    subgraph EMQX["EMQX 5.x Broker (192.168.1.5:1883)"]
        direction TB
        LISTENER["MQTT Listeners\n:1883 TCP (LAN)\n:8883 TLS (external)\n:8083 WebSocket (optional)"]

        AUTH_MOD["Auth Module\nBuilt-in username/password DB\nor JWT plugin\nRejects unauthenticated clients"]

        TOPIC_ROUTER["Topic Router\ntrie-based O(1) match\ngdf/barn-a-temp-01/temperature\n  → matched by 'gdf/#'\n  → matched by 'gdf/barn-a-temp-01/+'\n  → delivered to all matching subscribers"]

        QOS_ENGINE["QoS Engine\nQoS 0: fire-and-forget\nQoS 1: store → deliver → await PUBACK\n       retry on timeout\nQoS 2: (not used)"]

        RETAIN["Retained Messages\nlast value kept per topic\nnew subscriber gets last reading immediately\nupon SUBSCRIBE"]

        SESSION_STORE["Session Store\npersistent sessions (cleanSession=false)\nmissed messages queued\nwhile client offline"]

        RULES_ENGINE["EMQX Rules Engine (optional)\nSQL-like rules on message arrival\ne.g. forward to HTTP webhook\nor write to Kafka/InfluxDB directly"]

        LISTENER --> AUTH_MOD --> TOPIC_ROUTER --> QOS_ENGINE
        TOPIC_ROUTER --> RETAIN
        TOPIC_ROUTER --> SESSION_STORE
        TOPIC_ROUTER --> RULES_ENGINE
    end

    subgraph SUBSCRIBERS["Subscribers"]
        SUB_FASTAPI["FastAPI MQTT Bridge\naiomqtt client\nSUBSCRIBE gdf/#   QoS 1\n(receives every sensor reading)"]
        SUB_RULES["Rules Engine forward\n(optional: data lake / backup)"]
    end

    PUB1 & PUB2 & PUB3 & PUBN -->|"TCP :1883\nMQTT CONNECT + PUBLISH"| LISTENER
    QOS_ENGINE -->|"PUBACK to publisher\nwhen delivered"| PUB1
    TOPIC_ROUTER -->|"fan-out to all\nmatching subscribers"| SUB_FASTAPI & SUB_RULES

    subgraph TOPIC_EXAMPLES["Topic Wildcard Examples"]
        TE1["Subscribe 'gdf/#'\n→ ALL sensor readings\n(FastAPI bridge uses this)"]
        TE2["Subscribe 'gdf/barn-a-temp-01/+'\n→ all channels of one sensor"]
        TE3["Subscribe 'gdf/+/temperature'\n→ temperature from every sensor"]
    end
```

---

## L5 — Application Server Layer

Every service running on the server and how they talk to each other.

```mermaid
graph TD
    subgraph FASTAPI_APP["FastAPI Application (Python 3.12, uvicorn :8001)"]
        subgraph ROUTERS["REST API Routers"]
            R_AUTH["/api/auth\nPOST /login → JWT\nGET /me → profile"]
            R_SENSORS["/api/sensors\nCRUD + plugin list\nRBAC: location filter"]
            R_TELEMETRY["/api/telemetry\nGET ?sensor_id&start&end&channel\nGET /latest → last value per channel"]
            R_ALERTS["/api/alerts\nCRUD alert_rules\nGET active_alerts\nPOST /resolve"]
            R_TASKS["/api/tasks\nCRUD + assignees\nPOST /{id}/submit, /approve, /reject\nPOST /{id}/attachments"]
            R_PLANS["/api/plans\nCRUD plans + plan_actions"]
            R_PUSH["/api/push\nPOST /subscribe (save VAPID endpoint)\nPOST /test-push"]
            R_USERS["/api/users\nCRUD + permissions\nGET /me/notifications"]
            R_NOTIFS["/api/notifications\nGET list · POST /read-all"]
        end

        subgraph MIDDLEWARE["Middleware Stack"]
            MW_CORS["CORSMiddleware\norigin: frontend domain"]
            MW_AUTH["JWTBearer dependency\ndecodes token → User object\nchecks Redis blocklist"]
            MW_RBAC["require_permission()\nchecks user_location_permissions\nuser_sensor_permissions"]
        end

        subgraph BG_TASKS["Background Services (asyncio)"]
            MQTT_BGT["MQTT Bridge Task\naiomqtt.Client subscribe gdf/#\non_message → ingest_reading()"]
            ALERT_BGT["Alert Engine\nalert_engine.py\neval_rules(sensor_id, channel, value)\n< 5ms per reading"]
            PLAN_BGT["Plan Action Service\nplan_action_service.py\nfires actions on threshold breach"]
            SCHED_BGT["APScheduler\nevery 30 min:\n  task_reminder_service.check_deadlines()"]
        end

        subgraph SERVICES["Shared Services"]
            PUSH_SVC_S["push_service.py\npywebpush\nfilter by RBAC + push_enabled"]
            TWILIO_S["twilio_service.py\nTwilio REST Client\nSMS + TwiML voice"]
            EMAIL_S["email_service.py\naiosmtplib\nHTML email template"]
            PLUGIN_REG_S["plugin_registry.py\nauto-discover plugins/types/\ntemperature_humidity\nweight_hx711\nmilk_analyzer_lactoscan\nip_camera_rtsp"]
        end
    end

    subgraph TIMESCALE["TimescaleDB :5432"]
        HT["sensor_readings\n(hypertable, 7-day chunks)\n─────────────────\nINSERT: ~1ms async\nSELECT with time filter: 2–20ms\nChunk pruning: O(chunks) not O(rows)"]
        AGG["readings_hourly (continuous agg)\nreadings_daily (continuous agg)\npre-computed, auto-updated"]
        OTHER_TBL["sensors · users · alert_rules\nalert_rule_actions · active_alerts\nplans · plan_actions · tasks\ntask_attachments · task_assignees\nnotifications · push_subscriptions\nuser_location_permissions\nuser_sensor_permissions"]
        HT --> AGG
    end

    subgraph REDIS_S["Redis :6379"]
        CHAN_READ["Pub/Sub channel: sensor:reading\npayload: {sensor_id, channel, value, unit, ts}"]
        CHAN_ALERT["Pub/Sub channel: alert:triggered\npayload: {alert_id, rule_id, severity, message}"]
        BLOCKLIST["SET jwt_blocklist:{jti}\n(set on logout, TTL = token remaining TTL)"]
    end

    MQTT_BGT -->|"INSERT"| HT
    MQTT_BGT -->|"PUBLISH"| CHAN_READ
    MQTT_BGT --> ALERT_BGT
    ALERT_BGT -->|"INSERT"| OTHER_TBL
    ALERT_BGT -->|"PUBLISH"| CHAN_ALERT
    ALERT_BGT --> PLAN_BGT
    PLAN_BGT --> PUSH_SVC_S & TWILIO_S & EMAIL_S
    PLAN_BGT -->|"INSERT"| OTHER_TBL
    SCHED_BGT -->|"SELECT tasks"| OTHER_TBL
    SCHED_BGT --> PUSH_SVC_S
    ROUTERS <-->|"asyncpg"| HT & OTHER_TBL
    ROUTERS <-->|"aioredis"| BLOCKLIST
    ROUTERS --- MIDDLEWARE
```

---

## L6 — Host & Infrastructure Layer

Docker containers, volumes, Nginx routing, and cloud/VPS placement.

```mermaid
graph TD
    subgraph CLOUD["Cloud / VPS (e.g. DigitalOcean, AWS EC2, Hetzner)"]
        subgraph HOST_OS["Host OS (Ubuntu 22.04 LTS)"]
            subgraph DOCKER["Docker Engine + Compose"]
                subgraph NET_BRIDGE["Docker bridge network: gdf-net"]
                    C_NGINX["nginx container\n:80 → redirect HTTPS\n:443 TLS (Let's Encrypt)\n─────────────────\nServes: /usr/share/nginx/html (dist/)\nProxies:\n  /api/ → backend:8001\n  /socket.io/ → realtime:3001\n  /uploads/ → backend:8001"]

                    C_BACKEND["backend container\n(Python 3.12 + uvicorn)\nExposes: 8001 (internal only)\nVolume: uploads/ ↔ /app/uploads\nEnv: DATABASE_URL, MQTT_HOST,\n     VAPID_*, SECRET_KEY, TWILIO_*"]

                    C_REALTIME["realtime container\n(Node.js 20 + Fastify)\nExposes: 3001 (internal only)\nEnv: REDIS_URL, PORT=3001"]

                    C_EMQX["emqx container\n:1883 ← ESP32 publish (LAN only)\n:8883 ← TLS (if external needed)\n:18083 ← dashboard (firewall off externally)\nVolume: emqx_data/"]

                    C_TSDB["timescaledb container\n(PostgreSQL 16 + TimescaleDB ext)\n:5432 (internal only)\nVolume: tsdb_data/ → 100GB+ SSD"]

                    C_REDIS["redis container\n:6379 (internal only)\nVolume: redis_data/\nno password (LAN only)"]
                end

                VOL_TSDB["Volume: tsdb_data\n(PostgreSQL WAL + data files)"]
                VOL_REDIS["Volume: redis_data\n(AOF persistence)"]
                VOL_EMQX["Volume: emqx_data\n(sessions + retained messages)"]
                VOL_UPLOADS["Volume: uploads\n(task attachments)"]
                VOL_STATIC["Bind mount: frontend/dist\n→ nginx html root"]
            end

            FW["UFW Firewall\nAllow: 22 (SSH), 80, 443, 1883 (LAN subnet only)\nDeny: 5432, 6379, 3001, 8001 (internal only)"]
            CERTBOT["Certbot (cron)\nauto-renews Let's Encrypt TLS cert\n→ /etc/letsencrypt/live/farm.domain/"]
        end
    end

    subgraph FARM_LAN2["Farm LAN (192.168.1.0/24)"]
        ESP32_FAR["ESP32 nodes\n→ EMQX :1883 (LAN)"]
        RPI_FAR["Raspberry Pi\n→ EMQX :1883 (LAN)"]
        BROWSER_FAR["Farm office browser\n→ Nginx :443 (LAN or WAN)"]
    end

    subgraph USERS_REMOTE["Remote Users"]
        MOBILE_USER["Farm owner mobile\n→ Nginx :443 (WAN / 4G)"]
        ADMIN_PC["Admin laptop\n→ Nginx :443 (WAN)"]
    end

    subgraph EXTERNAL_SVCS["External Services"]
        TWILIO_EXT["Twilio API\napi.twilio.com\nSMS + Voice"]
        PUSH_ENDPOINT["Browser Push Endpoints\nfcm.googleapis.com (Chrome/Android)\npush.apple.com (Safari/iOS)\nmozilla push service (Firefox)"]
        SMTP_EXT["SMTP relay\n(Gmail / SendGrid / Mailgun)"]
    end

    ESP32_FAR & RPI_FAR --> C_EMQX
    BROWSER_FAR & MOBILE_USER & ADMIN_PC --> C_NGINX
    C_NGINX --> C_BACKEND & C_REALTIME
    C_BACKEND --> C_TSDB & C_REDIS & C_EMQX
    C_REALTIME --> C_REDIS
    C_BACKEND --> TWILIO_EXT & SMTP_EXT
    C_BACKEND --> PUSH_ENDPOINT
    FW -.->|"protects"| HOST_OS
    CERTBOT -.->|"auto-renew"| C_NGINX

    C_TSDB --- VOL_TSDB
    C_REDIS --- VOL_REDIS
    C_EMQX --- VOL_EMQX
    C_BACKEND --- VOL_UPLOADS
    C_NGINX --- VOL_STATIC
```

---

## L7 — Client Delivery Layer

Everything that runs inside the browser (or as an installed PWA).

```mermaid
graph TD
    subgraph BROWSER["Browser / Installed PWA"]
        subgraph SW["Service Worker (sw.js — Workbox)"]
            SW_INSTALL2["install event\n→ precache: index.html, main.js,\n  main.css, icons/, fonts/"]
            SW_FETCH2["fetch event handler\nNetworkFirst  → /api/**\n  (fresh data, fallback to cache)\nCacheFirst    → /assets/** (hashed)\nStaleWhileRevalidate → index.html"]
            SW_PUSH2["push event\n→ parse notification payload\n→ self.registration.showNotification(\n    title, body, icon,\n    data: {url: '/notifications'}\n  )"]
            SW_CLICK["notificationclick\n→ clients.openWindow(data.url)\n  (opens app to notifications page)"]
            SW_INSTALL2 --- SW_FETCH2
            SW_PUSH2 --> SW_CLICK
        end

        subgraph REACT["React 18 App (SPA)"]
            ROUTER2["React Router v6\n<BrowserRouter>\nRoutes: / /monitoring /sensors\n/tasks/:id /planning /alerts\n/notifications /settings /users /locations"]

            AUTH_CTX["AuthContext\n─────────────────\nstores: {user, token}\nlogin() → POST /api/auth/login\n         save token → localStorage gdf_token\nlogout() → clear + blocklist\napiFetch() → adds Authorization: Bearer token\nExpires: 24h JWT, auto-logout on 401"]

            QUERY_CLIENT["TanStack Query v5\n─────────────────\nQueryClient(staleTime: 60s)\nWindow focus refetch: true\nBackground refetch on reconnect: true\nRefetchInterval per query:\n  sensors: 30s\n  telemetry: 60s\n  tasks: on-demand\n  notifications: 30s"]

            ZUSTAND_STORE["Zustand Store (sensorStore)\n─────────────────\nstate: { readings: Map<sensorId, Reading[]> }\nupdateReading(data) called by Socket.io\ncomponents subscribe with selectors\n→ only re-renders component that\n  uses that specific sensor's data"]

            SOCKET_CLIENT["Socket.io Client\n─────────────────\nio(window.location.origin, {path:'/socket.io'})\nauto-reconnect (exp. backoff, max 30s)\n\nOn connect:\n  emit('subscribe', {sensor_id}) for\n  every sensor on current page\n\nOn 'reading' event:\n  zustand.updateReading(payload)\n\nOn 'alert' event:\n  toast.error(message)\n  invalidate query ['active-alerts']"]

            PUSH_CLIENT["Push Registration\n─────────────────\nSettings page → 'Enable notifications'\n  → Notification.requestPermission()\n  → serviceWorker.pushManager.subscribe({\n      userVisibleOnly: true,\n      applicationServerKey: VAPID_PUBLIC_KEY\n    })\n  → POST /api/push/subscribe {endpoint, keys}\n\nStored per browser in push_subscriptions table"]

            subgraph PAGES["Pages"]
                PG_DASH["/ Dashboard\nactive alerts summary\nrecent readings\ntask counts"]
                PG_MON["/ monitoring\nSensorMonitorCard per sensor\nlive values from Zustand\nDeviceStatusPanel"]
                PG_SENSORS["/ sensors\nSensor list, add/edit/delete\nSensorDetail with chart"]
                PG_TASKS["/ tasks\nTask list with filters\nDeadlineBadge component"]
                PG_PLAN["/ planning\nPlan CRUD\nplan_actions config"]
                PG_NOTIFS["/ notifications\nAll notifications list\nread/unread state"]
                PG_SETTINGS["/ settings\nPush notification toggle\nUser profile (phone, duty)"]
            end
        end

        subgraph PWA2["PWA Manifest"]
            MANIFEST2["manifest.webmanifest\nname: GDF-AutoMon\nshort_name: GDF\ndisplay: standalone\nstart_url: /\ntheme_color: #059669\nbackground_color: #0a0a0a\nicons: [192px, 512px maskable]"]
        end
    end

    AUTH_CTX --> QUERY_CLIENT
    AUTH_CTX --> SOCKET_CLIENT
    SOCKET_CLIENT --> ZUSTAND_STORE
    ZUSTAND_STORE --> PG_MON
    QUERY_CLIENT --> PG_DASH & PG_SENSORS & PG_TASKS & PG_PLAN & PG_NOTIFS
    SW_PUSH2 --> PG_NOTIFS
    PUSH_CLIENT --> SW_INSTALL2
    MANIFEST2 -.->|"browser install prompt"| ROUTER2
```

---

## F1 — Sensor Reading → Live Dashboard

The happy path: a temperature value travels from sensor to browser pixel.

```mermaid
sequenceDiagram
    actor ESP32 as ESP32 Sensor Node<br/>(barn-a-temp-01)
    participant EMQX as EMQX Broker<br/>:1883
    participant BRIDGE as FastAPI<br/>MQTT Bridge
    participant TSDB as TimescaleDB<br/>sensor_readings
    participant REDIS as Redis<br/>sensor:reading
    participant SOCKER as Socket.io<br/>Gateway :3001
    participant NGINX as Nginx<br/>:443
    participant WS as WebSocket<br/>(browser)
    participant ZUSTAND as Zustand Store<br/>sensorStore
    participant REACT as React Component<br/>SensorMonitorCard

    Note over ESP32: Wakes from deep-sleep<br/>Reads SHT31 → 22.4°C

    ESP32->>EMQX: PUBLISH QoS 1<br/>topic: gdf/barn-a-temp-01/temperature<br/>payload: {"value":22.4,"unit":"°C","ts":"2026-04-30T08:15:00Z"}
    EMQX-->>ESP32: PUBACK (QoS 1 confirmed)
    EMQX->>BRIDGE: deliver message<br/>(subscribed to gdf/#)

    BRIDGE->>BRIDGE: parse topic<br/>sensor_id = "barn-a-temp-01"<br/>channel = "temperature"

    par store + fan-out (parallel)
        BRIDGE->>TSDB: INSERT sensor_readings<br/>(sensor_id, channel, value=22.4,<br/> unit='°C', recorded_at=ts)
        Note over TSDB: Hypertable auto-routes<br/>to current 7-day chunk<br/>~1ms INSERT
    and
        BRIDGE->>REDIS: PUBLISH sensor:reading<br/>{"sensor_id":"barn-a-temp-01",<br/>"channel":"temperature",<br/>"value":22.4,"unit":"°C","ts":"..."}
    end

    REDIS->>SOCKER: delivers to ioredis subscriber
    SOCKER->>SOCKER: io.to("sensor:barn-a-temp-01")<br/>.emit("reading", payload)
    SOCKER->>NGINX: WebSocket frame
    NGINX->>WS: proxied WebSocket frame<br/>(wss:// upgrade, path /socket.io)

    WS->>ZUSTAND: socket.on('reading', data =><br/>  store.updateReading(data))
    ZUSTAND->>REACT: Zustand selector fires<br/>component re-renders

    Note over REACT: Card shows:<br/>🌡 22.4°C<br/>Updated 08:15:00<br/>● online

    Note over ESP32,REACT: Total wall-clock time: ~80–250 ms LAN<br/>~300–600 ms over 4G WAN
```

---

## F2 — Alert Threshold Breach → Push Notification

Temperature crosses the configured limit; the right people are notified.

```mermaid
sequenceDiagram
    actor SENSOR as ESP32 Sensor
    participant EMQX as EMQX Broker
    participant BRIDGE as FastAPI<br/>MQTT Bridge
    participant ENGINE as Alert Engine<br/>alert_engine.py
    participant TSDB as TimescaleDB
    participant REDIS as Redis<br/>alert:triggered
    participant SOCK2 as Socket.io<br/>Gateway
    participant PUSH_S as push_service.py<br/>(pywebpush)
    participant BROWSER_SW as Browser<br/>Service Worker
    participant USER as Farm Owner<br/>(mobile screen)

    SENSOR->>EMQX: PUBLISH gdf/barn-a-temp-01/temperature<br/>payload: {"value":38.7,"unit":"°C","ts":"..."}
    EMQX->>BRIDGE: deliver
    BRIDGE->>TSDB: INSERT reading (value=38.7)

    BRIDGE->>ENGINE: evaluate_rules("barn-a-temp-01", "temperature", 38.7)
    ENGINE->>TSDB: SELECT alert_rules<br/>WHERE sensor_id='barn-a-temp-01'<br/>AND channel='temperature' AND enabled=true

    Note over TSDB: Returns rule:<br/>id=rule-42, condition=gt<br/>threshold=35, severity=critical

    ENGINE->>ENGINE: 38.7 > 35 → TRIGGERED

    ENGINE->>TSDB: INSERT active_alerts<br/>(rule_id=rule-42,<br/> triggered_value=38.7,<br/> message="Temperature 38.7°C exceeds 35°C",<br/> triggered_at=now())

    ENGINE->>TSDB: SELECT alert_rule_actions<br/>WHERE rule_id=rule-42

    Note over TSDB: Returns actions:<br/>1. notification (push)<br/>2. sms

    ENGINE->>TSDB: SELECT users WHERE<br/>has RBAC access to barn-a-temp-01's location<br/>AND push_enabled=true for 'critical'

    Note over TSDB: Returns: [user-farm-owner, user-admin]

    ENGINE->>TSDB: SELECT push_subscriptions<br/>WHERE user_id IN [...]

    ENGINE->>PUSH_S: send_push(subscriptions, title, body, data)

    loop for each push subscription endpoint
        PUSH_S->>PUSH_S: sign payload with VAPID private key
        PUSH_S->>BROWSER_SW: POST to browser push endpoint<br/>(e.g. fcm.googleapis.com/fcm/send/...)<br/>headers: VAPID Authorization, TTL=86400
        BROWSER_SW-->>PUSH_S: 201 Created
    end

    BROWSER_SW->>BROWSER_SW: onpush event fires<br/>even if browser tab is closed!
    BROWSER_SW->>USER: showNotification(<br/>  "🚨 Critical Alert",<br/>  "barn-a-temp-01: Temperature 38.7°C > 35°C",<br/>  icon: "/icons/icon-192.png",<br/>  badge: "/icons/badge-72.png",<br/>  data: {url: "/alerts"}<br/>)

    USER->>BROWSER_SW: taps notification
    BROWSER_SW->>USER: opens GDF-AutoMon app<br/>navigates to /alerts page

    par also via Socket.io (if tab is open)
        ENGINE->>REDIS: PUBLISH alert:triggered {alert_id, severity, message}
        REDIS->>SOCK2: delivers
        SOCK2->>USER: socket.emit('alert', payload)<br/>→ toast.error() shown in UI<br/>→ bell icon counter incremented
    end
```

---

## F3 — Alert Breach → Twilio SMS & Voice Call

When push alone isn't enough — critical alerts reach the user's phone directly.

```mermaid
sequenceDiagram
    actor ENGINE2 as Alert Engine
    participant TSDB2 as TimescaleDB
    participant TWILIO_S as twilio_service.py
    participant TWILIO_API as Twilio REST API<br/>api.twilio.com
    participant TWILIO_INFRA as Twilio Infrastructure<br/>(carrier routing)
    actor USER_PHONE as User's Phone<br/>(+92-xxx-xxx-xxxx)

    ENGINE2->>TSDB2: SELECT alert_rule_actions<br/>WHERE rule_id=rule-42
    Note over TSDB2: action_type='sms'<br/>config={to_number: user.phone}<br/><br/>action_type='call'<br/>config={to_number: user.phone}

    ENGINE2->>TSDB2: SELECT user.phone<br/>WHERE user_id = assigned_user

    Note over ENGINE2: user.phone = "+92-311-1234567"

    ENGINE2->>TWILIO_S: send_sms(to="+92-311-1234567",<br/>  body="[GDF ALERT] CRITICAL: barn-a-temp-01\nTemperature 38.7°C exceeds limit 35°C\nTime: 08:15 UTC\nView: https://farm.domain/alerts")

    TWILIO_S->>TWILIO_API: POST /2010-04-01/Accounts/{SID}/Messages<br/>From: +12345670000 (Twilio number)<br/>To: +92-311-1234567<br/>Body: [alert text]<br/>Auth: Basic SID:AuthToken

    TWILIO_API-->>TWILIO_S: {"sid":"SM...","status":"queued"}

    TWILIO_API->>TWILIO_INFRA: route to carrier
    TWILIO_INFRA->>USER_PHONE: SMS delivered (3–15 seconds)

    Note over USER_PHONE: Phone buzzes\n📱 SMS from +1234567000\n"[GDF ALERT] CRITICAL..."

    ENGINE2->>TWILIO_S: make_call(to="+92-311-1234567",<br/>  twiml_message="Emergency alert from GDF AutoMon.\nSensor barn-a-temp-01 temperature is\n38.7 degrees celsius. This exceeds\nthe critical threshold of 35 degrees.\nPlease check the barn immediately.")

    TWILIO_S->>TWILIO_API: POST /2010-04-01/Accounts/{SID}/Calls<br/>From: +12345670000<br/>To: +92-311-1234567<br/>Twiml: <Response><Say voice='alice'>...</Say></Response>

    TWILIO_API->>TWILIO_INFRA: initiate voice call
    TWILIO_INFRA->>USER_PHONE: phone rings (5–20 seconds)

    Note over USER_PHONE: Phone rings\n📞 Call from +1234567000\nUser answers → hears voice message
```

---

## F4 — User Opens Historical Chart

A chart request: from browser click to rendered graph.

```mermaid
sequenceDiagram
    actor USER2 as User
    participant REACT2 as React<br/>SensorDetail page
    participant TQ as TanStack Query
    participant APIFETCH as apiFetch()<br/>client.ts
    participant NGINX2 as Nginx
    participant FASTAPI2 as FastAPI<br/>/api/telemetry
    participant TSDB3 as TimescaleDB

    USER2->>REACT2: Clicks sensor "Barn A Temp"\nSelects "Last 24 hours"

    REACT2->>TQ: useQuery({<br/>  queryKey: ['telemetry','barn-a-temp-01','temperature', 24],<br/>  queryFn: () => apiFetch('/api/telemetry?sensor_id=barn-a-temp-01<br/>    &channel=temperature&start=2026-04-29T08:15:00Z')<br/>  refetchInterval: 60_000<br/>})

    TQ->>TQ: check cache<br/>key not found → FRESH FETCH

    TQ->>APIFETCH: call queryFn
    APIFETCH->>APIFETCH: read localStorage gdf_token\nadd header: Authorization: Bearer eyJhb...

    APIFETCH->>NGINX2: GET /api/telemetry?sensor_id=...&start=...<br/>Authorization: Bearer token<br/>HTTPS :443

    NGINX2->>FASTAPI2: proxy to :8001<br/>GET /api/telemetry?...

    FASTAPI2->>FASTAPI2: decode JWT → user\ncheck user_sensor_permissions for barn-a-temp-01

    FASTAPI2->>TSDB3: SELECT sensor_id, channel, value, unit, recorded_at<br/>FROM sensor_readings<br/>WHERE sensor_id='barn-a-temp-01'<br/>  AND channel='temperature'<br/>  AND recorded_at >= '2026-04-29T08:15:00Z'<br/>ORDER BY recorded_at ASC<br/>LIMIT 10000

    Note over TSDB3: Hypertable query:<br/>only scans 4 × 7-day chunks max<br/>→ chunk pruning<br/>Returns ~8640 rows for 24h at 10s intervals<br/>Query time: 5–20ms

    TSDB3-->>FASTAPI2: [{sensor_id, channel, value, unit, recorded_at}, ...]

    FASTAPI2-->>NGINX2: JSON array (gzip compressed ~50KB)
    NGINX2-->>APIFETCH: 200 OK

    APIFETCH-->>TQ: parsed JSON array
    TQ->>TQ: store in cache with 60s staleTime<br/>mark query as success

    TQ-->>REACT2: data = SensorReading[]

    REACT2->>REACT2: Recharts LineChart renders<br/>x-axis: timestamps<br/>y-axis: °C values<br/>~8640 data points downsampled to visible pixels

    REACT2-->>USER2: Chart rendered with<br/>temperature trend over 24 hours

    Note over TQ: After 60 seconds:<br/>TQ silently refetches in background<br/>Chart updates without user interaction
```

---

## F5 — Task Deadline Reminder

A task is approaching its deadline and assignees are reminded automatically.

```mermaid
sequenceDiagram
    participant SCHED as APScheduler<br/>(every 30 min)
    participant TASK_SVC as task_reminder_service.py
    participant TSDB4 as TimescaleDB
    participant PUSH_S2 as push_service.py
    participant NOTIF_INS as Notification INSERT
    participant BROWSER_SW2 as Browser Service Worker
    actor ASSIGNEE as Assigned User

    Note over SCHED: every 30 minutes (e.g. 09:00, 09:30...)

    SCHED->>TASK_SVC: check_deadlines()

    TASK_SVC->>TSDB4: SELECT t.id, t.title, t.deadline,<br/>  ta.user_id<br/>FROM tasks t<br/>JOIN task_assignees ta ON t.id=ta.task_id<br/>WHERE t.deadline BETWEEN now() AND now() + INTERVAL '24 hours'<br/>  AND t.status IN ('open','rejected')<br/>  AND t.id NOT IN (<br/>    SELECT task_id FROM sent_reminders<br/>    WHERE sent_at > now() - INTERVAL '12 hours'<br/>  )

    Note over TSDB4: Returns tasks within 24h deadline<br/>not yet reminded in last 12h

    loop for each task × assignee
        TASK_SVC->>NOTIF_INS: INSERT INTO notifications<br/>(user_id, title='Task Due Soon',<br/> body='Milk Quality Check due in 3h',<br/> created_at=now())

        TASK_SVC->>TSDB4: SELECT push_subscriptions<br/>WHERE user_id = assignee.id<br/>  AND push_enabled = true

        TASK_SVC->>PUSH_S2: send_push(<br/>  subscriptions,<br/>  title="⏰ Task Due Soon",<br/>  body="Milk Quality Check — due in 3 hours",<br/>  data={url:"/tasks/{task_id}"}<br/>)

        PUSH_S2->>BROWSER_SW2: VAPID push POST to endpoint

        BROWSER_SW2->>ASSIGNEE: showNotification(<br/>  "⏰ Task Due Soon",<br/>  "Milk Quality Check — due in 3 hours"<br/>)
    end

    TASK_SVC->>TSDB4: INSERT INTO sent_reminders<br/>(task_id, sent_at=now())<br/>(prevents duplicate reminders in 12h window)

    ASSIGNEE->>BROWSER_SW2: taps notification
    BROWSER_SW2->>ASSIGNEE: opens /tasks/{task_id}<br/>user can mark task as submitted
```

---

## F6 — PWA Install & First Offline Load

How a user installs the app and what happens when they're offline.

```mermaid
sequenceDiagram
    actor USER3 as Farm Owner
    participant CHROME as Chrome Browser
    participant SW3 as Service Worker<br/>(sw.js)
    participant CACHE as Workbox Cache<br/>(CacheStorage)
    participant NGINX3 as Nginx / CDN
    participant API as FastAPI API

    Note over USER3,NGINX3: FIRST VISIT — Online

    USER3->>CHROME: opens https://farm.domain
    CHROME->>NGINX3: GET / → index.html
    NGINX3-->>CHROME: index.html + <script> loads main.js

    CHROME->>NGINX3: GET /sw.js (Service Worker)
    NGINX3-->>CHROME: sw.js (Workbox generated)

    CHROME->>SW3: register service worker
    SW3->>SW3: install event fires
    SW3->>NGINX3: precache: index.html, main.js,<br/>main.css, icons/192.png, icons/512.png,<br/>manifest.webmanifest, fonts/...
    NGINX3-->>SW3: all assets (200 OK)
    SW3->>CACHE: store in 'workbox-precache' cache
    SW3->>CHROME: activate (skipWaiting)

    Note over CHROME: Address bar shows install icon

    USER3->>CHROME: clicks "Install GDF-AutoMon"<br/>OR Share → Add to Home Screen (iOS)
    CHROME->>CHROME: installs to home screen<br/>creates standalone window
    CHROME-->>USER3: app icon on home screen ✓

    Note over USER3,API: NORMAL USE — Online

    USER3->>CHROME: opens app → /monitoring
    CHROME->>SW3: fetch /api/sensors (NetworkFirst)
    SW3->>API: GET /api/sensors
    API-->>SW3: JSON sensor list
    SW3->>CACHE: update 'api-cache' entry
    SW3-->>CHROME: JSON data → renders sensor cards

    Note over USER3,API: GOING OFFLINE

    USER3->>CHROME: opens app → /monitoring<br/>(no internet connection)
    CHROME->>SW3: fetch /api/sensors (NetworkFirst)
    SW3->>API: GET /api/sensors [NETWORK ERROR]
    SW3->>CACHE: fallback → return cached /api/sensors
    SW3-->>CHROME: stale JSON from last online visit
    CHROME-->>USER3: shows sensor cards (stale data)<br/>"⚠ Offline — showing cached data"

    CHROME->>SW3: fetch /monitoring (SWR)
    SW3->>CACHE: return cached index.html immediately
    SW3->>API: background revalidate [FAILS — offline]
    SW3-->>CHROME: index.html served from cache instantly

    Note over USER3,API: RECONNECT

    USER3->>CHROME: network restored
    CHROME->>SW3: 'online' event
    SW3->>API: refetch all NetworkFirst routes
    API-->>SW3: fresh data
    SW3->>CACHE: update all cache entries
    SW3-->>CHROME: live data resumes
    CHROME-->>USER3: Socket.io reconnects<br/>live readings resume
```

---

## F7 — New Sensor Registered (Admin Flow)

An admin adds a new ESP32 sensor through the UI and the system activates it.

```mermaid
sequenceDiagram
    actor ADMIN as Admin User
    participant UI as React<br/>SensorManagement page
    participant FASTAPI3 as FastAPI<br/>/api/sensors
    participant TSDB5 as TimescaleDB
    participant PLUGIN as Plugin Registry<br/>plugin_registry.py
    participant EMQX2 as EMQX Broker
    participant ESP32_NEW as New ESP32 Node<br/>(just powered on)

    Note over ADMIN,PLUGIN: Admin adds sensor via UI

    ADMIN->>UI: GET /sensors → clicks "Add Sensor"
    UI->>FASTAPI3: GET /api/sensors/types
    FASTAPI3->>PLUGIN: registry.get_all_types()
    PLUGIN-->>FASTAPI3: [temperature_humidity, weight_hx711,<br/>milk_analyzer_lactoscan, ip_camera_rtsp]
    FASTAPI3-->>UI: sensor type list + config schemas
    UI-->>ADMIN: type dropdown + dynamic config form

    ADMIN->>UI: fills form:<br/>name = "Barn B Temp North"<br/>type = temperature_humidity<br/>location = Barn B<br/>config = {mqtt_topic_prefix: "gdf/barn-b-temp-north"}

    UI->>FASTAPI3: POST /api/sensors<br/>body: {name, sensor_type, location_id, config}

    FASTAPI3->>FASTAPI3: validate role = admin or super_admin<br/>validate user has permission for location_id

    FASTAPI3->>PLUGIN: get_adapter("temperature_humidity")\nvalidate config schema against ConfigSchema

    FASTAPI3->>TSDB5: INSERT INTO sensors<br/>(id=uuid, name, sensor_type,<br/> protocol, location_id, config JSONB,<br/> is_active=true, created_at=now())

    TSDB5-->>FASTAPI3: sensor row with new id

    FASTAPI3-->>UI: {id: "uuid-new-sensor", name, ...}
    UI-->>ADMIN: sensor appears in list ✓

    Note over ESP32_NEW,EMQX2: Admin flashes firmware to new ESP32\nwith SENSOR_ID="barn-b-temp-north"

    ESP32_NEW->>EMQX2: CONNECT (client_id=barn-b-temp-north)
    EMQX2-->>ESP32_NEW: CONNACK

    ESP32_NEW->>EMQX2: PUBLISH gdf/barn-b-temp-north/temperature<br/>payload: {"value":19.1,"unit":"°C","ts":"..."}
    EMQX2->>FASTAPI3: deliver (subscribed to gdf/#)
    FASTAPI3->>TSDB5: INSERT sensor_readings<br/>(sensor_id="uuid-new-sensor", ...)

    Note over FASTAPI3: Bridge matches MQTT sensor_id<br/>to DB sensor by mqtt_topic_prefix config

    FASTAPI3->>UI: Socket.io broadcast 'reading'<br/>for new sensor
    UI-->>ADMIN: new sensor card appears on<br/>Monitoring page with live value ✓
```

---

## F8 — Full End-to-End: Sensor Spike to Resolved Alert

Complete lifecycle of a critical event from first anomalous reading to admin marks resolved.

```mermaid
flowchart TD
    A["ESP32 reads SHT31\nTemperature = 39.1°C\n(normal max = 30°C)"]
    B["PUBLISH QoS 1\ngdf/barn-a-temp-01/temperature\n{'value':39.1,'unit':'°C','ts':'...'}\nEMQX → FastAPI Bridge"]
    C["INSERT sensor_readings\n(recorded_at, value=39.1)"]
    D["evaluate_rules() called\nrule: gt threshold=35 severity=critical\n→ TRIGGERED"]
    E["INSERT active_alerts\n(rule_id, triggered_value=39.1,\nmessage='Temperature 39.1°C > 35°C',\ntriggered_at=now())"]
    F["Load alert_rule_actions\naction 1: notification\naction 2: sms\naction 3: call"]
    G["Fetch permitted users\nwith push_subscriptions"]

    H["pywebpush → Browser SW\n'🚨 CRITICAL: Barn A Temp 39.1°C'"]
    I["Twilio SMS\n'+92-311-xxx: [GDF ALERT] Critical...'"]
    J["Twilio Voice Call\n'Emergency: temperature 39.1 degrees...'"]
    K["INSERT notifications\n(in-app bell for all permitted users)"]
    L["PUBLISH alert:triggered → Redis\n→ Socket.io → toast in open tabs"]

    M{{"User Response"}}
    N["Farm owner goes to barn\nchecks ventilation system\nfixes the issue"]
    O["Temperature drops to 26°C\nnext reading: value=26.0"]
    P["evaluate_rules() → 26.0 < 35\nrule NOT triggered"]
    Q["auto-resolve: UPDATE active_alerts\nSET resolved_at=now()\nWHERE triggered_at = earliest unresolved"]
    R["OR: Admin opens /alerts page\nclicks 'Mark Resolved'\nPOST /api/alerts/{alert_id}/resolve"]
    S["UPDATE active_alerts SET resolved_at=now()"]
    T["Socket.io broadcast 'alert_resolved'\n→ alert disappears from dashboard\n→ notification marked read"]
    U["TimescaleDB retains full history:\n  active_alerts (resolved)\n  sensor_readings (all values)\n  → auditable for regulatory compliance"]

    A --> B --> C --> D --> E --> F --> G
    G --> H & I & J & K & L
    H & I & J --> M
    M -- "Physical fix" --> N --> O --> P --> Q --> T
    M -- "Manual resolve" --> R --> S --> T
    Q & S --> U
    T --> U

    style D fill:#7f1d1d,color:#fca5a5
    style E fill:#7f1d1d,color:#fca5a5
    style H fill:#065f46,color:#6ee7b7
    style I fill:#1e3a5f,color:#93c5fd
    style J fill:#3b0764,color:#d8b4fe
    style U fill:#1c1917,color:#a8a29e
```

---

## Quick Reference: Layer Stack

```
┌─────────────────────────────────────────────────────────────────┐
│  L7  Client Browser / PWA                                       │
│       React 18 · Zustand · TanStack Query · Socket.io-client    │
│       Service Worker (Workbox) · PWA Manifest                   │
├─────────────────────────────────────────────────────────────────┤
│  L6  Host Infrastructure                                        │
│       Nginx :443  ·  Docker Compose (7 containers)              │
│       VPS / cloud server  ·  Let's Encrypt TLS                  │
├─────────────────────────────────────────────────────────────────┤
│  L5  Application Server                                         │
│       FastAPI :8001  ·  TimescaleDB :5432  ·  Redis :6379       │
│       Socket.io Gateway :3001                                   │
├─────────────────────────────────────────────────────────────────┤
│  L4  MQTT Broker                                                │
│       EMQX 5.x :1883 / :8883                                    │
│       topic: gdf/{sensor_id}/{channel}  ·  QoS 1               │
├─────────────────────────────────────────────────────────────────┤
│  L3  Wireless Network                                           │
│       Ubiquiti UniFi APs  ·  PoE switch  ·  LAN 192.168.1.0/24 │
│       2.4 GHz (ESP32)  ·  Gigabit Ethernet (RPi + cameras)     │
├─────────────────────────────────────────────────────────────────┤
│  L2  Edge Firmware                                              │
│       ESP32 C++ (Arduino SDK)  ·  RPi Python bridges            │
│       Deep-sleep  ·  pyserial  ·  ffmpeg  ·  paho-mqtt          │
├─────────────────────────────────────────────────────────────────┤
│  L1  Physical Sensors                                           │
│       SHT31 (I2C)  ·  HX711 (pseudo-SPI)  ·  Lactoscan (RS-232)│
│       IP Cameras (RTSP)  ·  Load cells  ·  ADC probes           │
└─────────────────────────────────────────────────────────────────┘
```

*Diagrams version: April 2026 · GDF-AutoMon v1.x*
