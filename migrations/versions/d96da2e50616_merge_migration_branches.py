"""merge migration branches

Revision ID: d96da2e50616
Revises: 646ed07bb03a, ba8a3336c786
Create Date: 2026-09-25 21:00:22.421072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd96da2e50616'
down_revision: Union[str, Sequence[str], None] = ('646ed07bb03a', 'ba8a3336c786')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
