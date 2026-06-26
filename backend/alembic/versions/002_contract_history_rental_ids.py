"""合同增加 history_rental_ids 字段

Revision ID: 002
Revises: 001
Create Date: 2025-01-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'contract',
        sa.Column(
            'history_rental_ids',
            sa.JSON(),
            nullable=True,
            comment='回收时快照的设备ID列表，方便复盘',
        ),
    )


def downgrade() -> None:
    op.drop_column('contract', 'history_rental_ids')
