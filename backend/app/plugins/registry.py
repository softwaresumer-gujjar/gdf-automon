"""
SensorTypeRegistry — discovers and manages all sensor type implementations.

On startup, imports all modules in plugins/types/ and auto-registers any
SensorAdapter subclass found there. New sensor types are added by:
  1. Creating a new file in plugins/types/{name}.py
  2. Defining a class that extends SensorAdapter
  No manual registration needed.
"""
from __future__ import annotations

import importlib
import pkgutil
import logging
from typing import Type

from app.plugins.base import SensorAdapter

logger = logging.getLogger(__name__)


class SensorTypeRegistry:
    def __init__(self):
        self._types: dict[str, Type[SensorAdapter]] = {}

    def register(self, cls: Type[SensorAdapter]):
        if not cls.sensor_type:
            raise ValueError(f"{cls.__name__} must define sensor_type")
        self._types[cls.sensor_type] = cls
        logger.info("Registered sensor type: %s (%s)", cls.sensor_type, cls.display_name)

    def get(self, sensor_type: str) -> Type[SensorAdapter] | None:
        return self._types.get(sensor_type)

    def create(self, sensor_type: str, sensor_id: str, config: dict) -> SensorAdapter:
        cls = self.get(sensor_type)
        if cls is None:
            raise ValueError(f"Unknown sensor type: {sensor_type!r}. Available: {list(self._types)}")
        return cls(sensor_id, config)

    def all_types(self) -> list[dict]:
        return [cls(sensor_id="preview", config={}).to_dict() for cls in self._types.values()]

    def auto_discover(self):
        """Import all modules in app/plugins/types/ to trigger class registration."""
        import app.plugins.types as types_pkg
        for _, module_name, _ in pkgutil.iter_modules(types_pkg.__path__):
            try:
                module = importlib.import_module(f"app.plugins.types.{module_name}")
                # Register any SensorAdapter subclasses found in the module
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, SensorAdapter)
                        and obj is not SensorAdapter
                        and obj.sensor_type
                    ):
                        self.register(obj)
            except Exception as e:
                logger.error("Failed to load sensor type module %s: %s", module_name, e)


# Global singleton
registry = SensorTypeRegistry()
