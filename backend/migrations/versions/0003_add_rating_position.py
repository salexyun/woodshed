"""Add rating.position

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, so the previous release can keep inserting ratings without one; nulls
    # never collide in the unique constraint.
    op.add_column("rating", sa.Column("position", sa.Integer(), nullable=True))
    op.create_unique_constraint(
        "rating_session_position", "rating", ["session_id", "position"]
    )


def downgrade() -> None:
    op.drop_constraint("rating_session_position", "rating")
    op.drop_column("rating", "position")
