"""
Alembic 环境配置
"""
import os
import sys
from logging.config import fileConfig

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import engine_from_config, pool
from alembic import context

# 导入所有模型，确保 Base.metadata 包含所有表
from src.core.database import Base
import src.customer.models    # noqa: E402, F401
import src.rental.models      # noqa: E402, F401
import src.template.models    # noqa: E402, F401
import src.mail.models        # noqa: E402, F401
import src.system.models       # noqa: E402, F401
import src.scheduler.models   # noqa: E402, F401

# Alembic Config 对象
config = context.config

# 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 从环境变量覆盖 sqlalchemy.url
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# 目标元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式迁移（生成 SQL 脚本）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式迁移（直接连接数据库执行）"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
