import redis.asyncio as aioredis
from app.core.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish_chat_message(room_id: str, message: dict):
    """Publish a chat message to Redis Pub/Sub for the Socket.io gateway."""
    import json
    r = await get_redis()
    await r.publish(f"chat:{room_id}", json.dumps(message))


async def publish_reading(sensor_id: str, channel: str, value: float, unit: str, ts: str):
    """Publish a sensor reading to Redis Pub/Sub for the Socket.io gateway."""
    import json
    r = await get_redis()
    payload = json.dumps({"sensor_id": sensor_id, "channel": channel, "value": value, "unit": unit, "ts": ts})
    await r.publish(f"gdf:{sensor_id}:{channel}", payload)
    # Also publish to the all-sensors channel for dashboard
    await r.publish("gdf:readings", payload)
