"""
Celery 应用配置
Beat 定时任务调度 — 调度时间从数据库 system_config 表读取
"""
import os
from celery import Celery
from celery.schedules import crontab

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "4"))

# 默认调度时间
_DEFAULT_SCHEDULES = {
    'check-expiring-rentals': (8, 0),   # 临期提醒 (expiry_warning)
    'check-expired-rentals': (8, 0),    # 到期提醒 (expiry_notice)
    'check-reclaim-expired': (0, 1),    # 回收执行 + 回收通知 (reclaim)
}


def _load_schedules():
    """从数据库加载调度时间配置，失败则使用默认值"""
    try:
        from src.system.models import SystemConfig
        from src.core.database import SessionLocal
        db = SessionLocal()
        try:
            schedules = {}
            for task_name, (dh, dm) in _DEFAULT_SCHEDULES.items():
                config = db.query(SystemConfig).filter(
                    SystemConfig.key == task_name
                ).first()
                if config and config.value:
                    parts = config.value.strip().split(':')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        h, m = int(parts[0]), int(parts[1])
                        if 0 <= h <= 23 and 0 <= m <= 59:
                            schedules[task_name] = (h, m)
                            continue
                schedules[task_name] = (dh, dm)
            return schedules
        finally:
            db.close()
    except Exception:
        return dict(_DEFAULT_SCHEDULES)


celery_app = Celery('cronmail', broker=CELERY_BROKER_URL)

celery_app.conf.update(
    timezone='Asia/Shanghai',
    worker_concurrency=CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


@celery_app.on_after_configure.connect
def setup_beat_schedule(sender, **kwargs):
    """在 Celery app 配置完成后、Beat 启动前读取调度时间"""
    schedules = _load_schedules()
    h1, m1 = schedules['check-expiring-rentals']
    h2, m2 = schedules['check-expired-rentals']
    h3, m3 = schedules['check-reclaim-expired']
    sender.conf.beat_schedule = {
        'check-expiring-rentals': {
            'task': 'scheduler.tasks.check_expiring_rentals',
            'schedule': crontab(hour=h1, minute=m1),
        },
        'check-expired-rentals': {
            'task': 'scheduler.tasks.check_expired_rentals',
            'schedule': crontab(hour=h2, minute=m2),
        },
        'check-reclaim-expired': {
            'task': 'scheduler.tasks.check_reclaim_expired',
            'schedule': crontab(hour=h3, minute=m3),
        },
    }


# 强制立即执行任务发现，并预加载模型确保 SQLAlchemy mapper 正确初始化
celery_app.autodiscover_tasks(['src.scheduler'], force=True)

from celery import signals as _celery_signals
@_celery_signals.worker_process_init.connect
def _preload_models(**kwargs):
    """Worker 子进程启动时预加载所有模型，防止 lazy import 导致的 mapper 初始化失败"""
    import src.customer.models  # noqa
    import src.rental.models  # noqa
    import src.contract.models  # noqa
    import src.template.models  # noqa
    import src.mail.models  # noqa
    import src.system.models  # noqa
    import src.scheduler.models  # noqa
