# CronMail 审计修复清单

> 审计日期：2026-06-27 | 审计范围：全栈 | 状态：✅ 全部修复

---

## 🔴 致命

### F-1：定时任务竞态 — `check_expired_rentals` 和 `check_reclaim_expired` 同时 00:00

- **文件**：`backend/src/scheduler/celery_app.py` 第 31-38 行
- **修复**：将 `check_reclaim_expired` 的 crontab 从 `hour=0, minute=0` 改为 `hour=1, minute=0`
- **原因**：两者同时触发，若前者慢后者快可能通知未发就回收

### F-2：手动回收可跳过 `expired` 直接变 `reclaimed`

- **文件**：`backend/src/scheduler/tasks.py` `send_manual_email` 函数 reclaim 分支
- **文件**：`backend/src/rental/api.py` 的 reclaim 端点
- **修复**：在 reclaim 操作前检查 `contract.status == 'expired'`，否则拒绝并提示「仅已到期合同可回收」

---

## 🟠 高危

### H-1：删除合同后设备字段未清理

- **文件**：`backend/src/contract/services.py` `delete_contract` 函数（约第 97 行）
- **修复**：删除前遍历 `contract.rentals`，将每个设备的 `status` 置为 `'空闲中'`、`customer_id` 置 `None`

### H-2：前端设备状态枚举与后端不一致

- **文件**：`frontend/src/api/modules/rental.ts`（L18-L19）、`frontend/src/lib/rental.ts`
- **修复**：确认后端实际使用的状态值，统一前后端枚举

### H-3：合同列表缺少「已到期(expired)」筛选

- **文件**：`frontend/src/views/contracts/index.vue` 筛选下拉
- **修复**：添加 `{ label: '已到期', value: 'expired' }` 选项

### H-4：同事管理分页 total 计算错误

- **文件**：`frontend/src/views/system/colleagues.vue`（约第 46 行）
- **修复**：`total.value = res.total` 代替 `list.value.length`

---

## 🟡 中危

### M-1：临期天数配置重复导致重复发邮件

- **文件**：`backend/src/scheduler/tasks.py` `check_expiring_rentals`
- **修复**：解析 `expiry_warning_days` 配置后对 `days_list` 做 `list(set(...))` 去重

### M-2：`check_expired_rentals` 中 `db.rollback()` 无效

- **文件**：`backend/src/scheduler/tasks.py`
- **修复**：去掉无效的 `db.rollback()`，改为只打错误日志

### M-3：邮件成功但状态更新失败导致重复通知

- **文件**：`backend/src/scheduler/tasks.py` `check_expired_rentals`
- **修复**：将 `c.status = 'expired'` 和 `db.commit()` 移入 `send_merged_email_by_contract` 内部，确保邮件发送和状态变更原子化

### M-4：合同关联设备 TOCTOU 竞态

- **文件**：`backend/src/contract/services.py` `_link_rentals`
- **修复**：用 `try/except IntegrityError` 包裹插入操作，返回 409 而非 500

### M-5：SMTP/钉钉配置 404 误判

- **文件**：`frontend/src/views/system/smtp.vue`、`dingtalk.vue`
- **修复**：在 API 调用时加 `__silent: true`，然后检查返回值是否为 null（而非 catch 404）
