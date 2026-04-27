"""
Weight / Load Cell sensor type (HX711-based via ESP32 over MQTT).

MQTT payload: {"value": 4.21, "unit": "kg", "tare": 0.0}
Topic: gdf/{sensor_id}/weight
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import aiomqtt

from app.plugins.base import SensorAdapter, SensorReading, Channel
from app.core.config import settings

logger = logging.getLogger(__name__)


class WeightSensor(SensorAdapter):
    sensor_type = "weight_hx711"
    display_name = "Weight / Load Cell (HX711)"
    protocol = "mqtt"
    icon = "scale"

    config_schema = {
        "type": "object",
        "required": ["mqtt_topic_prefix"],
        "properties": {
            "mqtt_topic_prefix": {
                "type": "string",
                "title": "MQTT Topic Prefix",
                "description": "e.g. barn/milk-scale-01",
                "default": "barn/scale01",
            },
            "capacity_kg": {
                "type": "number",
                "title": "Max Capacity (kg)",
                "description": "Maximum weight capacity of the load cell.",
                "default": 50,
                "minimum": 0.1,
            },
            "unit": {
                "type": "string",
                "title": "Weight Unit",
                "enum": ["kg", "g", "lb"],
                "default": "kg",
            },
            "tare_on_connect": {
                "type": "boolean",
                "title": "Auto-tare on Connect",
                "description": "Send tare command when sensor connects.",
                "default": False,
            },
        },
    }

    data_channels = [
        Channel("weight", "Weight", "kg", "float", min_value=0, max_value=500),
    ]

    def __init__(self, sensor_id: str, config: dict):
        super().__init__(sensor_id, config)
        self._client: aiomqtt.Client | None = None

    async def connect(self) -> None:
        self._client = aiomqtt.Client(
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            identifier=f"gdf-{self.sensor_id}-weight",
        )
        await self._client.__aenter__()
        prefix = self.config.get("mqtt_topic_prefix", f"gdf/{self.sensor_id}")
        await self._client.subscribe(f"{prefix}/weight")
        self._running = True

    async def stream(self) -> AsyncIterator[SensorReading]:
        async for message in self._client.messages:
            if not self._running:
                break
            try:
                payload = json.loads(message.payload)
                value = float(payload["value"] if isinstance(payload, dict) else payload)
                unit = payload.get("unit", self.config.get("unit", "kg")) if isinstance(payload, dict) else "kg"
            except (ValueError, KeyError, TypeError):
                logger.warning("Bad weight payload: %r", message.payload)
                continue
            yield SensorReading(sensor_id=self.sensor_id, channel="weight", value=value, unit=unit)

    async def disconnect(self) -> None:
        self._running = False
        if self._client:
            await self._client.__aexit__(None, None, None)
