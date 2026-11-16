"""Add session.steps

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, so the previous release can keep inserting sessions without steps.
    op.add_column("session", sa.Column("steps", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("session", "steps")
