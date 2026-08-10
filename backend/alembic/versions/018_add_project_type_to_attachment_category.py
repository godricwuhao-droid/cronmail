"""018: add project_type to attachment_categories

Revision ID: 018_add_project_type
Revises: 017_add_contacts
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = '018_add_project_type'
down_revision = '017_add_contacts'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('attachment_category', sa.Column('project_type', sa.String(100), nullable=True, comment='项目类型，仅 contract_type=project 时使用，NULL 表示兜底'))


def downgrade():
    op.drop_column('attachment_category', 'project_type')
