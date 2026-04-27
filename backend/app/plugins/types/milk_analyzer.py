"""
Milk Analyzer sensor type — Lactoscan / Milkoscan via RS-232 serial bridge.

The Raspberry Pi bridge script (sensor-edge/raspberry-pi/lactoscan_bridge.py)
reads the serial output and publishes structured JSON to MQTT:

MQTT payload: {
  "fat": 3.8, "protein": 3.2, "lactose": 4.7,
  "somatic_cells": 180000, "temperature": 4.2,
  "sample_id": "cow_007", "unit": "%"
}
Topics: gdf/{sensor_id}/fat, /protein, /lactose, /somatic_cells, /milk_temp
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import aiomqtt

from app.plugins.base import SensorAdapter, SensorReading, Channel
from app.core.config import settings

logger = logging.getLogger(__name__)

MILK_CHANNELS = {
    "fat": Channel("fat", "Fat Content", "%", "float", min_value=0, max_value=10),
    "protein": Channel("protein", "Protein Content", "%", "float", min_value=0, max_value=6),
    "lactose": Channel("lactose", "Lactose Content", "%", "float", min_value=0, max_value=6),
    "somatic_cells": Channel("somatic_cells", "Somatic Cell Count", "cells/mL", "int", min_value=0, max_value=2_000_000),
    "milk_temp": Channel("milk_temp", "Milk Temperature", "°C", "float", min_value=0, max_value=45),
}


class MilkAnalyzerSensor(SensorAdapter):
    sensor_type = "milk_analyzer_lactoscan"
    display_name = "Milk Analyzer (Lactoscan / Milkoscan)"
    protocol = "mqtt"
    icon = "droplets"

    config_schema = {
        "type": "object",
        "required": ["mqtt_topic_prefix"],
        "properties": {
            "mqtt_topic_prefix": {
                "type": "string",
                "title": "MQTT Topic Prefix",
                "description": "Topic prefix where the Raspberry Pi bridge publishes. e.g. barn/lactoscan-01",
                "default": "barn/lactoscan-01",
            },
            "scc_alert_threshold": {
                "type": "integer",
                "title": "SCC Alert Threshold (cells/mL)",
                "description": "Trigger an alert when SCC exceeds this value. Regulatory limit is typically 200,000.",
                "default": 200000,
                "minimum": 0,
            },
            "fat_min": {
                "type": "number",
                "title": "Minimum Fat % (alert below)",
                "default": 2.5,
            },
            "fat_max": {
                "type": "number",
                "title": "Maximum Fat % (alert above)",
                "default": 5.5,
            },
        },
    }

    data_channels = list(MILK_CHANNELS.values())

    def __init__(self, sensor_id: str, config: dict):
        super().__init__(sensor_id, config)
        self._client: aiomqtt.Client | None = None

    async def connect(self) -> None:
        self._client = aiomqtt.Client(
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            identifier=f"gdf-{self.sensor_id}-milk",
        )
        await self._client.__aenter__()
        prefix = self.config.get("mqtt_topic_prefix", f"gdf/{self.sensor_id}")
        for channel in MILK_CHANNELS:
            await self._client.subscribe(f"{prefix}/{channel}")
        self._running = True

    async def stream(self) -> AsyncIterator[SensorReading]:
        async for message in self._client.messages:
            if not self._running:
                break
            channel = str(message.topic).rsplit("/", 1)[-1]
            if channel not in MILK_CHANNELS:
                continue
            try:
                payload = json.loads(message.payload)
                value = float(payload["value"] if isinstance(payload, dict) else payload)
                unit = MILK_CHANNELS[channel].unit
            except (ValueError, KeyError, TypeError):
                continue
            yield SensorReading(sensor_id=self.sensor_id, channel=channel, value=value, unit=unit)

    async def disconnect(self) -> None:
        self._running = False
        if self._client:
            await self._client.__aexit__(None, None, None)
