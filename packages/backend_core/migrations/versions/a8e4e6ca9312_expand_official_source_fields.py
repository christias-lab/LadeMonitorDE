"""expand official source fields

Revision ID: a8e4e6ca9312
Revises: dc1b7cbfdafe
Create Date: 2026-07-30 00:35:00
"""

import sqlalchemy as sa
from alembic import op

revision = "a8e4e6ca9312"
down_revision = "dc1b7cbfdafe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "connectors",
        "connector_type",
        existing_type=sa.String(length=64),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "static_capabilities",
        "value",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "static_capabilities",
        "value",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "connectors",
        "connector_type",
        existing_type=sa.Text(),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
