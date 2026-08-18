"""api keys callbacks and uploads

Revision ID: 5b7d9e4c2a11
Revises: 2682ab3db262
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5b7d9e4c2a11"
down_revision = "2682ab3db262"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(length=80), nullable=False),
        sa.Column("key_id", sa.String(length=40), nullable=False),
        sa.Column("secret_hash", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("key_id"),
    )
    op.create_index("ix_merchant_api_keys_merchant_id", "merchant_api_keys", ["merchant_id"])
    op.create_index("ix_merchant_api_keys_key_id", "merchant_api_keys", ["key_id"])
    op.create_table(
        "callback_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("callback_url", sa.String(length=500), nullable=False),
        sa.Column("request_body", postgresql.JSONB(), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_body", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_callback_attempts_order_id", "callback_attempts", ["order_id"])
    op.create_index("ix_callback_attempts_status", "callback_attempts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_callback_attempts_status", table_name="callback_attempts")
    op.drop_index("ix_callback_attempts_order_id", table_name="callback_attempts")
    op.drop_table("callback_attempts")
    op.drop_index("ix_merchant_api_keys_key_id", table_name="merchant_api_keys")
    op.drop_index("ix_merchant_api_keys_merchant_id", table_name="merchant_api_keys")
    op.drop_table("merchant_api_keys")
