# ADR-005: 模块间事件通信方案

## Status
Accepted

## Context
模块化单体架构中，跨模块通信有两种方式：
1. **同步调用**：A 模块直接调用 B 模块的 Service
2. **事件驱动**：A 模块发布事件，B 模块订阅响应

对于邮件发送场景：租赁记录状态变更（开通、临期、到期）不应让 rental 模块直接依赖 mail 模块的具体实现。需要解耦。

## Decision

采用 **Python blinker（Signal）做进程内事件总线**，但实际邮件发送已改为直接调用 + Celery 异步任务。

### 方案对比

| 对比项 | blinker Signal | Redis Pub/Sub | 直接调用 Service |
|--------|---------------|---------------|-----------------|
| 耦合度 | ✅ 低（发布者不依赖订阅者） | ✅ 低 | ❌ 高 |
| 可靠性 | ⚠️ 进程挂了丢失 | ✅ Redis 持久化 | ✅ 同步可靠 |
| 复杂度 | ✅ 极低（标准库级） | ⚠️ 需维护 Redis 连接 | ✅ 简单 |
| 适用场景 | 单体应用 | 分布式 | 单体 |
| 调试难度 | ✅ 容易 | ⚠️ 需额外工具 | ✅ 容易 |

### 当前实际使用情况

blinker 事件机制仍然存在，但**主要发送路径已改为直接调用**：

| 场景 | 发送机制 | 说明 |
|------|---------|------|
| 定时任务（临期/到期/回收） | 直接调用 `send_merged_email_by_contract()` | 同步发送，按合同合并 |
| 手动发送（开通/提醒/回收） | Celery 异步任务 `send_manual_email.delay()` | 按合同合并，异步执行 |
| blinker 订阅者 | 保留但降级为日志/审计用途 | 仅记录 EmailLog，不执行 SMTP 发送 |

### 事件定义

```python
# rental/events.py
import blinker

# 信号定义（保留用于审计/日志）
rental_provisioned = blinker.signal('rental.provisioned')
rental_expiring = blinker.signal('rental.expiring')
rental_expired = blinker.signal('rental.expired')
rental_reclaimed = blinker.signal('rental.reclaimed')
```

### 手动触发的流程（当前实际实现）

管理员在详情页点击「发送开通邮件」→ 调用 `POST /api/rentals/{id}/send-provision-email` → rental API 查出关联合同 → `send_manual_email.delay(contract_id, trigger_type)` → Celery Worker 执行 → `send_merged_email_by_contract()` → 渲染模板 → SMTP 发送 → 写 EmailLog

## Consequences

### 变得容易
- rental 模块不依赖 mail 模块，可独立测试
- 增加新的邮件类型只需新增事件 + 订阅者
- 调试时可在订阅者处断点

### 变得困难
- 信号发送是同步的，订阅者处理慢会阻塞发布者（对于邮件发送可接受，SMTP 发送本身也不快）
- 如果进程崩溃，事件丢失，不会重发（可通过 EmailLog 表 + 重发按钮弥补）

### 可逆性等级：高
- 可随时改为直接调用 Service（只需修改事件发送处）
- 如果未来需要异步/分布式，可升级为 Redis Pub/Sub 或 RabbitMQ，事件接口不变
