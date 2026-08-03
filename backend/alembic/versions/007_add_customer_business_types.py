"""007_add_customer_business_types

Revision ID: 007
Revises: 006
Create Date: 2026-07-10

变更：
  - customer 表新增 business_types 字段（JSON，多选）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否已存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('customer', 'business_types'):
        op.add_column(
            'customer',
            sa.Column(
                'business_types',
                sa.JSON,
                nullable=True,
                comment="业务类型多选: ['算力租赁','算力服务','卫星数据']",
            ),
        )


def downgrade() -> None:
    if _column_exists('customer', 'business_types'):
        op.drop_column('customer', 'business_types')
