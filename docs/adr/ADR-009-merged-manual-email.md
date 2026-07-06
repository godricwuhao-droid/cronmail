# ADR-009: 手动邮件发送统一合并策略（已演进为按合同合并）

## Status
Accepted

## Context

当前系统存在两条邮件发送路径：

| 路径 | 行为 | 合并？ |
|------|------|--------|
| 定时任务（Celery Beat） | 扫描合同 → 按合同合并设备 → 发送 | ✅ 一封邮件含合同下所有设备 |
| 手动触发（API 按钮） | 取单条 rental → 找关联合同 → 按合同合并发送 | ✅ 一封邮件含合同下所有设备 |

ADR-010（Contract 聚合根）引入后，合并维度从「按日期匹配」演进为「按合同关联」。同一客户不会因为多次点击而收到多封邮件——每次都按合同维度合并。

## Decision

**所有发送路径（定时 + 手动）统一使用按合同合并的发送逻辑。**

具体规则：

1. **核心发送函数**：`mail/services.py` 中的 `send_merged_email_by_contract(contract, trigger_type)` 是唯一发送入口，按合同下的全部关联设备合并为一封邮件。

2. **手动触发改为 Celery 异步任务**：

   | 触发类型 | API 端点 | 实际执行 |
   |---------|---------|---------|
   | 开通邮件 | `POST /api/rentals/{id}/send-provision-email` | 查设备→得关联合同→`send_manual_email.delay(contract_id, "provision")` → Worker 执行 `send_merged_email_by_contract` |
   | 临期提醒 | `POST /api/rentals/{id}/send-expiry-reminder` | 查设备→得关联合同→`send_manual_email.delay(contract_id, "expiry_warning")` |
   | 回收通知 | `POST /api/rentals/{id}/reclaim` | 查设备→得关联合同→`send_manual_email.delay(contract_id, "reclaim")` → 回收逻辑 + 状态更新在 Worker 中执行 |

3. **定时任务复用同一逻辑**：Celery Beat 定时任务直接同步调用 `send_merged_email_by_contract`，与手动触发的异步任务最终走同一套发送管道。

4. **事件机制降级**：blinker 事件（ADR-005）仅用于日志/审计，不再负责实际 SMTP 发送，避免双重发送。

## Consequences

### 变容易了
- 合并维度明确（一个合同 = 一封邮件），不会出现「同客户不同合同被错误合并」
- 定时任务和手动触发共享同一套 `send_merged_email_by_contract`，无重复逻辑
- 手动发送改为异步 Celery 任务，API 响应更快，失败自动重试

### 变难了
- 如果用户只想对合同下的某台设备发邮件（不合并），无法做到
- 手动发送从同步变为异步，前端需要轮询或在 EmailLog 中确认发送结果

## Reversibility
中 —— 按合同合并是 ADR-010 聚合根设计的自然结果。如要回退到「按日期匹配」，需同时回退 ADR-010 的 Contract 聚合根。
