"""Add alert_rule_actions table and user profile fields

Revision ID: 003
Revises: 002
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── alert_rule_actions ────────────────────────────────────────────────────
    op.create_table(
        "alert_rule_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", UUID(as_uuid=True),
                  sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_alert_rule_actions_rule", "alert_rule_actions", ["rule_id"])

    # ── user profile fields ───────────────────────────────────────────────────
    op.add_column("users", sa.Column("phone", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("current_location", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("working_hours", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("duty", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "duty")
    op.drop_column("users", "working_hours")
    op.drop_column("users", "current_location")
    op.drop_column("users", "phone")
    op.drop_index("idx_alert_rule_actions_rule", table_name="alert_rule_actions")
    op.drop_table("alert_rule_actions")
