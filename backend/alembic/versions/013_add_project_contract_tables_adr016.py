"""add_project_contract_tables_adr016

Revision ID: 013
Revises: 012
Create Date: 2026-07-28

变更：
  - 新增 project_contract 表（项目管理合同）
  - 新增 project_service_line 表（项目管理合同 - 服务内容行）
  - 所有字段含幂等保护，已存在则跳过
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """检查表是否已存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # ---- project_contract ----
    if not _table_exists('project_contract'):
        op.create_table(
            'project_contract',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('company_code', sa.String(20), nullable=False, comment="公司: fengyun/tianshu/qianxing"),
            sa.Column('name', sa.String(255), nullable=False, comment="合同名称"),
            sa.Column('contract_no', sa.String(100), nullable=True, comment="合同编号"),
            sa.Column('contract_type', sa.String(30), nullable=False, server_default='sales', comment="sales/procurement"),
            sa.Column('party_a_name', sa.String(255), nullable=True, comment="甲方"),
            sa.Column('party_b_name', sa.String(255), nullable=True, comment="乙方"),
            sa.Column('amount', sa.Numeric(12, 2), nullable=True, comment="合同金额"),
            sa.Column('start_date', sa.Date, nullable=True, comment="开始日期"),
            sa.Column('end_date', sa.Date, nullable=True, comment="结束日期"),
            sa.Column('related_contract_id', sa.String(36), nullable=True, comment="背靠背关联"),
            sa.Column('project_name', sa.String(255), nullable=True, comment="所属项目"),
            sa.Column('contract_content', sa.Text, nullable=True, comment="合同内容"),
            sa.Column('delivery_requirements', sa.Text, nullable=True, comment="交付要求"),
            sa.Column('process_records', sa.Text, nullable=True, comment="过程记录"),
            sa.Column('remark', sa.Text, nullable=True, comment="备注"),
            sa.Column('sort_order', sa.Integer, nullable=False, server_default='0', comment="排序序号"),
            sa.Column('created_at', sa.DateTime, nullable=True),
            sa.Column('updated_at', sa.DateTime, nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_project_contract_company_code'), 'project_contract', ['company_code'], unique=False)
        op.create_foreign_key(
            'fk_project_contract_related',
            'project_contract', 'project_contract',
            ['related_contract_id'], ['id'],
        )

    # ---- project_service_line ----
    if not _table_exists('project_service_line'):
        op.create_table(
            'project_service_line',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('contract_id', sa.String(36), nullable=False),
            sa.Column('category', sa.String(50), nullable=False),
            sa.Column('item_name', sa.String(100), nullable=False),
            sa.Column('specification', sa.JSON, nullable=True),
            sa.Column('vcpu_count', sa.Numeric(10, 2), nullable=True),
            sa.Column('memory_gb', sa.Numeric(10, 2), nullable=True),
            sa.Column('storage_gb', sa.Numeric(10, 2), nullable=True),
            sa.Column('gpu_count', sa.Integer, nullable=True),
            sa.Column('gpu_model', sa.String(100), nullable=True),
            sa.Column('gpu_memory_gb', sa.Numeric(10, 2), nullable=True),
            sa.Column('gpu_tops', sa.Numeric(10, 2), nullable=True),
            sa.Column('unit', sa.String(20), nullable=False),
            sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
            sa.Column('period_months', sa.Integer, nullable=False, server_default='1'),
            sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
            sa.Column('total_price', sa.Numeric(12, 2), nullable=False),
            sa.Column('sort_order', sa.Integer, server_default='0'),
            sa.Column('service_description', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_project_service_line_contract_id'), 'project_service_line', ['contract_id'], unique=False)
        op.create_foreign_key(
            'fk_project_service_line_contract',
            'project_service_line', 'project_contract',
            ['contract_id'], ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    if _table_exists('project_service_line'):
        op.drop_table('project_service_line')
    if _table_exists('project_contract'):
        op.drop_table('project_contract')
