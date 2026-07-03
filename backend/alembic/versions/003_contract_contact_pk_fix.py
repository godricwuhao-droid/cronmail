"""修复 contract_contact 主键：将 recipient_type 加入复合主键

Revision ID: 003
Revises: 002
Create Date: 2025-06-29

问题：原主键 (contract_id, contact_id) 不支持同一联系人在同一合同下同时作为 to 和 cc。
修复后主键变为 (contract_id, contact_id, recipient_type)。
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除旧主键
    op.execute("ALTER TABLE contract_contact DROP PRIMARY KEY")
    # 2. 添加 recipient_type 到主键
    op.execute(
        "ALTER TABLE contract_contact ADD PRIMARY KEY (contract_id, contact_id, recipient_type)"
    )
    # 3. 重建唯一约束
    op.execute("ALTER TABLE contract_contact DROP INDEX IF EXISTS uq_contract_contact")
    op.execute(
        "ALTER TABLE contract_contact ADD UNIQUE KEY uq_contract_contact "
        "(contract_id, contact_id, recipient_type)"
    )


def downgrade() -> None:
    # 回退：恢复为 (contract_id, contact_id) 主键
    # 注意：如果已有同一 contact_id 多条不同 recipient_type 的记录，回退会失败
    op.execute("ALTER TABLE contract_contact DROP PRIMARY KEY")
    op.execute("ALTER TABLE contract_contact ADD PRIMARY KEY (contract_id, contact_id)")
    op.execute("ALTER TABLE contract_contact DROP INDEX IF EXISTS uq_contract_contact")
    op.execute(
        "ALTER TABLE contract_contact ADD UNIQUE KEY uq_contract_contact "
        "(contract_id, contact_id)"
    )
