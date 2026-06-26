# ADR-004: 定时任务方案

## Status
Accepted

## Context
平台需要两个定时任务：
1. **临期提醒**：每天检查到期前 ≤3 天的租赁记录，发提醒邮件
2. **到期回收**：每天检查已到期的租赁记录，发回收邮件并更新状态

需要选择一个定时任务调度方案。

## Decision

采用 **Celery Beat + Redis Broker + Celery Worker**。

### 方案对比

| 对比项 | Celery Beat | APScheduler | 系统 crontab + 脚本 |
|--------|------------|-------------|---------------------|
| 与 FastAPI 集成 | ✅ celery 生态成熟 | ⚠️ 需自行管理进程 | ❌ 完全分离 |
| 任务管理 | ✅ Flower 监控面板 | ❌ 无内置面板 | ❌ 靠日志 |
| 失败重试 | ✅ 内置重试策略 | ⚠️ 需自行实现 | ❌ 需自行实现 |
| 额外依赖 | Redis | 无（可内存） | 无 |
| 生产成熟度 | ✅ 业界标准 | ⚠️ 一般 | ✅ 但维护成本高 |

### 定时任务定义

```python
# 临期提醒：每天 08:00 执行
@celery_app.task
def check_expiring_rentals():
    """
    查出 end_date - today <= 3 天且 end_date > today
    且 status in (PROVISIONED, EXPIRING)
    逐条发临期提醒邮件，状态更新为 EXPIRING
    """

# 到期回收：每天 02:00 执行
@celery_app.task
def check_expired_rentals():
    """
    查出 end_date < today 且 status in (EXPIRING, PROVISIONED)
    逐条发回收通知邮件，状态更新为 RECLAIMED
    """
```

### Celery Beat 调度配置

```python
beat_schedule = {
    'check-expiring-rentals': {
        'task': 'scheduler.tasks.check_expiring_rentals',
        'schedule': crontab(hour=8, minute=0),
    },
    'check-expired-rentals': {
        'task': 'scheduler.tasks.check_expired_rentals',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

### 手动触发支持

管理员可在前端手动触发以下操作（不走定时任务）：
- 发送开通邮件（租赁详情页按钮）
- 发送临期提醒（对单条记录手动发送）
- 标记已回收并发送通知
- 对失败的邮件一键重发

手动触发通过调用 REST API，由后端同步或异步（Celery task）执行。

## Consequences

### 变得容易
- 定时任务与业务代码在同一进程共享 Service 层
- Flower 面板可视化监控任务执行状态
- 失败自动重试，不需要手动处理

### 变得困难
- 部署需额外运行 Celery Worker 和 Celery Beat 两个进程
- Redis 是额外依赖（但已由用户提供）
- Celery 任务与 FastAPI 异步上下文隔离，任务内不能直接使用 FastAPI 的依赖注入

### 可逆性等级：中
- 可降级为 APScheduler（去掉 Redis 依赖），但失去任务监控和重试能力
- 调度时间配置在代码中，后续可改为数据库配置实现动态调整
