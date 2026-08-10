"""
CronMail FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import engine, Base, SessionLocal


# ============================================================
# 导入所有模型，确保 Base.metadata 包含全部表定义
# （必须在 create_all 之前导入）
# ============================================================
import src.customer.models        # noqa: E402, F401
import src.rental.models          # noqa: E402, F401
import src.contract.models        # noqa: E402, F401
import src.template.models        # noqa: E402, F401
import src.mail.models            # noqa: E402, F401
import src.system.models           # noqa: E402, F401
import src.scheduler.models       # noqa: E402, F401
import src.attachment.models      # noqa: E402, F401
import src.satellite.models       # noqa: E402, F401
import src.compute_service.models # noqa: E402, F401
import src.project.models       # noqa: E402, F401


# ============================================================
# 生命周期管理
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时自动建表，关闭时释放引擎"""
    try:
        Base.metadata.create_all(bind=engine)
        print(f"[CronMail] 数据库表创建/检查完成")
    except Exception as e:
        print(f"[CronMail] 警告: 数据库连接失败，跳过自动建表: {e}")

    # 初始化默认系统配置
    try:
        db = SessionLocal()
        from src.system.models import SystemConfig
        if not db.query(SystemConfig).filter(SystemConfig.key == 'expiry_warning_days').first():
            db.add(SystemConfig(
                key='expiry_warning_days',
                value='7,3',
                description='临期提醒天数（逗号分隔）',
            ))
            db.commit()
            print("[CronMail] 已初始化默认系统配置: expiry_warning_days=7,3")
        if not db.query(SystemConfig).filter(SystemConfig.key == 'reclaim_time').first():
            db.add(SystemConfig(
                key='reclaim_time',
                value='22:00',
                description='每日回收执行时间（HH:MM）',
            ))
            db.commit()
            print("[CronMail] 已初始化默认系统配置: reclaim_time=22:00")
        # 初始化默认调度时间
        # check-expiring-rentals: 临期提醒 (expiry_warning)
        # check-expired-rentals: 到期提醒 (expiry_notice)
        # check-reclaim-expired: 回收执行 + 回收通知 (reclaim)
        _default_schedules = {
            'check-expiring-rentals': '08:00',
            'check-expired-rentals': '08:00',
            'check-reclaim-expired': '00:01',
        }
        for key, val in _default_schedules.items():
            existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if not existing:
                db.add(SystemConfig(key=key, value=val, description=f'通知调度时间 - {key}'))
        db.commit()
        print("[CronMail] 已初始化默认调度时间配置")
        db.close()
    except Exception as e:
        print(f"[CronMail] 初始化默认配置跳过: {e}")

    # 初始化默认附件分类
    try:
        db = SessionLocal()
        from src.attachment.services import init_default_categories
        init_default_categories(db)
        db.close()
        print("[CronMail] 已初始化默认附件分类")
    except Exception as e:
        print(f"[CronMail] 初始化默认附件分类跳过: {e}")

    print(f"[CronMail] 应用启动完成，环境: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    yield
    # 关闭时释放资源
    engine.dispose()
    print("[CronMail] 应用已关闭")


# ============================================================
# 创建应用实例
# ============================================================
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS 中间件（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 注册事件订阅者（触发 blinker 信号连接）
# ============================================================
import src.mail.subscribers  # noqa: E402, F401 - 触发 blinker 连接

# ============================================================
# 注册各模块路由
# ============================================================
from src.customer.api import customer_router, contact_router  # noqa: E402
from src.system.api import system_router  # noqa: E402
from src.rental.api import rental_router  # noqa: E402
from src.template.api import template_router  # noqa: E402
from src.mail.api import log_router  # noqa: E402
from src.contract.api import contract_router  # noqa: E402
from src.satellite.api import satellite_router  # noqa: E402
from src.compute_service.api import compute_service_router  # noqa: E402
from src.attachment.api import attachment_router, system_attachment_category_router  # noqa: E402
from src.contract_parser.api import parse_router  # noqa: E402
from src.project.api import project_router, project_type_router  # noqa: E402

app.include_router(customer_router)
app.include_router(contact_router)
app.include_router(system_router)
app.include_router(rental_router)
app.include_router(template_router)
app.include_router(log_router)
app.include_router(contract_router)
app.include_router(satellite_router)
app.include_router(compute_service_router)
app.include_router(attachment_router)
app.include_router(system_attachment_category_router)
app.include_router(parse_router)
app.include_router(project_router)
app.include_router(project_type_router)


# ============================================================
# 健康检查端点
# ============================================================
@app.get("/api/health", tags=["System"])
def health_check():
    """健康检查"""
    return {"status": "ok"}


# ============================================================
# 直接运行入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
