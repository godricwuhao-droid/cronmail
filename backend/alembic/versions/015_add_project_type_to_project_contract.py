"""add_project_type_to_project_contract

Revision ID: 015
Revises: 014
Create Date: 2026-07-30

变更：
  - project_contract 新增 project_type 字段（项目类型，用户手动填写）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('project_contract', 'project_type'):
        op.add_column('project_contract',
            sa.Column('project_type', sa.String(100), nullable=True,
                      comment='项目类型，如算力服务合同，用户手动填写'))


def downgrade() -> None:
    if _column_exists('project_contract', 'project_type'):
        op.drop_column('project_contract', 'project_type')
