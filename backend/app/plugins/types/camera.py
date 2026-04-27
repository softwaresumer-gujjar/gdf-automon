"""
IP Camera sensor type — RTSP stream served as HLS for browser playback.

The Raspberry Pi bridge (camera_hls_bridge.py) runs ffmpeg to transcode
RTSP → HLS segments and serve them on an HTTP port. This adapter
records stream metadata, frame stats, and motion detection events to MQTT.

MQTT payload on gdf/{sensor_id}/camera_status:
  {"status": "online", "fps": 15, "resolution": "1920x1080"}

HLS stream URL: http://{bridge_host}:{bridge_port}/hls/{sensor_id}/index.m3u8
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import aiomqtt

from app.plugins.base import SensorAdapter, SensorReading, Channel
from app.core.config import settings

logger = logging.getLogger(__name__)


class CameraSensor(SensorAdapter):
    sensor_type = "ip_camera_rtsp"
    display_name = "IP Camera (RTSP)"
    protocol = "rtsp"
    icon = "camera"

    config_schema = {
        "type": "object",
        "required": ["rtsp_url", "hls_host"],
        "properties": {
            "rtsp_url": {
                "type": "string",
                "title": "RTSP Stream URL",
                "description": "Full RTSP URL including credentials. e.g. rtsp://admin:pass@192.168.1.10:554/stream",
                "format": "uri",
            },
            "hls_host": {
                "type": "string",
                "title": "HLS Bridge Host",
                "description": "IP/hostname of the Raspberry Pi running camera_hls_bridge.py",
                "default": "192.168.1.100",
            },
            "hls_port": {
                "type": "integer",
                "title": "HLS Bridge Port",
                "default": 8090,
                "minimum": 1024,
                "maximum": 65535,
            },
            "mqtt_topic_prefix": {
                "type": "string",
                "title": "MQTT Status Topic Prefix",
                "description": "The bridge publishes status/motion events here.",
                "default": "barn/camera-01",
            },
            "record_motion_events": {
                "type": "boolean",
                "title": "Record Motion Detection Events",
                "default": True,
            },
        },
    }

    data_channels = [
        Channel("fps", "Frames Per Second", "fps", "float", min_value=0, max_value=60),
        Channel("motion", "Motion Detected", "", "bool"),
        Channel("stream_status", "Stream Status", "", "int"),  # 1=online, 0=offline
    ]

    def __init__(self, sensor_id: str, config: dict):
        super().__init__(sensor_id, config)
        self._client: aiomqtt.Client | None = None

    @property
    def hls_url(self) -> str:
        host = self.config.get("hls_host", "localhost")
        port = self.config.get("hls_port", 8090)
        return f"http://{host}:{port}/hls/{self.sensor_id}/index.m3u8"

    async def connect(self) -> None:
        self._client = aiomqtt.Client(
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            identifier=f"gdf-{self.sensor_id}-camera",
        )
        await self._client.__aenter__()
        prefix = self.config.get("mqtt_topic_prefix", f"gdf/{self.sensor_id}")
        await self._client.subscribe(f"{prefix}/camera_status")
        await self._client.subscribe(f"{prefix}/motion")
        self._running = True

    async def stream(self) -> AsyncIterator[SensorReading]:
        async for message in self._client.messages:
            if not self._running:
                break
            channel = str(message.topic).rsplit("/", 1)[-1]
            try:
                payload = json.loads(message.payload)
                if channel == "camera_status":
                    fps = float(payload.get("fps", 0))
                    online = 1 if payload.get("status") == "online" else 0
                    yield SensorReading(sensor_id=self.sensor_id, channel="fps", value=fps, unit="fps")
                    yield SensorReading(sensor_id=self.sensor_id, channel="stream_status", value=online, unit="")
                elif channel == "motion":
                    detected = 1 if payload.get("detected") else 0
                    yield SensorReading(sensor_id=self.sensor_id, channel="motion", value=detected, unit="",
                                        metadata={"confidence": payload.get("confidence", 0)})
            except (ValueError, KeyError, TypeError):
                continue

    async def disconnect(self) -> None:
        self._running = False
        if self._client:
            await self._client.__aexit__(None, None, None)
