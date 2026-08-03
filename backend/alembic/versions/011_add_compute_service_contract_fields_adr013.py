"""add_compute_service_contract_fields_adr013

Revision ID: 011
Revises: 010
Create Date: 2026-07-23

变更：
  - compute_service_contract 表新增 4 个字段 (ADR-013):
    project_name, contract_content, delivery_requirements, process_records
  - 所有字段 nullable=True，不破坏现有数据
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否已存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # ---- compute_service_contract 新增 4 个字段 ----

    if not _column_exists('compute_service_contract', 'project_name'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'project_name',
                sa.String(255),
                nullable=True,
                comment='所属项目',
            ),
        )

    if not _column_exists('compute_service_contract', 'contract_content'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'contract_content',
                sa.Text,
                nullable=True,
                comment='合同内容',
            ),
        )

    if not _column_exists('compute_service_contract', 'delivery_requirements'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'delivery_requirements',
                sa.Text,
                nullable=True,
                comment='合同交付要求',
            ),
        )

    if not _column_exists('compute_service_contract', 'process_records'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'process_records',
                sa.Text,
                nullable=True,
                comment='过程记录',
            ),
        )


def downgrade() -> None:
    for col in ['process_records', 'delivery_requirements', 'contract_content', 'project_name']:
        if _column_exists('compute_service_contract', col):
            op.drop_column('compute_service_contract', col)
