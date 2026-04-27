"""
Generic sensor plugin system.

Every sensor type implements SensorAdapter and describes itself via:
  - sensor_type: str — unique slug, e.g. "temperature_sht31"
  - config_schema: dict — JSON Schema for the configuration form in AddSensorWizard
  - data_channels: list[Channel] — the data fields this sensor produces

The frontend's AddSensorWizard fetches /api/sensors/types and renders
a form from config_schema — no frontend changes needed for new sensor types.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Any


@dataclass
class Channel:
    name: str          # e.g. "temperature"
    label: str         # e.g. "Temperature"
    unit: str          # e.g. "°C"
    value_type: str    # "float" | "int" | "bool" | "string"
    min_value: float | None = None
    max_value: float | None = None


@dataclass
class SensorReading:
    sensor_id: str
    channel: str
    value: float | int | bool | str
    unit: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class SensorAdapter(ABC):
    """
    Abstract base class for all sensor type implementations.

    Subclasses must set class-level attributes:
        sensor_type, display_name, protocol, config_schema, data_channels

    And implement:
        connect(), stream(), disconnect()
    """

    # Class-level descriptor — set on each subclass
    sensor_type: str = ""         # Unique slug, e.g. "temperature_sht31"
    display_name: str = ""        # Human label, e.g. "Temperature Sensor (SHT31)"
    protocol: str = ""            # "mqtt" | "modbus" | "serial" | "http" | "rtsp"
    icon: str = "thermometer"     # Icon name for the UI card

    # JSON Schema describing the config fields for this sensor type.
    # Used by the frontend AddSensorWizard to render the config form.
    config_schema: dict = {}

    # Channels this sensor produces — used to configure chart widgets.
    data_channels: list[Channel] = []

    def __init__(self, sensor_id: str, config: dict):
        self.sensor_id = sensor_id
        self.config = config
        self._running = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the sensor/device."""

    @abstractmethod
    async def stream(self) -> AsyncIterator[SensorReading]:
        """
        Yield SensorReading objects continuously until disconnect() is called.
        Implementations should yield at least one reading per poll interval.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly close the sensor connection."""

    async def test_connection(self) -> tuple[bool, str]:
        """Test connectivity without starting persistent stream. Returns (ok, message)."""
        try:
            await asyncio.wait_for(self.connect(), timeout=10.0)
            await self.disconnect()
            return True, "Connection successful"
        except asyncio.TimeoutError:
            return False, "Connection timed out after 10s"
        except Exception as e:
            return False, str(e)

    def to_dict(self) -> dict:
        return {
            "sensor_type": self.sensor_type,
            "display_name": self.display_name,
            "protocol": self.protocol,
            "icon": self.icon,
            "config_schema": self.config_schema,
            "data_channels": [
                {
                    "name": ch.name,
                    "label": ch.label,
                    "unit": ch.unit,
                    "value_type": ch.value_type,
                    "min_value": ch.min_value,
                    "max_value": ch.max_value,
                }
                for ch in self.data_channels
            ],
        }
