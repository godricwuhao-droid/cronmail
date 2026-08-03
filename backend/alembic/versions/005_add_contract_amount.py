"""005_add_contract_amount

Revision ID: 005
Revises: c587c343402d
Create Date: 2026-07-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = 'c587c343402d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'contract',
        sa.Column(
            'amount',
            sa.Numeric(12, 2),
            nullable=True,
            comment='合同金额',
        ),
    )


def downgrade() -> None:
    op.drop_column('contract', 'amount')
