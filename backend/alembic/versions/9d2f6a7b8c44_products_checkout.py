"""products and protected checkout

Revision ID: 9d2f6a7b8c44
Revises: 7c9e1a2b4d33
"""
import sqlalchemy as sa
from alembic import op

revision = "9d2f6a7b8c44"
down_revision = "7c9e1a2b4d33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_products_merchant_id", "products", ["merchant_id"])
    op.create_index("ix_products_enabled", "products", ["enabled"])
    op.create_table(
        "product_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("payment_channels.id"), nullable=False),
        sa.Column("fixed_amount", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("orders", sa.Column("public_token", sa.String(length=64)))
    op.add_column("orders", sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")))
    op.execute("UPDATE orders SET public_token = md5(random()::text || clock_timestamp()::text) WHERE public_token IS NULL")
    op.alter_column("orders", "public_token", nullable=False)
    op.create_index("ix_orders_public_token", "orders", ["public_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_orders_public_token", table_name="orders")
    op.drop_column("orders", "product_id")
    op.drop_column("orders", "public_token")
    op.drop_table("product_channels")
    op.drop_index("ix_products_enabled", table_name="products")
    op.drop_index("ix_products_merchant_id", table_name="products")
    op.drop_table("products")
