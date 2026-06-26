# ADR-005: 模块间事件通信方案

## Status
Accepted

## Context
模块化单体架构中，跨模块通信有两种方式：
1. **同步调用**：A 模块直接调用 B 模块的 Service
2. **事件驱动**：A 模块发布事件，B 模块订阅响应

对于邮件发送场景：租赁记录状态变更（开通、临期、到期）不应让 rental 模块直接依赖 mail 模块的具体实现。需要解耦。

## Decision

采用 **Python blinker（Signal）做进程内事件总线**。

### 方案对比

| 对比项 | blinker Signal | Redis Pub/Sub | 直接调用 Service |
|--------|---------------|---------------|-----------------|
| 耦合度 | ✅ 低（发布者不依赖订阅者） | ✅ 低 | ❌ 高 |
| 可靠性 | ⚠️ 进程挂了丢失 | ✅ Redis 持久化 | ✅ 同步可靠 |
| 复杂度 | ✅ 极低（标准库级） | ⚠️ 需维护 Redis 连接 | ✅ 简单 |
| 适用场景 | 单体应用 | 分布式 | 单体 |
| 调试难度 | ✅ 容易 | ⚠️ 需额外工具 | ✅ 容易 |

### 事件定义

```python
# rental/events.py
import blinker

# 信号定义
rental_provisioned = blinker.signal('rental.provisioned')
rental_expiring = blinker.signal('rental.expiring')
rental_expired = blinker.signal('rental.expired')
rental_reclaimed = blinker.signal('rental.reclaimed')
```

```python
# mail/subscribers.py
from rental.events import rental_provisioned, rental_expiring, rental_expired

@rental_provisioned.connect
def on_rental_provisioned(sender, rental_record, template):
    """发送开通邮件"""
    ...

@rental_expiring.connect
def on_rental_expiring(sender, rental_record, template):
    """发送临期提醒"""
    ...

@rental_expired.connect
def on_rental_expired(sender, rental_record, template):
    """发送回收通知"""
    ...
```

```python
# 发布事件（在 rental/services.py 中）
from rental.events import rental_provisioned

def send_provision_email(rental_record):
    template = get_template('provision')
    rental_provisioned.send(rental_record, template=template)
```

### 手动触发的流程

管理员在详情页点击「发送开通邮件」→ 调用 `POST /api/rentals/{id}/send-provision-email` → rental Service 发布 `rental_provisioned` 事件 → mail 模块监听到 → 渲染模板 → SMTP 发送 → 写 EmailLog

**区别于自动发送**：创建租赁记录时不自动发布事件，仅保存数据。

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
