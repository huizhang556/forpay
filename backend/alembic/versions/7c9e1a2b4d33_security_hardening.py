"""security hardening

Revision ID: 7c9e1a2b4d33
Revises: 5b7d9e4c2a11
"""
import sqlalchemy as sa
from alembic import op

revision = "7c9e1a2b4d33"
down_revision = "5b7d9e4c2a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("merchant_api_keys", sa.Column("secret_encrypted", sa.Text()))
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=100)))
    op.create_index("ix_orders_idempotency_key", "orders", ["idempotency_key"])
    op.create_index("ix_orders_merchant_idempotency", "orders", ["merchant_id", "idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_orders_merchant_idempotency", table_name="orders")
    op.drop_index("ix_orders_idempotency_key", table_name="orders")
    op.drop_column("orders", "idempotency_key")
    op.drop_column("merchant_api_keys", "secret_encrypted")
