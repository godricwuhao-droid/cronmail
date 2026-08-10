"""017: add responsible_person, business_person, party_a_contact, party_b_contact to project_contract

Revision ID: 017_add_contacts
Revises: 016_add_raw_tables_json_to_project_contract
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = '017_add_contacts'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('project_contract', sa.Column('responsible_person', sa.String(100), nullable=True, comment='负责人，手动填写'))
    op.add_column('project_contract', sa.Column('business_person', sa.String(100), nullable=True, comment='商务，手动填写'))
    op.add_column('project_contract', sa.Column('party_a_contact', sa.String(255), nullable=True, comment='甲方委派人及联系方式，Agent提取'))
    op.add_column('project_contract', sa.Column('party_b_contact', sa.String(255), nullable=True, comment='乙方委派人及联系方式，Agent提取'))


def downgrade():
    op.drop_column('project_contract', 'party_b_contact')
    op.drop_column('project_contract', 'party_a_contact')
    op.drop_column('project_contract', 'business_person')
    op.drop_column('project_contract', 'responsible_person')
