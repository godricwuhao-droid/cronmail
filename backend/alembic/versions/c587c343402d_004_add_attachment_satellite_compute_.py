"""004_add_attachment_satellite_compute_service

Revision ID: c587c343402d
Revises: 003
Create Date: 2026-07-03 17:18:53.889934

新增：
  - attachment_category: 附件分类表
  - attachment_item: 附件子项清单表
  - attachment: 附件文件表
  - attachment_status: 附件完成确认状态表
  - satellite_data_contract: 卫星数据合同表
  - compute_service_contract: 算力服务合同表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c587c343402d'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # attachment_category
    # ============================================================
    op.create_table(
        'attachment_category',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_type', sa.String(30), nullable=False, comment='合同类型: compute_leasing / satellite_data / compute_service'),
        sa.Column('name', sa.String(100), nullable=False, comment='分类名称'),
        sa.Column('code', sa.String(50), nullable=False, comment='分类编码'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ============================================================
    # attachment_item
    # ============================================================
    op.create_table(
        'attachment_item',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('category_id', sa.String(36), nullable=False, comment='所属分类ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='子项名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='子项说明'),
        sa.Column('expected_type', sa.String(20), nullable=True, comment='期望文件类型: pdf / excel / image / any'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['category_id'], ['attachment_category.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_attachment_item_category_id'), 'attachment_item', ['category_id'], unique=False)

    # ============================================================
    # attachment
    # ============================================================
    op.create_table(
        'attachment',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_type', sa.String(30), nullable=False, comment='关联哪种合同表'),
        sa.Column('contract_id', sa.String(36), nullable=False, comment='关联合同的 ID'),
        sa.Column('item_id', sa.String(36), nullable=False, comment='所属子项ID'),
        sa.Column('filename', sa.String(255), nullable=False, comment='原始文件名'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='相对路径'),
        sa.Column('file_size', sa.Integer(), nullable=True, comment='文件大小(字节)'),
        sa.Column('mime_type', sa.String(100), nullable=True, comment='MIME 类型'),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True, comment='上传时间'),
        sa.ForeignKeyConstraint(['item_id'], ['attachment_item.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_attachment_contract_id'), 'attachment', ['contract_id'], unique=False)
    op.create_index(op.f('ix_attachment_item_id'), 'attachment', ['item_id'], unique=False)

    # ============================================================
    # attachment_status
    # ============================================================
    op.create_table(
        'attachment_status',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_type', sa.String(30), nullable=False, comment='合同类型'),
        sa.Column('contract_id', sa.String(36), nullable=False, comment='合同 ID'),
        sa.Column('item_id', sa.String(36), nullable=False, comment='子项ID'),
        sa.Column('file_count', sa.Integer(), nullable=True, comment='文件数量'),
        sa.Column('confirmed', sa.Boolean(), nullable=True, comment='是否已确认完成'),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True, comment='确认时间'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['item_id'], ['attachment_item.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_type', 'contract_id', 'item_id', name='uq_attachment_status'),
    )
    op.create_index(op.f('ix_attachment_status_item_id'), 'attachment_status', ['item_id'], unique=False)

    # ============================================================
    # satellite_data_contract
    # ============================================================
    op.create_table(
        'satellite_data_contract',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False, comment='客户ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='合同名称'),
        sa.Column('contract_no', sa.String(100), nullable=True, comment='合同编号'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_satellite_data_contract_customer_id'), 'satellite_data_contract', ['customer_id'], unique=False)

    # ============================================================
    # compute_service_contract
    # ============================================================
    op.create_table(
        'compute_service_contract',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False, comment='客户ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='合同名称'),
        sa.Column('contract_no', sa.String(100), nullable=True, comment='合同编号'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_compute_service_contract_customer_id'), 'compute_service_contract', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_table('compute_service_contract')
    op.drop_table('satellite_data_contract')
    op.drop_table('attachment_status')
    op.drop_table('attachment')
    op.drop_table('attachment_item')
    op.drop_table('attachment_category')
