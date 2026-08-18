"""initial payment schema

Revision ID: 2682ab3db262
Revises: 
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '2682ab3db262'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "payment_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("channel_type", sa.String(length=20), nullable=False),
        sa.Column("account_label", sa.String(length=120), nullable=False),
        sa.Column("qr_code_url", sa.String(length=500)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(length=80), nullable=False),
        sa.Column("out_trade_no", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("display_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("payment_channels.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notify_url", sa.String(length=500)),
        sa.Column("return_url", sa.String(length=500)),
        sa.Column("buyer_name", sa.String(length=120)),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("out_trade_no"),
    )
    op.create_index("ix_orders_status_expires", "orders", ["status", "expires_at"])
    op.create_index("ix_orders_merchant_created", "orders", ["merchant_id", "created_at"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_out_trade_no", "orders", ["out_trade_no"])
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id")),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payment_events_order_id", "payment_events", ["order_id"])
    op.create_table(
        "payment_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("payment_channels.id"), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payer_name", sa.String(length=120)),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("match_status", sa.String(length=30), nullable=False),
        sa.Column("matched_order_id", sa.Integer(), sa.ForeignKey("orders.id")),
        sa.Column("notification_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_payment_notifications_match_status", "payment_notifications", ["match_status"])

def downgrade() -> None:
    op.drop_index("ix_payment_notifications_match_status", table_name="payment_notifications")
    op.drop_table("payment_notifications")
    op.drop_index("ix_payment_events_order_id", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_index("ix_orders_out_trade_no", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_merchant_created", table_name="orders")
    op.drop_index("ix_orders_status_expires", table_name="orders")
    op.drop_table("orders")
    op.drop_table("payment_channels")
