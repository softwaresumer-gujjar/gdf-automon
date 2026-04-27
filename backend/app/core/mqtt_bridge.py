"""
MQTT bridge: subscribes to gdf/# on EMQX, decodes messages,
writes to TimescaleDB, and publishes to Redis for live dashboard.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

import aiomqtt

from app.core.config import settings
from app.core.redis_client import publish_reading

logger = logging.getLogger(__name__)


async def _handle_message(topic: str, payload: bytes, db_session_factory):
    """Parse gdf/{sensor_id}/{channel} messages and persist them."""
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "gdf":
        return

    _, sensor_id, channel = parts

    try:
        data = json.loads(payload)
        value = float(data.get("value", data))  # support {"value":x} or bare number
        unit = data.get("unit", "")
        ts = data.get("ts", datetime.now(timezone.utc).isoformat())
    except (ValueError, TypeError):
        logger.warning("Unparseable MQTT payload on %s: %r", topic, payload)
        return

    # Persist to TimescaleDB
    async with db_session_factory() as session:
        from app.services.ingestion import insert_reading
        await insert_reading(session, sensor_id, channel, value, unit, ts)

    # Publish to Redis for Socket.io live push
    await publish_reading(sensor_id, channel, value, unit, ts)


async def run_mqtt_bridge(db_session_factory):
    """Long-running task: connects to EMQX and processes all sensor messages."""
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                identifier="gdf-backend-bridge",
            ) as client:
                logger.info("MQTT bridge connected to %s:%d", settings.mqtt_host, settings.mqtt_port)
                await client.subscribe(f"{settings.mqtt_topic_prefix}/#", qos=1)
                async for message in client.messages:
                    topic = str(message.topic)
                    asyncio.create_task(_handle_message(topic, message.payload, db_session_factory))
        except aiomqtt.MqttError as e:
            logger.error("MQTT connection error: %s — retrying in 5s", e)
            await asyncio.sleep(5)
