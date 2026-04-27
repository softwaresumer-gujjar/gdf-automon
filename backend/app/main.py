"""GDF-AutoMon FastAPI application entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.mqtt_bridge import run_mqtt_bridge
from app.plugins.registry import registry

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    registry.auto_discover()
    logger.info("Registered %d sensor types", len(registry._types))

    bridge_task = asyncio.create_task(run_mqtt_bridge(SessionLocal))

    from app.services.task_reminder_service import run_task_reminder_loop
    reminder_task = asyncio.create_task(run_task_reminder_loop(SessionLocal))

    yield

    # Shutdown
    for task in (bridge_task, reminder_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="GDF-AutoMon API",
    description="Goat & Dairy Farm Automated Monitoring Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from app.api import (
    sensors, telemetry, alerts, push, stream,
    auth, locations, users, notifications,
    plans, tasks, chat,
)

app.include_router(auth.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(sensors.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(stream.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "gdf-automon-backend"}
