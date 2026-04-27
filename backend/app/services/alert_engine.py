"""
Alert engine: evaluates alert rules on each incoming reading.
Runs asynchronously with <5ms target latency for in-memory checks.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertRule, ActiveAlert

logger = logging.getLogger(__name__)


def _check_condition(value: float, condition: str, threshold: float | None, threshold_max: float | None) -> bool:
    if threshold is None:
        return False
    if condition == "gt":
        return value > threshold
    if condition == "lt":
        return value < threshold
    if condition == "eq":
        return abs(value - threshold) < 1e-9
    if condition == "outside_range" and threshold_max is not None:
        return value < threshold or value > threshold_max
    return False


async def evaluate_rules(sensor_id: str, channel: str, value: float, session: AsyncSession) -> None:
    try:
        result = await session.execute(
            select(AlertRule).where(
                AlertRule.sensor_id == uuid.UUID(sensor_id),
                AlertRule.channel == channel,
                AlertRule.enabled == True,
            )
        )
        rules = result.scalars().all()

        for rule in rules:
            if _check_condition(value, rule.condition, rule.threshold, rule.threshold_max):
                await _fire_alert(rule, value, session)
    except Exception as e:
        logger.error("Alert evaluation error for sensor %s/%s: %s", sensor_id, channel, e)

    # Evaluate plan targets in parallel
    from app.services.plan_action_service import evaluate_plans
    await evaluate_plans(sensor_id, channel, value, session)


async def _fire_alert(rule: AlertRule, value: float, session: AsyncSession) -> None:
    msg = f"Sensor reading {value:.2f} triggered rule: {rule.condition} {rule.threshold}"

    alert = ActiveAlert(
        rule_id=rule.id,
        sensor_id=rule.sensor_id,
        channel=rule.channel,
        triggered_value=value,
        severity=rule.severity,
        message=msg,
        triggered_at=datetime.now(timezone.utc),
    )
    session.add(alert)
    await session.flush()

    # Dispatch push notification only to permitted, opted-in users
    from app.services.push_service import send_alert_notification
    import asyncio
    asyncio.create_task(send_alert_notification(
        title=f"{'🔴' if rule.severity == 'critical' else '⚠️'} Sensor Alert",
        body=msg,
        severity=rule.severity,
        sensor_id=rule.sensor_id,
    ))
    logger.warning("Alert fired: %s", msg)
