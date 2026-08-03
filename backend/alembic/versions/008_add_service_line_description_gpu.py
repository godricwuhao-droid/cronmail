"""add service_description and gpu fields to contract_service_line

Revision ID: 008
Revises: 007
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contract_service_line', sa.Column('service_description', sa.Text(), nullable=True, comment='服务描述长文本'))
    op.add_column('contract_service_line', sa.Column('gpu_count', sa.Integer(), nullable=True, comment='每台GPU卡数'))
    op.add_column('contract_service_line', sa.Column('gpu_model', sa.String(100), nullable=True, comment='GPU型号'))
    op.add_column('contract_service_line', sa.Column('gpu_memory_gb', sa.Numeric(10, 2), nullable=True, comment='单卡显存GB'))
    op.add_column('contract_service_line', sa.Column('gpu_tops', sa.Numeric(10, 2), nullable=True, comment='单卡算力TOPS'))


def downgrade():
    op.drop_column('contract_service_line', 'gpu_tops')
    op.drop_column('contract_service_line', 'gpu_memory_gb')
    op.drop_column('contract_service_line', 'gpu_model')
    op.drop_column('contract_service_line', 'gpu_count')
    op.drop_column('contract_service_line', 'service_description')
