#!/usr/bin/env python3
"""
GDF-AutoMon: IP Camera (RTSP) → HLS Bridge
Transcodes an RTSP stream to HLS segments using ffmpeg and serves
them via a lightweight HTTP server for browser playback.
Also publishes camera status and motion detection events to MQTT.

Requirements:
  apt install ffmpeg
  pip install paho-mqtt

Usage:
  python camera_hls_bridge.py \
    --sensor-id camera-barn-01 \
    --rtsp-url rtsp://admin:pass@192.168.1.10:554/stream \
    --http-port 8090
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = "gdf_backend"
MQTT_PASS = "backend_secret"
MQTT_TOPIC_PREFIX = "gdf"
HLS_BASE_DIR = Path("/tmp/gdf-hls")


def start_ffmpeg(sensor_id: str, rtsp_url: str) -> subprocess.Popen:
    """Start ffmpeg RTSP → HLS transcoding process."""
    out_dir = HLS_BASE_DIR / sensor_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "64k",
        "-vf", "scale=1280:720",  # 720p max
        "-hls_time", "2",          # 2-second segments
        "-hls_list_size", "5",     # Keep 5 segments (10s window)
        "-hls_flags", "delete_segments+independent_segments",
        "-hls_segment_filename", str(out_dir / "segment_%03d.ts"),
        str(out_dir / "index.m3u8"),
    ]

    logger.info("Starting ffmpeg for %s", sensor_id)
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def serve_hls(http_port: int):
    """Serve HLS files from HLS_BASE_DIR."""
    os.chdir(HLS_BASE_DIR)
    handler = SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None  # Suppress access logs
    server = HTTPServer(("0.0.0.0", http_port), handler)
    logger.info("HLS HTTP server on port %d (dir: %s)", http_port, HLS_BASE_DIR)
    server.serve_forever()


def publish_status(mqttc: mqtt.Client, sensor_id: str, status: str, fps: float = 0.0):
    topic = f"{MQTT_TOPIC_PREFIX}/{sensor_id}/camera_status"
    payload = json.dumps({
        "status": status,
        "fps": fps,
        "ts": datetime.now(timezone.utc).isoformat(),
        "sensor_id": sensor_id,
        "hls_url": f"http://localhost/hls/{sensor_id}/index.m3u8",
    })
    mqttc.publish(topic, payload, qos=1, retain=True)


def main(sensor_id: str, rtsp_url: str, http_port: int):
    # MQTT
    mqttc = mqtt.Client(client_id=f"gdf-camera-{sensor_id}")
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
    mqttc.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqttc.loop_start()

    # HLS HTTP server in background thread
    hls_thread = threading.Thread(target=serve_hls, args=(http_port,), daemon=True)
    hls_thread.start()

    try:
        while True:
            proc = start_ffmpeg(sensor_id, rtsp_url)
            publish_status(mqttc, sensor_id, "online")

            # Monitor ffmpeg; restart on crash
            while True:
                retcode = proc.poll()
                if retcode is not None:
                    logger.warning("ffmpeg exited (code %d), restarting in 5s", retcode)
                    publish_status(mqttc, sensor_id, "offline")
                    time.sleep(5)
                    break
                time.sleep(5)
                publish_status(mqttc, sensor_id, "online")
    except KeyboardInterrupt:
        proc.terminate()
        publish_status(mqttc, sensor_id, "offline")
        mqttc.loop_stop()
        mqttc.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RTSP Camera → HLS bridge")
    parser.add_argument("--sensor-id", required=True)
    parser.add_argument("--rtsp-url", required=True)
    parser.add_argument("--http-port", type=int, default=8090)
    args = parser.parse_args()

    HLS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    main(args.sensor_id, args.rtsp_url, args.http_port)
