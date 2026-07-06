# ADR-004: 定时任务方案

## Status
Accepted

## Context
平台需要三个定时任务（原计划两个，V2 通知流程将到期提醒与回收拆分为独立任务）：
1. **临期提醒**：每天 08:00 检查到期前 N 天的合同，发提醒邮件（N 可配置，默认 7 天和 3 天）
2. **到期提醒**：每天 08:00 检查当天到期的合同，发「今天到期，今晚回收」提醒
3. **到期回收**：每天 00:01 执行回收 + 发送回收通知邮件

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
# 临期提醒：每天 08:00 执行（扫描到期前 N 天的合同，N 从 system_config 读取）
@celery_app.task
def check_expiring_rentals():
    """
    按合同维度扫描：合同 end_date - today <= warning_days 且 end_date > today
    且合同 status in (active, expiring)
    按合同合并设备 → send_merged_email_by_contract
    合同状态更新为 expiring
    """

# 到期提醒：每天 08:00 执行
@celery_app.task
def check_expired_rentals():
    """
    按合同维度扫描：合同 end_date = today 且合同 status in (active, expiring)
    发 expiry_notice 邮件（「今天到期，今晚回收」）
    合同状态更新为 expired
    """

# 到期回收：每天 00:01 执行
@celery_app.task
def check_reclaim_expired():
    """
    按合同维度扫描：合同 end_date < today 且合同 status = expired
    执行回收 + 发 reclaim 邮件
    合同状态更新为 reclaimed + 快照设备 ID 到 history_rental_ids
    """
```

### 调度时间：从数据库动态读取

调度时间不在代码中硬编码，而是从 `system_config` 表读取，管理员可在前端 `/system/config` 页面动态调整：

```
system_config keys:
- check-expiring-rentals  → 默认 "08:00"
- check-expired-rentals   → 默认 "08:00"
- check-reclaim-expired   → 默认 "00:01"
- expiry_warning_days     → 默认 "7,3"（逗号分隔多天数）
```

### 手动触发支持

管理员可在前端手动触发以下操作（通过 Celery 异步任务 `send_manual_email`）：
- 发送开通邮件（设备详情页按钮，按合同合并发送）
- 发送临期提醒（按合同合并发送）
- 回收并发送通知（按合同合并发送）
- 对失败的邮件一键重发

手动触发通过调用 REST API，后端通过 Celery task 异步执行。

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
