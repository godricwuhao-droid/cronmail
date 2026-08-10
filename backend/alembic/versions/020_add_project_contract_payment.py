"""020: add project_contract_payment table

Revision ID: 020_add_project_contract_payment
Revises: 019_add_project_type_table
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa


revision = '020_add_project_contract_payment'
down_revision = '019_add_project_type_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_contract_payment',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('contract_id', sa.String(36), nullable=False, comment='关联合同ID'),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False, comment='本次回款金额'),
        sa.Column('payment_date', sa.Date, nullable=True, comment='回款日期'),
        sa.Column('receipt_file_id', sa.String(36), nullable=True, comment='回执单附件ID（attachment表）'),
        sa.Column('invoice_file_id', sa.String(36), nullable=True, comment='开票附件ID（attachment表）'),
        sa.Column('remark', sa.Text, nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, comment='更新时间'),
    )
    op.create_index('ix_project_contract_payment_contract_id', 'project_contract_payment', ['contract_id'])
    op.create_foreign_key(
        'fk_project_contract_payment_contract_id',
        'project_contract_payment',
        'project_contract',
        ['contract_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade():
    op.drop_table('project_contract_payment')
