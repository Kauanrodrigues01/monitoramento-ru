"""add avg_status_value to queue_snapshots

Revision ID: f977b3c0b6ec
Revises: fb141e074154
Create Date: 2026-06-04 22:03:23.821690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f977b3c0b6ec'
down_revision: Union[str, Sequence[str], None] = 'fb141e074154'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('queue_snapshots', sa.Column('avg_status_value', sa.Numeric(precision=3, scale=2), nullable=True))
    op.create_check_constraint(
        "ck_avg_status_value_range",
        "queue_snapshots",
        "avg_status_value IS NULL OR (avg_status_value >= 0.00 AND avg_status_value <= 3.00)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_avg_status_value_range", "queue_snapshots", type_="check")
    op.drop_column('queue_snapshots', 'avg_status_value')
