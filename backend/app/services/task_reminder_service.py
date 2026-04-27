"""
Background task: checks for tasks with deadlines within 24 hours
and sends push reminders to assigned users.
Runs every 30 minutes via asyncio loop started in main.py lifespan.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_SECONDS = 30 * 60  # 30 minutes
REMINDER_WINDOW_HOURS = 24


async def _send_reminders(session_factory) -> None:
    from app.models.task import Task, TaskAssignment
    from app.services.push_service import send_alert_notification

    now = datetime.now(timezone.utc)
    window = now + timedelta(hours=REMINDER_WINDOW_HOURS)

    async with session_factory() as session:
        result = await session.execute(
            select(Task).where(
                Task.deadline >= now,
                Task.deadline <= window,
                Task.status.in_(["open", "rejected"]),
                Task.reminder_sent_24h == False,
            )
        )
        tasks = result.scalars().all()

        for task in tasks:
            # Get assigned user IDs
            assign_result = await session.execute(
                select(TaskAssignment.user_id).where(TaskAssignment.task_id == task.id)
            )
            user_ids = [r for r, in assign_result.all()]
            if not user_ids:
                continue

            delta = task.deadline - now
            hours_left = int(delta.total_seconds() / 3600)
            msg = f"Task '{task.title}' is due in ~{hours_left} hour{'s' if hours_left != 1 else ''}. Please complete it."

            await send_alert_notification(
                title="Task Due Soon",
                body=msg,
                severity="warning",
                sensor_id=None,
                target_user_ids=user_ids,
            )

            task.reminder_sent_24h = True
            logger.info("Sent 24h reminder for task %s to %d users", task.id, len(user_ids))

        await session.commit()


async def run_task_reminder_loop(session_factory) -> None:
    """Long-running loop — cancel on shutdown."""
    logger.info("Task reminder service started (interval: %ds)", REMINDER_INTERVAL_SECONDS)
    while True:
        try:
            await _send_reminders(session_factory)
        except Exception as e:
            logger.error("Task reminder error: %s", e)
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
