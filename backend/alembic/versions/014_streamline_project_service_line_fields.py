"""streamline_project_service_line_fields

Revision ID: 014
Revises: 013
Create Date: 2026-07-29

变更：
  - project_service_line 删除 7 个硬编码规格字段（vcpu_count/memory_gb/storage_gb/gpu_count/gpu_model/gpu_memory_gb/gpu_tops）
  - 所有规格数据统一进 specification JSON
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    columns_to_drop = [
        'gpu_tops',
        'gpu_memory_gb',
        'gpu_model',
        'gpu_count',
        'storage_gb',
        'memory_gb',
        'vcpu_count',
    ]
    for col in columns_to_drop:
        if _column_exists('project_service_line', col):
            op.drop_column('project_service_line', col)


def downgrade() -> None:
    # 恢复 7 个字段（nullable=True，因为旧数据没有这些字段）
    columns_to_add = [
        ('vcpu_count', sa.Numeric(10, 2), 'vCPU核数'),
        ('memory_gb', sa.Numeric(10, 2), '内存GB'),
        ('storage_gb', sa.Numeric(10, 2), '存储GB'),
        ('gpu_count', sa.Integer(), '每台GPU卡数'),
        ('gpu_model', sa.String(100), 'GPU型号'),
        ('gpu_memory_gb', sa.Numeric(10, 2), '单卡显存GB'),
        ('gpu_tops', sa.Numeric(10, 2), '单卡算力TOPS'),
    ]
    for col_name, col_type, col_comment in columns_to_add:
        if not _column_exists('project_service_line', col_name):
            op.add_column('project_service_line', sa.Column(col_name, col_type, nullable=True, comment=col_comment))
