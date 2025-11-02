"""add email to users and email notification tables

Revision ID: c7c9f1f4f1c0
Revises: f1b0c738c6e8
Create Date: 2025-02-14 00:05:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "c7c9f1f4f1c0"
down_revision = "f1b0c738c6e8"
branch_labels = None
depends_on = None


email_trigger_enum = sa.Enum(
    "user_created",
    "user_updated",
    "user_deleted",
    "user_limited",
    "user_expired",
    "user_enabled",
    "user_disabled",
    "data_usage_reset",
    "data_reset_by_next",
    "subscription_revoked",
    "reached_usage_percent",
    "reached_days_left",
    name="emailnotificationtrigger",
)


def upgrade() -> None:
    bind = op.get_bind()
    email_trigger_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "email_smtp_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default=sa.text("587")),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("use_ssl", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "email_notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trigger", email_trigger_enum, nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("email_notification_preferences")
    op.drop_table("email_smtp_settings")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")

    bind = op.get_bind()
    email_trigger_enum.drop(bind, checkfirst=True)
