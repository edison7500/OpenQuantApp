"""add market type to symbol metadata

Revision ID: 3d45ab61a9c2
Revises: 9a60051f822f
Create Date: 2026-07-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3d45ab61a9c2"
down_revision: Union[str, Sequence[str], None] = "9a60051f822f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symbolmeta",
        sa.Column("market_type", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("symbolmeta", "market_type")
