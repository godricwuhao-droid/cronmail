"""006_add_compute_service_contract_fields

Revision ID: 006
Revises: 005
Create Date: 2026-07-18

变更：
  - compute_service_contract 表新增字段：
    contract_type, party_a_name, party_b_name, amount,
    start_date, end_date, related_contract_id
  - 新增 contract_service_line 表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_uuid_type():
    """根据数据库类型返回 UUID 列类型"""
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        from sqlalchemy.dialects.mysql import CHAR
        return CHAR(36)
    else:
        return sa.String(36)


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否已存在（幂等保护）"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    UUID = _get_uuid_type()

    # ---- compute_service_contract 新增字段 ----
    if not _column_exists('compute_service_contract', 'contract_type'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'contract_type',
                sa.String(10),
                nullable=False,
                server_default='sales',
                comment='合同类型: sales(销售) | procurement(采购)',
            ),
        )

    if not _column_exists('compute_service_contract', 'party_a_name'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'party_a_name',
                sa.String(255),
                nullable=True,
                comment='甲方名称',
            ),
        )

    if not _column_exists('compute_service_contract', 'party_b_name'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'party_b_name',
                sa.String(255),
                nullable=True,
                comment='乙方名称',
            ),
        )

    if not _column_exists('compute_service_contract', 'amount'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'amount',
                sa.Numeric(12, 2),
                nullable=True,
                comment='合同总金额',
            ),
        )

    if not _column_exists('compute_service_contract', 'start_date'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'start_date',
                sa.Date(),
                nullable=True,
                comment='合同开始日期',
            ),
        )

    if not _column_exists('compute_service_contract', 'end_date'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'end_date',
                sa.Date(),
                nullable=True,
                comment='合同到期日期',
            ),
        )

    if not _column_exists('compute_service_contract', 'related_contract_id'):
        op.add_column(
            'compute_service_contract',
            sa.Column(
                'related_contract_id',
                UUID,
                nullable=True,
                comment='背靠背关联合同ID',
            ),
        )
        # 添加自引用外键
        op.create_foreign_key(
            'fk_compute_service_contract_related',
            'compute_service_contract',
            'compute_service_contract',
            ['related_contract_id'],
            ['id'],
        )

    # ---- contract_service_line 新表 ----
    inspector = Inspector.from_engine(op.get_bind())
    existing_tables = inspector.get_table_names()
    if 'contract_service_line' not in existing_tables:
        op.create_table(
            'contract_service_line',
            sa.Column('id', UUID, primary_key=True),
            sa.Column(
                'contract_id',
                UUID,
                sa.ForeignKey('compute_service_contract.id', ondelete='CASCADE'),
                nullable=False,
                index=True,
                comment='合同ID',
            ),
            sa.Column('category', sa.String(50), nullable=False, comment='服务大类'),
            sa.Column('item_name', sa.String(100), nullable=False, comment='服务项'),
            sa.Column('specification', sa.JSON, nullable=True, comment='异构规格，仅展示'),
            sa.Column('vcpu_count', sa.Numeric(10, 2), nullable=True, comment='vCPU核数'),
            sa.Column('memory_gb', sa.Numeric(10, 2), nullable=True, comment='内存GB'),
            sa.Column('storage_gb', sa.Numeric(10, 2), nullable=True, comment='存储GB'),
            sa.Column('unit', sa.String(20), nullable=False, comment='单位'),
            sa.Column('quantity', sa.Numeric(12, 2), nullable=False, comment='数量'),
            sa.Column('period_months', sa.Integer, nullable=False, server_default='1', comment='周期月数'),
            sa.Column('unit_price', sa.Numeric(12, 2), nullable=False, comment='单价'),
            sa.Column('total_price', sa.Numeric(12, 2), nullable=False, comment='总价'),
            sa.Column('sort_order', sa.Integer, server_default='0', comment='排序'),
            sa.Column('created_at', sa.DateTime, comment='创建时间'),
        )


def downgrade() -> None:
    # 删除 contract_service_line 表
    op.drop_table('contract_service_line')

    # 删除 compute_service_contract 新增字段
    if _column_exists('compute_service_contract', 'related_contract_id'):
        op.drop_constraint(
            'fk_compute_service_contract_related',
            'compute_service_contract',
            type_='foreignkey',
        )
        op.drop_column('compute_service_contract', 'related_contract_id')

    for col in ['end_date', 'start_date', 'amount', 'party_b_name', 'party_a_name', 'contract_type']:
        if _column_exists('compute_service_contract', col):
            op.drop_column('compute_service_contract', col)
