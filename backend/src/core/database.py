"""
数据库引擎与 Session 管理
"""
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, declarative_base

from src.core.config import settings

# 创建引擎（SQLite 不支持 pool_size/max_overflow/pool_pre_ping）
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {"echo": settings.DEBUG}
if not _is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基类
Base = declarative_base()


# UUID 列类型：MySQL 使用 CHAR(36)，SQLite 使用 String(36)
if _is_sqlite:
    def UUIDColumn(*args, **kwargs):
        return String(36, *args, **kwargs)
else:
    from sqlalchemy.dialects.mysql import CHAR as _MySQLChar

    def UUIDColumn(*args, **kwargs):
        return _MySQLChar(36, *args, **kwargs)


def get_db():
    """
    FastAPI 依赖注入：获取数据库会话
    用法：
        @app.get("/xxx")
        def handler(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
