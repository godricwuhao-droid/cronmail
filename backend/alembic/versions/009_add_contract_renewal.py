"""add renewed_from_id to contract for renewal chain

Revision ID: 009
Revises: 008
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contract', sa.Column('renewed_from_id', sa.String(36), nullable=True, comment='续期来源合同ID'))
    op.create_index('ix_contract_renewed_from_id', 'contract', ['renewed_from_id'])
    op.create_foreign_key('fk_contract_renewed_from', 'contract', 'contract', ['renewed_from_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_contract_renewed_from', 'contract', type_='foreignkey')
    op.drop_index('ix_contract_renewed_from_id', 'contract')
    op.drop_column('contract', 'renewed_from_id')
