# ADR-009: 手动邮件发送统一合并策略

## Status
Accepted

## Context

当前系统存在两条邮件发送路径：

| 路径 | 行为 | 合并？ |
|------|------|--------|
| 定时任务（Celery Beat） | 扫描 → 按 customer_id 分组 → 合并发送 | ✅ 一封邮件含多台 |
| 手动触发（API 按钮） | 取单条 rental → 发单封邮件 | ❌ 每台一封 |

问题：同一客户同时开通/到期的多台资源，管理员手动触发时会产生多封邮件轰炸。

## Decision

**所有发送路径（定时 + 手动）统一使用合并发送逻辑。**

具体规则：

1. **提取公共函数**：将 `scheduler/helpers.py` 中的 `_send_merged_email` 提升为 `mail/services.py` 中的公开函数 `send_merged_email(customer, records, trigger_type)`

2. **手动触发合并维度**：

   | 触发类型 | 合并 Key | 说明 |
   |---------|---------|------|
   | 开通邮件 (`provision`) | `customer_id` + `start_date` | 同一客户、同一天开通的全部记录 |
   | 临期提醒 (`expiry_warning`) | `customer_id`（窗口聚合） | 同一客户、未来 3 天内到期的全部记录（含已标记 expiring） |
   | 回收通知 (`reclaim`) | `customer_id` + `end_date` | 同一客户、同一天到期的全部记录 + 批量更新状态为 `reclaimed` |

3. **API 端点改造**：

   ```
   POST /api/rentals/{id}/send-provision-email
     → 查 {id} → 得 customer_id + start_date
     → 查同一客户、同一 start_date 的所有 provisioned 记录
     → send_merged_email(records, customer, 'provision')
     → 返回合并后的 email_log_ids

   POST /api/rentals/{id}/send-expiry-reminder
     → 查 {id} → 得 customer_id
     → 查同一客户、end_date 在未来 3 天内、状态为 provisioned/expiring 的全部记录
     → send_merged_email(records, customer, 'expiry_warning')

   POST /api/rentals/{id}/reclaim
     → 查 {id} → 得 customer_id + end_date
     → 查同一客户、同一 end_date 的 provisioned/expiring 全部记录
     → send_merged_email(records, customer, 'reclaim')
     → 批量 update status = 'reclaimed'
   ```

4. **事件机制保留但不负责发送**：blinker 事件仅用于日志/审计，实际邮件发送由 API 直接调用 `send_merged_email` 完成，避免双重发送。

## Consequences

### 变容易了
- 管理员一次点击即可覆盖客户所有同日资源
- 定时任务和手动触发共享同一套合并逻辑，不再有两套代码
- 客户体验提升：一天一封邮件而非 N 封

### 变难了
- 如果用户只想对其中一台发邮件（不合并），无法做到。如后续有需求，可加 `?merge=false` 参数
- `send_merged_email` 需要从 scheduler 模块提取到 mail 模块，涉及 import 路径变更

## Reversibility
高 —— 逻辑下移为公共服务，不改变数据结构，回退只需恢复 API 端的单条发送调用。
