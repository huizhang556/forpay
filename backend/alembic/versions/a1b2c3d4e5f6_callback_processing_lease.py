"""add callback processing lease timestamp

Revision ID: a1b2c3d4e5f6
Revises: 9d2f6a7b8c44
"""
import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "9d2f6a7b8c44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("callback_attempts", sa.Column("processing_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("callback_attempts", "processing_at")
