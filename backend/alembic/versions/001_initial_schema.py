"""initial schema — complete GDF-AutoMon database

Revision ID: 001
Revises:
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    # TimescaleDB is optional — dev environments may not have it.
    op.execute("""
        DO $$ BEGIN
            CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'timescaledb not available — skipping (readings will be plain Postgres table)';
        END; $$
    """)
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── locations ─────────────────────────────────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(300), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── sensors ───────────────────────────────────────────────────────────────
    op.create_table(
        "sensors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sensor_type", sa.String(100), nullable=False),
        sa.Column("protocol", sa.String(50), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("location_id", UUID(as_uuid=True),
                  sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_sensors_location", "sensors", ["location_id"])

    # ── sensor_readings ───────────────────────────────────────────────────────
    op.create_table(
        "sensor_readings",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor_id", UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.PrimaryKeyConstraint("time", "sensor_id", "channel"),
    )
    op.create_index("idx_sensor_readings_sensor_time", "sensor_readings", ["sensor_id", "time"])

    # ── alert_rules ───────────────────────────────────────────────────────────
    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("sensor_id", UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("condition", sa.String(20), nullable=False),
        sa.Column("threshold", sa.Float, nullable=True),
        sa.Column("threshold_max", sa.Float, nullable=True),
        sa.Column("severity", sa.String(20), server_default="warning"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_alert_rules_sensor", "alert_rules", ["sensor_id"])

    # ── active_alerts ─────────────────────────────────────────────────────────
    op.create_table(
        "active_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", UUID(as_uuid=True),
                  sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sensor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("triggered_value", sa.Float, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── push_subscriptions ────────────────────────────────────────────────────
    op.create_table(
        "push_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("endpoint", sa.String(1000), unique=True, nullable=False),
        sa.Column("p256dh", sa.String(200), nullable=False),
        sa.Column("auth", sa.String(100), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── user_location_permissions ─────────────────────────────────────────────
    op.create_table(
        "user_location_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True),
                  sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "location_id", name="uq_user_location"),
    )

    # ── user_sensor_permissions ───────────────────────────────────────────────
    op.create_table(
        "user_sensor_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sensor_id", UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "sensor_id", name="uq_user_sensor"),
    )

    # ── notification_preferences ──────────────────────────────────────────────
    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("location_id", UUID(as_uuid=True),
                  sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("sensor_id", UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=True),
        sa.Column("push_enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── password_reset_tokens ─────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("token", sa.String(128), unique=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_prt_token", "password_reset_tokens", ["token"])

    # ── plans ─────────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sensor_id", UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("target_value", sa.Float, nullable=False),
        sa.Column("target_unit", sa.String(50), nullable=True),
        sa.Column("lower_limit", sa.Float, nullable=True),
        sa.Column("upper_limit", sa.Float, nullable=True),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_by_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── plan_actions ──────────────────────────────────────────────────────────
    op.create_table(
        "plan_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("plan_id", UUID(as_uuid=True),
                  sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("trigger_on", sa.String(50), nullable=False, server_default="any_breach"),
        sa.Column("message_template", sa.String(500), nullable=False,
                  server_default="Sensor {sensor} channel {channel}: value {value} breached target {target}"),
        sa.Column("recipient_user_ids", JSONB, nullable=True),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── tasks ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_by_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("submitted_by_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_note", sa.Text, nullable=True),
        sa.Column("reminder_sent_24h", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── task_assignments ──────────────────────────────────────────────────────
    op.create_table(
        "task_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_user"),
    )

    # ── task_attachments ──────────────────────────────────────────────────────
    op.create_table(
        "task_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("original_name", sa.String(300), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("uploaded_by_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── chat_rooms ────────────────────────────────────────────────────────────
    op.create_table(
        "chat_rooms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("room_type", sa.String(20), nullable=False, server_default="topic"),
        sa.Column("task_id", UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, unique=True),
        sa.Column("created_by_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── chat_room_members ─────────────────────────────────────────────────────
    op.create_table(
        "chat_room_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("room_id", UUID(as_uuid=True),
                  sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("room_id", "user_id", name="uq_room_member"),
    )

    # ── chat_messages ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("room_id", UUID(as_uuid=True),
                  sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_chat_messages_room", "chat_messages", ["room_id", "created_at"])

    # ── chat_attachments ──────────────────────────────────────────────────────
    op.create_table(
        "chat_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True),
                  sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("original_name", sa.String(300), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False, server_default="other"),
        sa.Column("file_size", sa.Integer, server_default="0"),
        sa.Column("mime_type", sa.String(100), nullable=False,
                  server_default="application/octet-stream"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_attachments")
    op.drop_table("chat_messages")
    op.drop_table("chat_room_members")
    op.drop_table("chat_rooms")
    op.drop_table("task_attachments")
    op.drop_table("task_assignments")
    op.drop_table("tasks")
    op.drop_table("plan_actions")
    op.drop_table("plans")
    op.drop_table("password_reset_tokens")
    op.drop_table("notification_preferences")
    op.drop_table("user_sensor_permissions")
    op.drop_table("user_location_permissions")
    op.drop_table("push_subscriptions")
    op.drop_table("active_alerts")
    op.drop_table("alert_rules")
    op.drop_table("sensor_readings")
    op.drop_table("sensors")
    op.drop_table("users")
    op.drop_table("locations")
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
    op.execute("DROP EXTENSION IF EXISTS timescaledb")
