"""add_sort_order_to_all_contracts

Revision ID: 012
Revises: 011
Create Date: 2026-07-23

变更：
  - contract 表新增 sort_order 字段 (Integer, default=0, NOT NULL)
  - satellite_data_contract 表新增 sort_order 字段 (Integer, default=0, NOT NULL)
  - compute_service_contract 表新增 sort_order 字段 (Integer, default=0, NOT NULL)
  - 所有字段 nullable=False, default=0，向后兼容，现有数据自动为 0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否已存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # ---- contract 新增 sort_order ----
    if not _column_exists('contract', 'sort_order'):
        op.add_column(
            'contract',
            sa.Column(
                'sort_order',
                sa.Integer,
                nullable=False,
                server_default='0',
                comment='排序序号',
            ),
        )

    # ---- satellite_data_contract 新增 sort_order ----
    if not _column_exists('satellite_data_contract', 'sort_order'):
        op.add_column(
            'satellite_data_contract',
            sa.Column(
                'sort_order',
                sa.Integer,
                nullable=False,
                server_default='0',
                comment='排序序号',
            ),
        )

    # ---- compute_service_contract 新增 sort_order ----
    if not _column_exists('compute_service_contract', 'sort_order'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'sort_order',
                sa.Integer,
                nullable=False,
                server_default='0',
                comment='排序序号',
            ),
        )


def downgrade() -> None:
    for table_name in ['compute_service_contract', 'satellite_data_contract', 'contract']:
        if _column_exists(table_name, 'sort_order'):
            op.drop_column(table_name, 'sort_order')
