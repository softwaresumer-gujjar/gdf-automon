"""
Plan action service — evaluates enabled plans when a sensor reading arrives.
Called from alert_engine.evaluate_rules() after alert evaluation.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanAction

logger = logging.getLogger(__name__)


def _is_breached(value: float, plan: Plan) -> tuple[bool, str]:
    """Returns (breached, which_side: above_upper|below_lower|within)."""
    if plan.upper_limit is not None and value > plan.upper_limit:
        return True, "above_upper"
    if plan.lower_limit is not None and value < plan.lower_limit:
        return True, "below_lower"
    return False, "within"


def _action_triggered(action: PlanAction, breach_side: str) -> bool:
    if not action.enabled:
        return False
    t = action.trigger_on
    if t == "any_breach":
        return True
    return t == breach_side


def _format_message(template: str, **kwargs) -> str:
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


async def evaluate_plans(
    sensor_id: str,
    channel: str,
    value: float,
    session: AsyncSession,
) -> None:
    try:
        result = await session.execute(
            select(Plan).where(
                Plan.sensor_id == uuid.UUID(sensor_id),
                Plan.channel == channel,
                Plan.enabled == True,
            )
        )
        plans = result.scalars().all()
        for plan in plans:
            breached, side = _is_breached(value, plan)
            if not breached:
                continue
            action_result = await session.execute(
                select(PlanAction).where(PlanAction.plan_id == plan.id)
            )
            for action in action_result.scalars().all():
                if _action_triggered(action, side):
                    msg = _format_message(
                        action.message_template,
                        sensor=str(sensor_id),
                        channel=channel,
                        value=f"{value:.2f}",
                        target=f"{plan.target_value:.2f}",
                        unit=plan.target_unit or "",
                        side=side,
                    )
                    import asyncio
                    asyncio.create_task(
                        _dispatch_action(action, plan, msg, uuid.UUID(sensor_id))
                    )
    except Exception as e:
        logger.error("Plan evaluation error for sensor %s/%s: %s", sensor_id, channel, e)


async def _dispatch_action(
    action: PlanAction,
    plan: Plan,
    message: str,
    sensor_id: uuid.UUID,
) -> None:
    from app.core.config import settings

    target_user_ids: list[uuid.UUID] | None = None
    if action.recipient_user_ids:
        target_user_ids = [uuid.UUID(str(uid)) for uid in action.recipient_user_ids]

    if action.action_type == "notification":
        from app.services.push_service import send_alert_notification
        await send_alert_notification(
            title=f"Plan Alert: {plan.name}",
            body=message,
            severity="warning",
            sensor_id=sensor_id,
            target_user_ids=target_user_ids,
        )

    elif action.action_type == "reminder":
        from app.services.push_service import send_alert_notification
        await send_alert_notification(
            title=f"Reminder: {plan.name}",
            body=message,
            severity="info",
            sensor_id=sensor_id,
            target_user_ids=target_user_ids,
        )

    elif action.action_type == "sms":
        if not settings.twilio_account_sid:
            logger.warning("Twilio not configured — skipping SMS action for plan %s", plan.id)
            return
        await _send_twilio_sms(message, action.config.get("phone", ""), settings)

    elif action.action_type == "call":
        if not settings.twilio_account_sid:
            logger.warning("Twilio not configured — skipping call action for plan %s", plan.id)
            return
        await _send_twilio_call(message, action.config.get("phone", ""), settings)


async def _send_twilio_sms(message: str, to_number: str, settings) -> None:
    if not to_number:
        logger.warning("No phone number configured for SMS action")
        return
    import asyncio
    try:
        from twilio.rest import Client
        def _send():
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            client.messages.create(body=message, from_=settings.twilio_from_number, to=to_number)
        await asyncio.to_thread(_send)
        logger.info("SMS sent to %s", to_number)
    except Exception as e:
        logger.error("Twilio SMS failed: %s", e)


async def _send_twilio_call(message: str, to_number: str, settings) -> None:
    if not to_number:
        logger.warning("No phone number configured for call action")
        return
    import asyncio
    # TwiML: read the message aloud
    twiml = f'<Response><Say>{message}</Say></Response>'
    try:
        from twilio.rest import Client
        def _call():
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            client.calls.create(
                twiml=twiml,
                from_=settings.twilio_from_number,
                to=to_number,
            )
        await asyncio.to_thread(_call)
        logger.info("Voice call initiated to %s", to_number)
    except Exception as e:
        logger.error("Twilio call failed: %s", e)
