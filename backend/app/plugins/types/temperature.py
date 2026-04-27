"""
Temperature / Humidity sensor type.
Supports SHT31, DHT22, BME280 and any sensor that publishes over MQTT.

MQTT payload format (JSON):
  {"value": 22.5, "unit": "°C"}
  or flat: 22.5

Topic convention: gdf/{sensor_id}/temperature  and  gdf/{sensor_id}/humidity
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


class TemperatureHumiditySensor(SensorAdapter):
    sensor_type = "temperature_humidity"
    display_name = "Temperature / Humidity Sensor"
    protocol = "mqtt"
    icon = "thermometer"

    config_schema = {
        "type": "object",
        "required": ["mqtt_topic_prefix"],
        "properties": {
            "mqtt_topic_prefix": {
                "type": "string",
                "title": "MQTT Topic Prefix",
                "description": "Topic prefix for this device, e.g. barn/sensor01. Readings published to {prefix}/temperature and {prefix}/humidity.",
                "default": "barn/sensor01",
            },
            "poll_interval_seconds": {
                "type": "number",
                "title": "Expected Poll Interval (seconds)",
                "description": "How often the sensor publishes. Used for offline detection.",
                "default": 30,
                "minimum": 1,
                "maximum": 3600,
            },
            "temperature_unit": {
                "type": "string",
                "title": "Temperature Unit",
                "enum": ["°C", "°F"],
                "default": "°C",
            },
        },
    }

    data_channels = [
        Channel("temperature", "Temperature", "°C", "float", min_value=-40, max_value=85),
        Channel("humidity", "Humidity", "%RH", "float", min_value=0, max_value=100),
    ]

    def __init__(self, sensor_id: str, config: dict):
        super().__init__(sensor_id, config)
        self._client: aiomqtt.Client | None = None
        self._queue: asyncio.Queue[SensorReading] = asyncio.Queue(maxsize=100)

    async def connect(self) -> None:
        self._client = aiomqtt.Client(
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            identifier=f"gdf-{self.sensor_id}-monitor",
        )
        await self._client.__aenter__()
        prefix = self.config.get("mqtt_topic_prefix", f"gdf/{self.sensor_id}")
        await self._client.subscribe(f"{prefix}/temperature")
        await self._client.subscribe(f"{prefix}/humidity")
        self._running = True

    async def stream(self) -> AsyncIterator[SensorReading]:
        async for message in self._client.messages:
            if not self._running:
                break
            parts = str(message.topic).rsplit("/", 1)
            channel = parts[-1] if len(parts) >= 2 else "unknown"
            try:
                payload = json.loads(message.payload)
                value = float(payload["value"] if isinstance(payload, dict) else payload)
                unit = payload.get("unit", self.config.get("temperature_unit", "°C")) if isinstance(payload, dict) else "°C"
            except (ValueError, KeyError, TypeError):
                logger.warning("Bad payload on %s: %r", message.topic, message.payload)
                continue
            yield SensorReading(sensor_id=self.sensor_id, channel=channel, value=value, unit=unit)

    async def disconnect(self) -> None:
        self._running = False
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
