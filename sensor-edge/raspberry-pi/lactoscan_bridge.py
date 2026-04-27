#!/usr/bin/env python3
"""
GDF-AutoMon: Lactoscan Milk Analyzer → MQTT Bridge
Reads RS-232 serial output from a Lactoscan MA device and publishes
individual channel readings to the EMQX MQTT broker.

Tested with: Lactoscan MA, Lactoscan S, Milkotester Master Pro
Serial protocol: 9600 8N1, output format varies by model — see PARSE_MODE below.

Requirements:
  pip install pyserial paho-mqtt

Usage:
  python lactoscan_bridge.py --sensor-id barn-lactoscan-01 --port /dev/ttyUSB0
"""
import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone

import serial
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
MQTT_HOST = "localhost"       # Change to your server IP
MQTT_PORT = 1883
MQTT_USER = "gdf_backend"
MQTT_PASS = "backend_secret"
MQTT_TOPIC_PREFIX = "gdf"

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600

# Lactoscan typically outputs a tab-delimited line:
# FAT  PROTEIN  LACTOSE  TOTAL_SOLIDS  SNF  WATER  ADDED_WATER  DENSITY  SCC  TEMP
COLUMN_MAP = {
    0: ("fat",          "%"),
    1: ("protein",      "%"),
    2: ("lactose",      "%"),
    3: ("total_solids", "%"),
    4: ("snf",          "%"),       # Solids Non-Fat
    6: ("added_water",  "%"),
    7: ("density",      "g/cm³"),
    8: ("somatic_cells","cells/mL"),
    9: ("milk_temp",    "°C"),
}
# ─────────────────────────────────────────────────────────────────────────────


def parse_lactoscan_line(line: str) -> dict[str, float] | None:
    """Parse tab-delimited Lactoscan output line into channel readings."""
    parts = re.split(r"[\t,;]+", line.strip())
    if len(parts) < 5:
        return None

    readings = {}
    for idx, (channel, _) in COLUMN_MAP.items():
        if idx < len(parts):
            try:
                val = float(parts[idx].replace(",", "."))
                readings[channel] = val
            except ValueError:
                pass

    return readings if readings else None


def main(sensor_id: str, port: str):
    # MQTT setup
    mqttc = mqtt.Client(client_id=f"gdf-lactoscan-{sensor_id}", clean_session=True)
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
    mqttc.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqttc.loop_start()
    logger.info("MQTT connected to %s:%d", MQTT_HOST, MQTT_PORT)

    # Serial connection
    ser = serial.Serial(port, BAUD_RATE, timeout=5)
    logger.info("Serial opened: %s @ %d baud", port, BAUD_RATE)

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("ascii", errors="ignore").strip()
            logger.debug("RAW: %r", line)

            readings = parse_lactoscan_line(line)
            if not readings:
                continue

            ts = datetime.now(timezone.utc).isoformat()

            for channel, value in readings.items():
                _, unit = next(
                    ((ch, u) for i, (ch, u) in COLUMN_MAP.items() if ch == channel),
                    (channel, "")
                )
                topic = f"{MQTT_TOPIC_PREFIX}/{sensor_id}/{channel}"
                payload = json.dumps({"value": value, "unit": unit, "ts": ts, "sensor_id": sensor_id})
                mqttc.publish(topic, payload, qos=1)

            logger.info("Published %d channels for sensor %s", len(readings), sensor_id)

    except KeyboardInterrupt:
        logger.info("Stopping")
    finally:
        ser.close()
        mqttc.loop_stop()
        mqttc.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lactoscan → MQTT bridge")
    parser.add_argument("--sensor-id", default="lactoscan-01", help="Unique sensor ID")
    parser.add_argument("--port", default=SERIAL_PORT, help="Serial port (e.g. /dev/ttyUSB0)")
    args = parser.parse_args()
    main(args.sensor_id, args.port)
