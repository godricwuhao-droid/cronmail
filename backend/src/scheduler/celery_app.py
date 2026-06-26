"""
Celery 应用配置
Beat 定时任务调度
"""
import os

from celery import Celery
from celery.schedules import crontab

# 从环境变量读取 Broker URL，默认使用 Redis
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/0",
)

# Worker 并发数，可通过环境变量覆盖
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "4"))

celery_app = Celery('cronmail', broker=CELERY_BROKER_URL)

celery_app.conf.update(
    timezone='Asia/Shanghai',
    worker_concurrency=CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    beat_schedule={
        'check-expiring-rentals': {
            'task': 'scheduler.tasks.check_expiring_rentals',
            'schedule': crontab(hour=8, minute=0),
        },
        'check-expired-rentals': {
            'task': 'scheduler.tasks.check_expired_rentals',
            'schedule': crontab(hour=0, minute=0),
        },
        'check-reclaim-expired': {
            'task': 'scheduler.tasks.check_reclaim_expired',
            'schedule': crontab(hour=0, minute=0),
        },
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks(['src.scheduler'])
