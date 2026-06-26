"""设备状态迁移为裸金属语义

Revision ID: 001
Revises:
Create Date: 2025-01-16
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 rental_record 状态值迁移为中文裸金属语义"""
    op.execute("UPDATE rental_record SET status = '运行中' WHERE status = 'provisioned'")
    op.execute("UPDATE rental_record SET status = '运行中' WHERE status = 'expiring'")
    op.execute("UPDATE rental_record SET status = '运行中' WHERE status = 'expired'")
    op.execute("UPDATE rental_record SET status = '已下架' WHERE status = 'reclaimed'")


def downgrade() -> None:
    """回退：将中文状态恢复为英文"""
    op.execute("UPDATE rental_record SET status = 'provisioned' WHERE status = '运行中'")
    op.execute("UPDATE rental_record SET status = 'provisioned' WHERE status = '维护中'")
    op.execute("UPDATE rental_record SET status = 'reclaimed' WHERE status = '已下架'")
    op.execute("UPDATE rental_record SET status = 'provisioned' WHERE status = '故障'")
