"""SSE (Server-Sent Events) streaming endpoint — /api/stream/{sensor_id}"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/{sensor_id}")
async def stream_sensor(sensor_id: str, request: Request):
    """
    SSE endpoint: subscribes to Redis Pub/Sub channel for this sensor
    and forwards events to the browser as Server-Sent Events.
    Used as a fallback when Socket.io is not available.
    """
    from app.core.redis_client import get_redis

    async def event_generator():
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.psubscribe(f"gdf:{sensor_id}:*")
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "pmessage":
                    data = message["data"]
                    yield f"data: {data}\n\n"
                else:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.punsubscribe(f"gdf:{sensor_id}:*")
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
