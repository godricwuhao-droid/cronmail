"""019: add project_type table

Revision ID: 019_add_project_type_table
Revises: 018_add_project_type
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa


revision = '019_add_project_type_table'
down_revision = '018_add_project_type'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_type',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer, default=0, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )
    op.create_unique_constraint('uq_project_type_name', 'project_type', ['name'])


def downgrade():
    op.drop_table('project_type')
