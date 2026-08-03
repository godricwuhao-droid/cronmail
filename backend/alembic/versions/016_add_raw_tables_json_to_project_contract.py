"""add_raw_tables_json_to_project_contract

Revision ID: 016
Revises: 015
Create Date: 2026-07-30

变更：
  - project_contract 新增 raw_tables_json 字段（原始表格JSON，AI解析结果）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('project_contract', 'raw_tables_json'):
        op.add_column('project_contract',
            sa.Column('raw_tables_json', sa.Text, nullable=True,
                      comment='原始表格JSON，AI解析结果'))


def downgrade() -> None:
    if _column_exists('project_contract', 'raw_tables_json'):
        op.drop_column('project_contract', 'raw_tables_json')
