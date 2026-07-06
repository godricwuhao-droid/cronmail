# CronMail 后端变更日志

## 2026-07-17 (部署) — 后端镜像重新构建部署 (第四次)

### 部署
- **后端镜像构建 + K8s 滚动更新**
  - 影响文件：`Dockerfile.backend`
  - 变更内容：
    1. Docker 构建 `harbor.xhwltech.com/xhcloud/cronmail-backend:latest`（镜像 ID: `ff028ddb99fc`）
    2. 推送镜像到 Harbor（digest: `sha256:3a08533606f87ac19b946abe1fa1ca009b736dea5330f01a66a4bdda1ff2d582`）
    3. 滚动重启 `cronmail-backend-api` Deployment（`kubectl rollout restart`）
    4. 部署成功，`cronmail-backend-api` successfully rolled out
  - 构建代理：`http://192.168.180.251:7890`
  - 关联任务：后端部署

---

## 2026-07-17 (修复) — 附件分类管理页软删除子项仍显示

### 修复
- **`GET /api/system/attachment-categories` 软删除子项仍显示**
  - 影响文件：`backend/src/attachment/services.py`
  - 根因：`list_categories` 函数未过滤 `is_active`，直接通过 SQLAlchemy relationship 加载所有子项（含软删除）
  - 修复方式：
    1. 查询分类时增加 `AttachmentCategory.is_active == True` 过滤软删除的分类
    2. 对每个分类的 `items` 列表做 `is_active` 过滤，排除已软删除的子项
  - 关联任务：附件分类管理页软删除子项仍显示
  - 备注：附件管理页面（`get_attachment_list` / `get_summary`）原本已正确过滤 `is_active`，不受影响

---

## 2026-07-17 (修改) — Dashboard 待处理提醒加入已到期合同

### 修改
- **`get_expiring_contracts_with_rentals` 纳入已到期合同**
  - 影响文件：`backend/src/contract/dashboard.py`
  - 变更内容：
    1. 函数从「仅返回临期合同」改为「返回已到期 + 临期合同」
    2. 新增已到期查询：`Contract.status == 'expired'`，按 `end_date` 升序
    3. 合并逻辑：已到期排在临期前面（更紧急），通过 `seen` set 去重防止同一合同被两次命中
    4. 总返回条数不超过 `limit` 参数（默认 10）
  - 关联任务：Dashboard 待处理提醒加入已到期合同
  - 备注：前端无需修改 —— `contractStatusTagType` 和 `contractStatusLabel` 已有 `expired` 状态支持

---

## 2026-07-17 (修改) — 仪表盘统计增加「已到期」合同数

### 修改
- **`get_dashboard_stats` 新增 `expired` 字段**
  - 影响文件：`backend/src/contract/dashboard.py`
  - 变更内容：
    1. 新增 `expired = db.query(Contract).filter(Contract.status == 'expired').count()` 查询已到期合同数
    2. 返回值新增 `expired` 字段：`{"total_contracts": ..., "expiring": ..., "expired": ..., "reclaimed": ...}`
  - 关联任务：仪表盘已到期统计

---

## 2025-07-17 (修复) — 中文文件名下载 UnicodeEncodeError

### 修复
- **`GET /api/attachments/{id}/download` 中文文件名下载 500 错误**
  - 影响文件：`backend/src/attachment/api.py`
  - 根因：`Content-Disposition` header 直接拼接中文文件名（如 `【晨涧-盖亚】算力服务合同.pdf`），Starlette/Uvicorn 底层对 HTTP header 做 latin-1 编码时报 `UnicodeEncodeError: 'latin-1' codec can't encode characters`
  - 修复方式：
    1. 新增 `import urllib.parse`
    2. `download_attachment` 函数中，使用 `urllib.parse.quote(filename, safe='')` 对文件名做 URL 编码（RFC 5987）
    3. 同时提供 `filename`（ASCII fallback，中文 strip 后剩余部分或 `download`）和 `filename*=UTF-8''...`（RFC 5987 编码），兼容新旧浏览器
  - 关联任务：中文文件名下载修复

---

## 2025-07-17 (修复) — 附件上传 413 + FormData 字段名匹配

### 修复
- **nginx 未设置 client_max_body_size 导致附件上传 413**
  - 影响文件：`frontend/nginx.conf`
  - 变更内容：
    1. `http` 块全局添加 `client_max_body_size 200m;`（第 15 行）
    2. `/api/` location 块内添加 `client_max_body_size 200m;`（第 32 行）
  - 根因：nginx 默认 `client_max_body_size` 仅 1MB，上传大文件直接返回 413 Request Entity Too Large
  - 关联任务：附件上传 413 修复

- **前端 FormData 字段名 `file` 与后端 `files` 不匹配**
  - 影响文件：`frontend/src/views/attachments/AttachmentsPage.vue`
  - 变更内容：`formData.append('file', file)` → `formData.append('files', file)`
  - 根因：前端传 `file`（单数），后端 `POST /api/attachments/upload` 期望 `files`（复数 `list[UploadFile]`），字段名不匹配导致后端收不到文件
  - 关联任务：附件上传 413 修复

---

## 2026-07-03 (新增) — 多类型合同 + 附件管理

### 新增
- **附件管理模块 (`backend/src/attachment/`)**
  - 影响文件：`backend/src/attachment/models.py`, `schemas.py`, `services.py`, `api.py`
  - 变更内容：
    1. `AttachmentCategory` — 附件分类表，支持按合同类型（compute_leasing/satellite_data/compute_service）区分
    2. `AttachmentItem` — 分类下的子项清单表（如「合同扫描件」「验收单扫描件」等）
    3. `Attachment` — 实际文件表，多态关联三张合同表（contract_type + contract_id）
    4. `AttachmentStatus` — 子项完成确认状态表，含 UniqueConstraint(contract_type, contract_id, item_id)
  - API 路由：
    - `GET /api/attachments?contract_type=&contract_id=` — 按合同获取附件列表（分类+子项结构）
    - `POST /api/attachments/upload` — 多文件上传（multipart/form-data），存储至 `/app/uploads/{contract_type}/{contract_id}/{item_id}/{uuid}.ext`
    - `GET /api/attachments/{id}/download` — 文件下载（FileResponse）
    - `DELETE /api/attachments/{id}` — 删除文件（磁盘 + DB）
    - `GET /api/attachments/status/summary?contract_type=&contract_id=` — 完成状态汇总
    - `POST /api/attachments/status/{item_id}/confirm` — 确认完成
    - `POST /api/attachments/status/{item_id}/unconfirm` — 取消确认
  - 附件分类管理路由（挂载在 `/api/system/attachment-categories`）：
    - `GET /api/system/attachment-categories?contract_type=` — 列表（含子项）
    - `POST /api/system/attachment-categories` — 创建分类
    - `PUT /api/system/attachment-categories/{id}` — 更新
    - `DELETE /api/system/attachment-categories/{id}` — 软删除
    - `PUT /api/system/attachment-categories/{id}/reorder` — 排序
    - `POST /api/system/attachment-categories/{category_id}/items` — 添加子项
    - `PUT /api/system/attachment-items/{item_id}` — 更新子项
    - `DELETE /api/system/attachment-items/{item_id}` — 软删除子项
    - `PUT /api/system/attachment-items/{item_id}/reorder` — 子项排序
  - 关联任务：多类型合同 + 附件管理

- **卫星数据合同模块 (`backend/src/satellite/`)**
  - 影响文件：`backend/src/satellite/models.py`, `schemas.py`, `services.py`, `api.py`
  - 路由前缀：`/api/satellite-data-contracts`
  - CRUD + 列表（支持 `customer_id`, `search` 筛选，含 customer_name 关联查询）
  - 关联任务：多类型合同 + 附件管理

- **算力服务合同模块 (`backend/src/compute_service/`)**
  - 影响文件：`backend/src/compute_service/models.py`, `schemas.py`, `services.py`, `api.py`
  - 路由前缀：`/api/compute-service-contracts`
  - CRUD + 列表（支持 `customer_id`, `search` 筛选）
  - 关联任务：多类型合同 + 附件管理

- **默认附件分类初始化**
  - 影响文件：`backend/main.py`, `backend/src/attachment/services.py`
  - 变更内容：应用启动时自动初始化三种合同类型（compute_leasing / satellite_data / compute_service）的默认分类和子项，幂等（已存在则跳过）
  - 默认分类：合同协议(合同扫描件) / 交付材料(验收单扫描件) / 过程材料(资源交付清单 + 资源开通邮件截图)
  - 关联任务：多类型合同 + 附件管理

- **Alembic 迁移**
  - 影响文件：`backend/alembic/versions/c587c343402d_004_add_attachment_satellite_compute_.py`
  - 变更内容：创建 6 张新表（attachment_category, attachment_item, attachment, attachment_status, satellite_data_contract, compute_service_contract）
  - 关联任务：多类型合同 + 附件管理

### 约束
- ⚠️ 现有 `contract` 表/模型/API 一行未改，算力租赁功能不受影响
- 文件上传存储在 `/app/uploads/` 目录下（K8s NFS 挂载），通过 `os.makedirs` 确保目录存在
- 所有新模块遵循项目现有分层：models / schemas / services / api

---

## 2026-07-03 (新增) — 设备列表支持排序

### 新增
- **设备列表支持前端排序**
  - 影响文件：`backend/src/rental/api.py`, `backend/src/rental/services.py`
  - 变更内容：
    1. `GET /api/rentals` 新增 `sort_field` 和 `sort_order` 查询参数
    2. `sort_field` 白名单：`machine_model` / `memory_gb` / `bandwidth_mbps` / `rack_location` / `created_at`
    3. `sort_order` 支持 `asc`（升序，默认）和 `desc`（降序）
    4. `services.list_rentals` 使用白名单校验排序字段，不在白名单或未传时回退默认 `created_at DESC`
  - 关联任务：排序功能

---

## 2026-07-03 (修改) — 系统盘和数据盘字段改为字符串类型 ⚠️

### 修改
- **system_disk_gb Integer → system_disk String，data_disks 对象数组 → 字符串数组**
  - 影响文件：`backend/src/rental/models.py`, `schemas.py`, `api.py`, `services.py`, `backend/src/mail/services.py`, `backend/src/mail/api.py`, `backend/src/contract/services.py`, `backend/expiry_notice_template.html`, `backend/update_all_templates.py`, `backend/src/template/api.py`
  - 变更内容：
    - 模型：`system_disk_gb` (Integer) → `system_disk` (String(256))，存储如 `480GB SATA SSD`
    - 模型：`data_disks` 仍然是 JSON 列，但存储格式从 `[{size_gb, type}]` 改为 `["1000GB NVMe SSD"]` 字符串数组
    - Schema：删除 `DataDiskSchema` 类，所有 `system_disk_gb: Optional[int]` → `system_disk: Optional[str]`，`data_disks: Optional[list[DataDiskSchema]]` → `data_disks: Optional[list[str]]`
    - API 层：移除 DataDiskSchema 构造逻辑，直接透传原始数据
    - 服务层：`create_rental`/`update_rental` 中 data_disks 处理简化为直接赋值
    - 合同服务：SQL 查询和结果 dict 同步更新
    - 邮件模板：`{{ r.system_disk_gb }}GB` → `{{ r.system_disk }}`，数据盘遍历从 `{{ disk.size_gb }}GB {{ disk.type }}` → `{{ disk }}`
    - 模板变量 API：字段说明同步更新
  - 关联任务：磁盘字段优化
  - 备注：⚠️ Breaking Change — 已有数据库中的 `system_disk_gb` 列需通过 Migration 重命名为 `system_disk` 并转换类型；已有的 `data_disks` JSON 数据格式需从对象数组迁移为字符串数组

---

## 2026-07-01 (新增) — 到期提醒邮件模板入库

### 新增
- **expiry_notice 邮件模板写入数据库**
  - 影响文件：数据库 `email_template` 表
  - 变更内容：将 `backend/expiry_notice_template.html` 作为 `body_html` 插入到 `email_template` 表，`trigger_type='expiry_notice'`，模板名称「到期提醒模板」
  - 关联任务：到期提醒模板创建
  - 备注：模板 ID `d6815cc2-b058-454a-a112-4241d67a2d73`，变量包括 `customer_name`、`rental_count`、`rentals`、`reclaim_time`、`end_date`

---

## 2026-07-01 (修复) — 手动取消设备关联时清理 customer_id

### 修复
- **手动取消设备关联时未清理 customer_id**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：`unlink_rentals` 函数中，在 `rental.status = '空闲中'` 之后增加 `rental.customer_id = None`，与 `_reclaim_contract` 和 `delete_contract` 行为对齐
  - 关联任务：BUG
  - 备注：此前手动取消关联后设备列表仍显示旧的客户信息，现已修复

---

## 2026-07-01 (修复) — 客户/设备删除增加关联检查

### 修复
- **客户删除增加活跃合同关联检查**
  - 影响文件：`backend/src/customer/api.py`
  - 变更内容：`DELETE /api/customers/{customer_id}` 软删除前检查该客户是否有 `status IN ('active', 'expiring')` 的关联合同，如有则返回 400 阻止删除，提示用户先处理合同
  - 关联任务：删除关联检查
  - 备注：404 检查（客户是否存在）保留在关联检查之前

- **设备删除增加合同关联检查**
  - 影响文件：`backend/src/rental/api.py`
  - 变更内容：`DELETE /api/rentals/{rental_id}` 硬删除前检查该设备是否通过 `contract_rental` 中间表关联了合同，如有则返回 400 阻止删除，提示用户先在合同中解绑设备
  - 关联任务：删除关联检查
  - 备注：404 检查（设备是否存在）保留在关联检查之前；此前删除设备时 `contract_rental` 外键 `ondelete=CASCADE` 会静默移除关联，无任何提示

---

## 2026-07-01 (修复) — reclaim/expiry_notice 幂等检查增加合同ID过滤

### 修复
- **reclaim/expiry_notice 幂等检查增加按合同ID过滤**
  - 影响文件：`backend/src/mail/services.py`
  - 变更内容：
    1. 幂等检查从「按 rental_ids 交集判断」改为「按 contract_id 精确过滤」，使用 `JSON_EXTRACT(extra_data, '$.contract_id')` 在 SQL 层过滤
    2. EmailLog 写入时 `extra_data` 新增 `contract_id` 字段
  - 关联任务：BUG-回收幂等
  - 备注：避免同一合同被自动回收任务发过邮件后，手动回收时幂等检查误跳过

---

## 2026-07-16 (部署) — 后端镜像重新构建部署

### 部署
- **后端镜像构建 + K8s 滚动更新**
  - 影响文件：`Dockerfile.backend`
  - 变更内容：
    1. Docker 构建 `harbor.xhwltech.com/xhcloud/cronmail-backend:latest`，基于 `python:3.12-slim`
    2. 推送镜像到 Harbor
    3. 滚动重启 `cronmail-backend-api`、`cronmail-backend-beat`、`cronmail-backend-worker` 三个 Deployment
  - 验证：`POST /api/system/trigger/check_expired_rentals` 返回 200，`{"task":"check_expired_rentals","simulated_date":"2026-06-30","result":"None"}`
  - 关联任务：后端部署

---

## 2026-07-06 (修改) ⚠️ — 通知流程 V2：新增 expiry_notice 类型，回收后发邮件，钉钉失败告警

### 修改
- **新增 `expiry_notice` 触发类型**
  - 影响文件：`backend/src/template/models.py`, `backend/src/template/schemas.py`
  - 变更内容：模板 `trigger_type` 枚举新增 `expiry_notice`（到期提醒），与 `provision` / `expiry_warning` / `reclaim` 并列
  - 关联任务：通知流程 V2

- **`check_expired_rentals` 任务行为变更 ⚠️**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：
    1. `trigger_type` 从 `'reclaim'` 改为 `'expiry_notice'`
    2. 邮件发送后（无论成败）都将合同状态改为 `expired`，解除邮件成败与状态耦合
    3. 调度时间默认从 `00:00` 改为 `08:00`
  - 关联任务：通知流程 V2

- **`check_reclaim_expired` 任务行为变更 ⚠️**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：回收成功后调用 `send_merged_email_by_contract(db, c, 'reclaim')` 发送回收通知邮件；邮件失败不影响回收结果（try-except）
  - 调度时间默认从 `01:00` 改为 `00:01`
  - 关联任务：通知流程 V2

- **`send_manual_email` 任务 reclaim 流程调整 ⚠️**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：reclaim 类型改为先回收再发邮件（回收通知 = 资源已回收），与定时任务行为一致
  - 关联任务：通知流程 V2

- **邮件失败钉钉告警**
  - 影响文件：`backend/src/mail/services.py`
  - 变更内容：`send_merged_email_by_contract` 中邮件发送失败时（success=False），追加钉钉告警消息（⚠️ 邮件发送失败），包含合同编号、客户名称、通知类型、收件人、失败原因
  - 关联任务：通知流程 V2

- **`local_today()` 支持模拟日期**
  - 影响文件：`backend/src/core/timezone.py`
  - 变更内容：`local_today()` 和 `local_now()` 支持通过环境变量 `CRONMAIL_SIM_DATE` 覆盖日期（如 `CRONMAIL_SIM_DATE=2026-06-30`）
  - 关联任务：通知流程 V2 调试端点

- **新增调试触发端点 `POST /api/system/trigger/{task_name}`**
  - 影响文件：`backend/src/system/api.py`
  - 变更内容：支持手动触发三个定时任务（`check_expiring_rentals` / `check_expired_rentals` / `check_reclaim_expired`），可传入 `simulate_date` 模拟指定日期
  - 关联任务：通知流程 V2

- **`expiry_notice` 幂等检查**
  - 影响文件：`backend/src/mail/services.py`
  - 变更内容：`send_merged_email_by_contract` 幂等检查从仅 `reclaim` 扩展为 `reclaim` 和 `expiry_notice`，同一天不会重复发送同类型通知
  - 关联任务：通知流程 V2

- **钉钉通知类型映射更新**
  - 影响文件：`backend/src/system/dingtalk.py`
  - 变更内容：`build_notification_markdown` 新增 `expiry_notice` 类型映射（到期提醒 / #e65100）
  - 关联任务：通知流程 V2

- **默认调度时间更新**
  - 影响文件：`backend/main.py`, `backend/src/scheduler/celery_app.py`
  - 变更内容：`check-expired-rentals` 默认 `08:00`（原 `00:00`），`check-reclaim-expired` 默认 `00:01`（原 `01:00`），注释同步更新
  - 关联任务：通知流程 V2

---
## 2026-07-06 (修改) — Dashboard 临期判断改为读系统配置

### 修改
- **Dashboard 临期天数从硬编码改为读取 system_config**
  - 影响文件：`backend/src/contract/dashboard.py`
  - 变更内容：`get_dashboard_stats` 和 `get_expiring_contracts_with_rentals` 中的 `threshold = today + timedelta(days=3)` 硬编码改为从 `system_config.expiry_warning_days` 读取最大天数，新增 `_get_max_expiry_warning_days()` 辅助函数
  - 默认值：配置不存在时回退为 `7` 天（默认配置值 `"7,3"` 的最大值）
  - 关联任务：Dashboard 临期判断配置化

---

## 2026-06-29 (修复) — 合同删除 500：StaleDataError on contract_contact

### 修复
- **DELETE /api/contracts/{id} 删除合同 500 错误**
  - 影响文件：`backend/src/contract/services.py`
  - 根因：`contract_contact` 复合主键为 `(contract_id, contact_id, recipient_type)`，同一联系人可同时有 to 和 cc 两条记录。SQLAlchemy secondary relationship 的 CASCADE 删除按 `(contract_id, contact_id)` 发 DELETE，预期 1 行但实际匹配 2 行，触发 `StaleDataError`
  - 修复方式：`delete_contract` 中在 `db.delete(contract)` 之前，手动 `DELETE FROM contract_contact WHERE contract_id=X` 和 `DELETE FROM contract_rental WHERE contract_id=X`，绕过 secondary relationship 的 cascade 缺陷
  - 关联任务：合同删除 500 排查

---

## 2026-06-29 (修复) ⚠️ — 合同创建 500：contract_contact 主键不包含 recipient_type

### 修复
- **POST /api/contracts 同一联系人 to+cc 导致 IntegrityError 500**
  - 影响文件：`backend/src/contract/models.py`, `backend/alembic/versions/003_contract_contact_pk_fix.py`（新增）
  - 根因：`contract_contact` 表主键为 `(contract_id, contact_id)`，不包含 `recipient_type`。当前端传入同一联系人的 to 和 cc 两条记录时，第二条 INSERT 触发 duplicate primary key 错误
  - 修复方式：
    1. `models.py`：将 `recipient_type` 加入复合主键 `(contract_id, contact_id, recipient_type)`
    2. 数据库 DDL：`ALTER TABLE contract_contact DROP PRIMARY KEY; ALTER TABLE contract_contact ADD PRIMARY KEY (contract_id, contact_id, recipient_type);`
    3. `_replace_contract_contacts` 去重逻辑保持不变（按 `(contact_id, recipient_type)` 去重，与新主键一致）
  - 关联任务：合同创建 500 排查
  - 备注：⚠️ 已直接在 MySQL 上执行 DDL 并 stamp alembic 版本为 003；下次构建镜像时 003 migration 文件会随代码部署

---

## 2026-06-29 (新增) — 通知调度时间可配置化

### 新增
- **`GET /api/system/config/schedules`**：获取所有通知调度时间配置（临期提醒、到期通知、回收执行）
- **`PUT /api/system/config/schedules`**：批量更新通知调度时间，自动触发 Beat 重启使新配置生效
- **`services.upsert_system_config()`**：创建或更新 system_config 键值对的通用函数
- **`services.restart_beat()`**：通过 K8s API PATCH Deployment 触发 Beat 滚动重启

### 修改
- **`celery_app.py`**：将硬编码的 `crontab(hour=8, minute=0)` 等改为从数据库 `system_config` 表动态读取，通过 `on_after_configure` 信号在 Beat 启动前加载
- **`main.py`**：lifespan 中增加默认调度时间初始化（`check-expiring-rentals: 08:00`, `check-expired-rentals: 00:00`, `check-reclaim-expired: 01:00`）

### 影响文件
- `backend/src/scheduler/celery_app.py`
- `backend/src/system/api.py`
- `backend/src/system/services.py`
- `backend/main.py`

### 关联任务
- 通知时间配置后端

---

## 2026-07-16 (修复) — 定时任务健壮性修复

### 修复
- **FIX-1（致命）：`check_expired_rentals` 范围查询兜底**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：`Contract.end_date == today` 改为 `Contract.end_date <= today`，配合 status 过滤（`active/expiring`）实现天然幂等。Beat 宕机漏处理的到期合同会被后续扫描捕获，已处理（状态已变 expired/reclaimed）的不会被重复命中。增加 WARNING 日志：当 `end_date < today` 时打印漏处理警告
  - 关联任务：定时任务健壮性修复

- **FIX-2（高危）：`check_expiring_rentals` 范围查询兜底**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：`Contract.end_date == threshold` 改为 `Contract.end_date <= threshold`，同上原因。增加 WARNING 日志
  - 关联任务：定时任务健壮性修复

- **FIX-3（高危）：提取公共回收逻辑 `_reclaim_contract`**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：新增 `_reclaim_contract(db, contract)` 辅助函数（改状态、清关联、删中间表），供 `check_reclaim_expired` 和 `send_manual_email` 的 reclaim 分支共用，消除重复代码
  - 关联任务：定时任务健壮性修复

- **FIX-4（中危）：`send_merged_email_by_contract` reclaim 幂等保护**
  - 影响文件：`backend/src/mail/services.py`
  - 变更内容：在函数开头增加 reclaim 类型幂等检查：查询今天是否有同合同的 reclaim 邮件已发送成功（通过 `email_log` 表的 `trigger_type`/`status`/`created_at`/`extra_data.rental_ids` 交集判断），有则跳过
  - 关联任务：定时任务健壮性修复

---

## 2026-06-28 (修复)

### 修复
- **创建合同联系人重复导致 IntegrityError 500**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：`_replace_contract_contacts` 增加按 `(contact_id, recipient_type)` 去重逻辑，防止前端传入重复联系人（同一 contact_id + recipient_type 组合多次出现）导致 MySQL duplicate primary key 错误
  - 关联任务：合同列表 API 500 排查
  - 备注：实际报 500 的接口是 `POST /api/contracts`（创建合同），非列表接口 `GET /api/contracts`（列表始终 200 OK）。根因是前端可能传了重复的联系人数据

---

## 2026-06-27 (审计修复)

### 修复
- **F-1（致命）：错开回收任务时间**
  - 影响文件：`backend/src/scheduler/celery_app.py`
  - 变更内容：`check-reclaim-expired` crontab 从 `hour=0, minute=0` 改为 `hour=1, minute=0`，避免与 `check-expired-rentals` 同时 00:00 触发导致竞态
  - 关联任务：审计修复 F-1

- **F-2（致命）：手动回收加状态检查**
  - 影响文件：`backend/src/scheduler/tasks.py`, `backend/src/rental/api.py`
  - 变更内容：
    1. `send_manual_email` reclaim 分支：执行回收前检查 `contract.status == 'expired'`，不是则打印日志并 return
    2. `POST /api/rentals/{id}/reclaim` 端点：提交异步任务前检查 `contract.status == 'expired'`，否则返回 400 "仅已到期合同可执行回收"
  - 关联任务：审计修复 F-2

- **H-1（高危）：删除合同清理设备字段**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：`delete_contract` 删除前遍历 `contract.rentals`，将每个设备的 `status` 置为 `'空闲中'`、`customer_id` 置 `None`
  - 关联任务：审计修复 H-1

- **M-1（中危）：临期天数去重**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：`check_expiring_rentals` 解析 `expiry_warning_days` 后对 `days_list` 做 `list(set(...))` 去重并排序，防止配置重复值导致重复发邮件
  - 关联任务：审计修复 M-1

- **M-2（中危）：去掉无效 rollback**
  - 影响文件：`backend/src/scheduler/tasks.py`
  - 变更内容：在 `check_expired_rentals` 和 `check_expiring_rentals` 中删除无效的 `db.rollback()` 调用（子函数 `send_merged_email_by_contract` 内部已 commit，外层 rollback 无意义），只保留错误日志
  - 关联任务：审计修复 M-2

- **M-3（中危）：邮件成功状态更新原子化**
  - 影响文件：`backend/src/scheduler/tasks.py`, `backend/src/mail/services.py`
  - 变更内容：将 `c.status = 'expired'` 从 `check_expired_rentals` 移到 `send_merged_email_by_contract` 内部（邮件发送成功且 trigger_type=='reclaim' 时，在 log commit 之前更新），确保邮件发送和状态变更在同一事务内
  - 关联任务：审计修复 M-3

- **M-4（中危）：合同关联设备 TOCTOU**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：`_link_rentals` 中 `contract_rental.insert()` 包裹 `try/except IntegrityError`，捕获后 raise `HTTPException(status_code=409, detail="设备已被其他合同关联")` 代替 500
  - 关联任务：审计修复 M-4

---

## 2026-06-27 (修复)

### 修复
- ⚠️ **定时任务和 Dashboard 时区 Bug 修复**：Pod 系统时区为 UTC，`date.today()` 返回 UTC 日期，导致北京时间的定时任务查询条件偏移了 8 小时
  - 影响文件：`backend/src/core/timezone.py`, `backend/src/scheduler/tasks.py`, `backend/src/contract/dashboard.py`, `backend/src/mail/services.py`, `backend/src/mail/api.py`, `backend/src/rental/services.py`
  - 根因：Pod 系统时区为 UTC（`/etc/localtime → Etc/UTC`），`date.today()` 在北京时间 00:00（UTC 16:00）返回前一天日期。Celery `timezone='Asia/Shanghai'` 只影响 crontab 调度时间解析，不影响 Python 运行时 `date.today()`
  - 具体影响：
    1. `check_expired_rentals`（每天 00:00 CST）：`end_date == date.today()` 实际查询的是 UTC 日期，比北京时间晚 8 小时。例如 6月27日 00:00 CST（UTC 6月26日 16:00），`date.today()` 返回 `2026-06-26`，匹配不到 `end_date=2026-06-27` 的合同
    2. `check_expiring_rentals`（每天 08:00 CST）：同上，`threshold = today + timedelta(days=offset)` 计算偏移
    3. `check_reclaim_expired`（每天 00:00 CST）：同上
    4. Dashboard `get_dashboard_stats` / `get_expiring_contracts_with_rentals`：`end_date > today` 条件因 UTC 时区导致当天到期的合同被排除；且 `>` 改为 `>=` 以确保当天到期的合同也显示为"即将到期"
    5. `send_merged_email` / `send_merged_email_by_contract`：`days_until_expiry` 计算偏差
    6. `build_rental_context`（`rental/services.py`）：`days_until_expiry` 计算偏差
    7. `_build_rental_context`（`mail/api.py`）：`days_until_expiry` 计算偏差
  - 修复方式：
    1. `timezone.py` 新增 `local_today()` 函数：`(datetime.utcnow() + timedelta(hours=8)).date()`
    2. 全局替换所有 `date.today()` → `local_today()`
    3. Dashboard 条件 `end_date > today` → `end_date >= today`（当天到期也显示）
  - 关联任务：合同到期回收通知 Bug 排查

---

## 2026-06-26 (部署)

### 变更
- 三套邮件模板升级为 7 列布局（服务器类型 | IP | 操作系统 | 系统盘 | 数据盘 | 带宽 | 到期时间）
- 开通邮件新增「登录信息」区域
- 新增钉钉机器人通知功能（含配置管理 API、邮件发送后自动推送）
- 钉钉通知含客户信息（名称、编码、合同编号、计费方式）及设备 IP/机架

---

## 2026-07-16 (新增) — 钉钉机器人通知

### 新增
- **钉钉机器人通知功能**
  - 影响文件：`backend/src/system/models.py`, `backend/src/system/schemas.py`, `backend/src/system/services.py`, `backend/src/system/api.py`, `backend/src/system/dingtalk.py`（新建）, `backend/src/mail/services.py`, `backend/requirements.txt`
  - 变更内容：
    1. 新增 `DingTalkConfig` 数据模型（`dingtalk_config` 表），单条记录模式，字段：`webhook_url`、`secret`、`is_active`、`created_at`、`updated_at`
    2. 新增钉钉配置管理 API：
       - `GET /api/system/dingtalk` — 获取配置（secret 脱敏显示 `***`）
       - `PUT /api/system/dingtalk` — upsert 配置（secret 传 `***` 保留原值，传 `""` 清空，传其他值更新）
       - `POST /api/system/dingtalk/test` — 测试发送 Markdown 消息（可传自定义 webhook_url/secret）
    3. 新建 `src/system/dingtalk.py` 钉钉发送核心模块：
       - `_sign_dingtalk()` — HMAC-SHA256 加签逻辑
       - `_build_url()` — 构建带签名的 Webhook URL
       - `send_dingtalk_markdown()` — 发送钉钉 Markdown 消息（timeout 10s）
       - `build_notification_markdown()` — 构建邮件通知 Markdown 消息（含设备 IP 和机架位置）
    4. `send_merged_email_by_contract()` 邮件发送成功后自动推送钉钉通知：
       - 仅 `status == 'sent'` 时触发
       - 钉钉配置存在且 `is_active` 且 `webhook_url` 非空时才发送
       - 通知内容：通知类型、客户名称、设备数量、收件人、发送时间、关联设备列表（型号/IP/机架）
       - 钉钉失败不影响邮件发送（try-except 包裹）
    5. `requirements.txt` 新增 `requests` 依赖
  - 关联任务：钉钉机器人通知后端

---

## 2026-07-16 (修改) — 三套邮件模板 HTML 统一升级

### 修改
- **邮件模板 body_html 统一为 7 列布局**
  - 影响文件：`backend/update_all_templates.py`（新增一次性脚本）
  - 变更内容：
    1. 三套模板（provision / expiry_warning / reclaim）统一表格列：`服务器类型 | IP 地址 | 操作系统 | 系统盘 | 数据盘 | 带宽 | 到期时间`
    2. **开通邮件 (provision)**：绿色主题 #2e7d32，新增"登录信息"区域（IP / 账号 / 密码），底部蓝色提示
    3. **临期邮件 (expiry_warning)**：橙色主题 #ef6c00，到期时间红色加粗，底部橙色提示含续租指引
    4. **回收邮件 (reclaim)**：红色主题 #e53935，保留回收信息表格，底部红色重要提醒（3 条）
    5. 所有模板保持统一风格：620px 容器、圆角 8px、白色背景、阴影、微软雅黑字体、表格交替行色
    6. 数据盘使用 Jinja2 for 循环格式化：`{{ disk.size_gb }}GB {{ disk.type }}`，空时显示 "-"
    7. 脚本自动查找各 trigger_type 的活跃模板，更新 `body_html` + `version += 1`
  - 关联任务：邮件模板 HTML 升级

---

## 2026-07-16 (修改) — 后端 4 项优化

### 修改
- **时区修正 UTC→UTC+8**
  - 影响文件：`backend/src/core/timezone.py`（新增）, `backend/src/customer/models.py`, `backend/src/rental/models.py`, `backend/src/contract/models.py`, `backend/src/template/models.py`, `backend/src/system/models.py`, `backend/src/mail/models.py`, `backend/src/mail/services.py`, `backend/migrate_to_contract.py`
  - 变更内容：新增 `local_now()` 辅助函数（`datetime.utcnow() + timedelta(hours=8)`），全局替换所有 `datetime.utcnow` 为 `local_now`
  - 关联任务：时区修正

- **邮件日志 1 通知 = 1 条日志**
  - 影响文件：`backend/src/mail/models.py`, `backend/src/mail/services.py`
  - 变更内容：
    1. `EmailLog` 新增 `extra_data` JSON 字段存储关联信息（`rental_ids`, `to_emails`, `cc_emails`）
    2. `send_merged_email` 和 `send_merged_email_by_contract` 从 N×M 条日志改为只写 1 条日志
  - 关联任务：邮件日志去重

- **可配置临期提醒天数**
  - 影响文件：`backend/src/system/models.py`, `backend/src/system/api.py`, `backend/src/scheduler/tasks.py`, `backend/main.py`
  - 变更内容：
    1. 新增 `SystemConfig` 模型（`system_config` 表，key-value 存储）
    2. 新增 SystemConfig CRUD API：`GET/PUT /api/system/config`、`GET /api/system/config/{key}`
    3. 定时任务 `check_expiring_rentals` 改为从 `system_config.expiry_warning_days` 读取天数配置（默认 "7,3"）
    4. 应用启动时自动初始化默认配置
  - 关联任务：可配置临期提醒

- **仪表盘 API 检查**
  - 影响文件：`backend/src/contract/dashboard.py`
  - 变更内容：确认 `get_dashboard_stats` 和 `get_expiring_contracts_with_rentals` 逻辑正确，无需修改
  - 关联任务：仪表盘检查

### 数据库迁移
```sql
-- EmailLog 新字段
ALTER TABLE email_log ADD COLUMN extra_data JSON NULL COMMENT '关联信息: rental_ids, to_emails, cc_emails';

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id CHAR(36) PRIMARY KEY,
    `key` VARCHAR(100) UNIQUE NOT NULL,
    value VARCHAR(500) NOT NULL,
    description VARCHAR(255),
    updated_at DATETIME
);
INSERT IGNORE INTO system_config (id, `key`, value, description) VALUES (UUID(), 'expiry_warning_days', '7,3', '临期提醒天数（逗号分隔）');
```

---

## 2026-07-16 (修改) ⚠️ — 设备状态改为裸金属语义 + public_ips JSON 解析修复

### 修改
- ⚠️ **设备状态改为裸金属物理语义（与合同状态解耦）**
  - 影响文件：`backend/src/rental/schemas.py`, `backend/src/rental/services.py`, `backend/src/rental/api.py`, `backend/src/scheduler/tasks.py`
  - 变更内容：
    1. 设备状态值从英文改为中文：`provisioned` → `运行中`，`reclaimed` → `已下架`
    2. 新增可用状态：`维护中`、`故障`（人工可设置）
    3. `RentalRecordUpdate` Schema 新增 `status` 字段（Optional），允许人工修改设备物理状态
    4. `create_rental` 默认状态从 `provisioned` 改为 `运行中`
    5. `check_expired_rentals` / `send_manual_email` 中回收设备时：`r.status = '已下架'`
    6. `update_contract` 不再自动同步设备状态（设备状态人工管理）
    7. API 文档 `GET /api/rentals` status 参数说明更新为：`运行中 | 维护中 | 已下架 | 故障`
  - 关联任务：设备状态裸金属语义
  - 备注：合同状态（active/expiring/expired/reclaimed）保持不变；设备状态现在是物理状态，与合同状态解耦

- **数据库迁移**
  - 影响文件：`backend/alembic/versions/001_rental_status_chinese.py`
  - 变更内容：
    ```sql
    UPDATE rental_record SET status = '运行中' WHERE status = 'provisioned';
    UPDATE rental_record SET status = '运行中' WHERE status = 'expiring';
    UPDATE rental_record SET status = '运行中' WHERE status = 'expired';
    UPDATE rental_record SET status = '已下架' WHERE status = 'reclaimed';
    ```
  - 备注：部署后需执行 `alembic upgrade head`

### 修复
- **`get_contract_rentals` 中 `public_ips` JSON 字符串解析**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：原生 SQL `text()` 查询 JSON 列时可能返回字符串，在构建返回 dict 时增加 `json.loads()` 解析，确保前端收到的是数组而非字符串
  - 关联任务：public_ips 显示修复
  - 备注：同时影响合同详情 API 和仪表盘 API（它们都调用了 `get_contract_rentals`）

---

## 2026-07-03 (修改) ⚠️ — 设备管理简化：客户/日期/计费全从合同继承

### 修改
- ⚠️ **设备创建/编辑不再接受客户、日期、计费字段**
  - 影响文件：`backend/src/rental/schemas.py`, `backend/src/rental/services.py`, `backend/src/rental/api.py`, `backend/src/rental/models.py`, `backend/src/contract/services.py`
  - 变更内容：
    1. `RentalRecordCreate` Schema 移除 `customer_id`、`contacts`、`start_date`、`end_date`、`billing_model`、`auto_renew` 字段，`machine_model` 改为 Optional
    2. `RentalRecordUpdate` Schema 同样移除上述字段
    3. `create_rental` service：`customer_id` 默认 None，不再处理 contacts 写入
    4. `update_rental` service：移除 contacts 替换逻辑
    5. `create_rental` / `update_rental` API 端点：去掉客户校验和联系人校验逻辑
    6. `RentalRecord.customer_id` 列改为 `nullable=True`
  - 关联任务：设备管理简化
  - 备注：设备现在作为纯硬件档案存在，客户、日期、计费信息全部从关联合同继承

- ⚠️ **设备列表/详情返回合同继承字段**
  - 影响文件：`backend/src/rental/api.py`, `backend/src/rental/schemas.py`
  - 变更内容：
    1. `_rental_to_list_item` / `_rental_to_detail`：通过 `rental.contracts[0]` 取合同，从中获取 `customer_name`、`start_date`、`end_date`、`billing_model`、`auto_renew`
    2. 无合同时返回 None/"-"，兼容旧数据（回退到 `rental.customer`）
    3. `RentalRecordDetailResponse` 新增 `contract_info: Optional[dict]` 字段，返回关联合同的 id/name/start_date/end_date/billing_model
  - 关联任务：设备管理简化

- **关联合同时自动同步设备字段**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：
    1. `_link_rentals`：关联设备时同步 `customer_id`、`end_date`、`start_date`、`billing_model` 到设备
    2. `update_contract`：合同关键字段（customer_id/end_date/start_date/billing_model）变更时同步给所有关联设备
  - 关联任务：设备管理简化

### 数据库变更
- `ALTER TABLE rental_record MODIFY customer_id CHAR(36) NULL;`（需在 Pod 内手动执行）

---

## 2026-07-03 (新增) — 后端 6 项优化

### 新增
- **租赁搜索增加机架位置过滤**
  - 影响文件：`backend/src/rental/api.py`, `backend/src/rental/services.py`
  - 变更内容：
    1. `GET /api/rentals` 新增 `rack_location` 查询参数，支持按机架位置模糊搜索
    2. `services.list_rentals` 新增 `rack_location` 参数，使用 `ilike` 过滤
  - 关联任务：优化 1

- **设备唯一合同约束**
  - 影响文件：`backend/src/contract/models.py`, `backend/src/contract/services.py`
  - 变更内容：
    1. `contract_rental` 中间表的 `rental_id` 列增加 `unique=True`，确保一个设备只能关联一个合同
    2. `_link_rentals` 增加全局冲突检测：如果 `rental_id` 已被其他合同占用，跳过并打印 warning 日志
  - 关联任务：优化 2
  - 备注：需要 Pod 内手动执行 `ALTER TABLE contract_rental ADD UNIQUE INDEX uq_rental_id (rental_id);`（auto-create_all 不会改已有表结构）

- **仪表盘合同统计 API**
  - 影响文件：`backend/src/contract/dashboard.py`（新建）, `backend/src/contract/api.py`
  - 变更内容：
    1. 新建 `dashboard.py`：`get_dashboard_stats(db)` 返回 total_contracts/expiring/expired；`get_expiring_contracts_with_rentals(db)` 返回临期合同及其关联设备
    2. `GET /api/contracts/dashboard/stats` — 仪表盘合同运营概览统计
  - 关联任务：优化 3

- **变更记录系统**
  - 影响文件：`backend/src/contract/models.py`, `backend/src/contract/api.py`
  - 变更内容：
    1. 新增 `ChangeLog` 模型（表名 `change_log`）：`id`、`target_type`（contract/rental）、`target_id`、`content`、`created_at`
    2. `GET /api/contracts/changelog?target_type=xxx&target_id=xxx` — 查询变更记录
    3. `POST /api/contracts/changelog` — 创建变更记录
  - 关联任务：优化 4

### 修改
- **设备 end_date 自动从合同同步**
  - 影响文件：`backend/src/contract/services.py`
  - 变更内容：
    1. `_link_rentals`：关联设备后同步 `rental.end_date = contract.end_date`
    2. `update_contract`：合同 `end_date` 变更时同步给所有关联设备的 `end_date`
    3. `unlink_rentals` 解绑时不动 `end_date`（保留最后值）
  - 关联任务：优化 5

---

## 2026-07-03 (修改) — Phase 3 ⚠️

### 修改
- ⚠️ **邮件系统改为合同驱动**
  - 影响文件：`backend/src/mail/services.py`, `backend/src/scheduler/tasks.py`, `backend/src/rental/api.py`
  - 变更内容：
    1. **新增 `send_merged_email_by_contract` 函数**（`mail/services.py`）：按合同合并发送邮件，从 `contract_rental` 和 `contract_contact` 获取设备和联系人。`end_date`、`billing_model`、`days_until_expiry` 从 Contract 获取（而非 RentalRecord 的 DEPRECATED 字段）
    2. **`send_manual_email` Celery 任务签名变更**：参数从 `(rental_ids, customer_id, trigger_type)` 改为 `(contract_id, trigger_type)`，任务名保持 `scheduler.tasks.send_manual_email` 不变
    3. **`check_expiring_rentals` 定时任务改为扫合同**：查询 Contract 表（`end_date <= today+3 AND end_date > today AND status IN ('active','expiring')`），按合同逐个调用 `send_merged_email_by_contract`
    4. **`check_expired_rentals` 定时任务改为扫合同**：查询 Contract 表（`end_date < today AND status IN ('active','expiring')`），发送回收邮件后更新合同和设备状态为 `reclaimed`
    5. **三个手动端点改为合同驱动**：
       - `POST /api/rentals/{id}/send-provision-email`：从 rental 找到关联合同 → dispatch Celery 任务
       - `POST /api/rentals/{id}/send-expiry-reminder`：从 rental 找到关联合同 → 更新合同状态为 expiring → dispatch
       - `POST /api/rentals/{id}/reclaim`：从 rental 找到关联合同 → dispatch（状态更新在 Celery 任务中）
       - 如果设备未关联合同，返回 400 错误
    6. **保留旧 `send_merged_email` 函数不动**（兼容可能存在的调用）
  - 关联任务：Phase 3 — 邮件系统改为合同驱动
  - 备注：定时任务名称 `check_expiring_rentals` / `check_expired_rentals` 保持原名不变（避免 Celery Beat 配置变更），但内部逻辑已改为扫合同

---

## 2026-07-03 (新增) — Phase 2

### 新增
- **Contract API（合同 CRUD + 设备关联 + 联系人管理）**
  - 影响文件：`backend/src/contract/schemas.py`, `backend/src/contract/services.py`, `backend/src/contract/api.py`, `backend/main.py`
  - 路由前缀：`/api/contracts`
  - 变更内容：
    1. `GET /api/contracts` — 合同列表，支持 `customer_id`、`status`、`search` 过滤和分页
    2. `POST /api/contracts` — 创建合同，可同时关联设备（`rental_ids`）和联系人（`contacts`）
    3. `GET /api/contracts/{id}` — 合同详情，含关联设备和联系人列表
    4. `PUT /api/contracts/{id}` — 更新合同，支持全量替换联系人
    5. `DELETE /api/contracts/{id}` — 删除合同（CASCADE 删除中间表关联）
    6. `POST /api/contracts/{id}/rentals` — 关联设备（跳过已存在的避免 duplicate key）
    7. `DELETE /api/contracts/{id}/rentals` — 取消关联设备
  - 关联任务：Phase 2 — 合同 API（CRUD + 设备关联 + 联系人管理）

- **Contract（合同）模块数据模型**
  - 影响文件：`backend/src/contract/__init__.py`, `backend/src/contract/models.py`
  - 变更内容：
    1. 新增 `Contract` 模型（表名 `contract`），作为合同聚合根：
       - `id`（UUID 主键）、`customer_id`（外键 → customer）、`name`、`contract_no`、`start_date`、`end_date`
       - `billing_model`（monthly / quarterly / yearly）、`status`（active / expiring / expired / reclaimed）
       - `remark`、`created_at`、`updated_at`
    2. 新增 `contract_rental` 中间表：Contract 与 RentalRecord M:N 关联，含 `created_at` 时间戳
    3. 新增 `contract_contact` 中间表：Contract 与 Contact M:N 关联，含 `recipient_type`（to / cc）
    4. 所有外键使用 `ondelete='CASCADE'`
  - 关联任务：Phase 1 — 合同系统数据模型

- **数据迁移脚本**
  - 影响文件：`backend/migrate_to_contract.py`
  - 变更内容：将现有 RentalRecord 按 (customer_id, start_date, end_date, billing_model) 分组，每组创建一个 Contract，迁移 rental_contact → contract_contact（去重）
  - 执行方式：`python migrate_to_contract.py`（需手动调用）
  - 关联任务：Phase 1 — 合同系统数据模型

### 修改
- **RentalRecord 模型字段标记为 DEPRECATED**
  - 影响文件：`backend/src/rental/models.py`
  - 变更内容：`end_date`、`billing_model` 字段的 comment 标注 "DEPRECATED: 请从关联 Contract 获取"，字段保留不做删除
  - 关联任务：Phase 1 — 合同系统数据模型

- **main.py 注册 contract 模块**
  - 影响文件：`backend/main.py`
  - 变更内容：添加 `import src.contract.models` 确保 Base.metadata 包含 contract 相关表

---

## 2026-07-01 (修复)

### 修复
- **邮件主题里塞了签名 HTML**
  - 影响文件：`backend/src/mail/services.py`
  - 变更内容：`send_merged_email()` 中 `render_template(template.subject_tpl, ...)` 去掉 `signature_html` 参数，仅 body 渲染时传入签名
  - 关联任务：Bug 修复 - 邮件主题不应包含签名 HTML
  - 备注：`subscribers.py` 中 `_send_email_for_rental()` 原本已正确处理（subject 不传 signature），无需修改

- ⚠️ **手动回收/开通/临期 API 超时 15s（同步 SMTP 阻塞）**
  - 影响文件：`backend/src/rental/api.py`, `backend/src/scheduler/tasks.py`, `backend/src/rental/schemas.py`
  - 变更内容：
    1. `scheduler/tasks.py` 新增 `send_manual_email` Celery 任务：重新查询 records + customer → 调用 `send_merged_email` → reclaim 类型更新状态为 reclaimed
    2. `rental/api.py` 三个手动端点改为 `send_manual_email.delay()` 异步调度，立即返回 202（`SendEmailResponse` 含 `message` 字段说明已提交异步任务）
    3. `reclaim_rental` 状态更新逻辑移到 Celery 任务中，API 不再等待 SMTP
    4. `SendEmailResponse` Schema 新增 `message: Optional[str]` 字段
  - 关联任务：Bug 修复 - 手动邮件发送改为 Celery 异步，避免 FastAPI 默认 15s 超时

---

## 2026-07-01 (修改)

### 修改
- ⚠️ **手动邮件发送改为按客户合并发送**
  - 影响文件：`backend/src/rental/api.py`, `backend/src/mail/services.py`, `backend/src/scheduler/helpers.py`, `backend/src/scheduler/tasks.py`
  - 变更内容：
    1. `_send_merged_email` 从 `scheduler/helpers.py` 移动到 `mail/services.py`，改名为 `send_merged_email`（公开函数），返回 `dict {"log_ids": [...], "recipient_count": n}`
    2. `scheduler/helpers.py` 改为 re-export：`from src.mail.services import send_merged_email`
    3. `scheduler/tasks.py` 更新 import 路径为 `from src.mail.services import send_merged_email`
    4. `rental/api.py` 三个手动发送端点改为直接调用合并发送逻辑：
       - `send_provision_email`：查同客户同 start_date 的 provisioned 记录 → 合并发送
       - `send_expiry_reminder`：查同客户未来3天内到期的记录 → 更新状态为 expiring → 合并发送
       - `reclaim_rental`：查同客户同 end_date 的记录 → 合并发送 → 批量更新状态为 reclaimed
    5. `send_merged_email` 新增 `provision` trigger_type 支持（原仅 `expiry_warning` / `reclaim`）
    6. 写 EmailLog 时增加 `db.flush()` 以在 commit 前获取 log id
  - 关联任务：手动邮件合并发送（ADR-009）
  - 备注：定时任务逻辑不受影响，仍调用同一 `send_merged_email` 函数；blinker 事件订阅者不再用于手动发送路径

### 修复
- ⚠️ **测试发送变量结构统一为 rentals 数组**
  - 影响文件：`backend/src/template/api.py`, `backend/src/rental/services.py`, `backend/src/mail/api.py`
  - 变更内容：
    1. `POST /api/templates/{id}/test-send`：`sample_data` 自动包装为统一结构 `{customer_name, rental_count: 1, rentals: [sample_data]}`
    2. `build_rental_context()`（`rental/services.py`）：返回值从平铺字段改为统一结构，单条设备包装为 `rentals[0]`
    3. `_build_rental_context()`（`mail/api.py` 重发用）：同上
    4. 定时合并发送（`scheduler/helpers.py`）原本已使用统一结构，无需修改
  - 关联任务：测试发送变量结构修复
  - 备注：现在所有发送路径（测试发送 / 手动单发 / 定时合并）均使用一致的模板变量结构：`customer_name` + `rental_count` + `rentals` 数组

---

## 2026-06-26 (修复)

### 修复
- **Beat Pod CrashLoopBackOff 修复**：liveness probe 使用 `pgrep` 命令，但 `python:3.12-slim` 镜像未安装 `procps` 包导致 `pgrep: not found`
  - 影响文件：`Dockerfile.backend`, `k8s/backend-beat.yaml`
  - 根因：容器镜像基于 `python:3.12-slim`，缺少 `procps` 包，liveness probe 中 `pgrep -f 'celery.*beat'` 命令不存在
  - 修复方式：
    1. `Dockerfile.backend` 安装 `procps` 包（提供 `pgrep` 命令）
    2. `k8s/backend-beat.yaml` liveness probe 改用 `pidof python`（busybox 内置，无需额外包）
  - 关联任务：Beat Pod 崩溃修复

---

## 2026-06-26 (修改)

### 修改
- ⚠️ **定时任务改为按客户合并发送邮件**
  - 影响文件：`backend/src/scheduler/tasks.py`, `backend/src/scheduler/helpers.py`（新增）, `backend/src/template/api.py`
  - 变更内容：
    1. `check_expiring_rentals`：扫描到期前 ≤3 天的记录 → 按 `customer_id` 分组 → 更新 status='expiring' → 每组调用 `_send_merged_email` 合并发送
    2. `check_expired_rentals`：同理，按 `customer_id` 分组 → 更新 status='reclaimed' → 合并发送回收邮件
    3. 新增 `backend/src/scheduler/helpers.py`：`_send_merged_email()` 合并发送函数
       - 去重收件人（跨多台设备的 contacts）
       - 构建 `rentals` 数组上下文 + `customer_name` + `rental_count`
       - 渲染 Jinja2 模板 → SMTP 发送 → 每条记录写 EmailLog
    4. 模板变量 API `GET /api/templates/variables` 新增 `rental_count` 和 `rentals` 字段
    5. 定时任务不再使用 blinker 事件系统，直接调用合并发送函数
  - 关联任务：定时任务邮件按客户合并发送
  - 备注：手动发送（详情页按钮）不受影响，仍走 blinker 事件单机发送

---

## 2026-06-26 (新增)

### 新增
- **模板可用变量动态接口 + 预览拼接签名**
  - 影响文件：`backend/src/template/api.py`, `backend/src/template/schemas.py`
  - 变更内容：
    1. 新增 `GET /api/templates/variables` 接口，返回 21 个租赁记录模板变量（field/label/type/note）
    2. `TemplatePreviewRequest` Schema 新增 `signature_html: Optional[str]` 字段
    3. `POST /api/templates/preview` 接口渲染时传入 `signature_html` 参数，实现签名拼接预览
  - 关联任务：前端模板编辑器需要动态变量列表 + 预览时拼接签名

### 新增
- **联系人列表支持 all=true 查询所有客户联系人**
  - 影响文件：`backend/src/customer/api.py`, `backend/src/customer/services.py`
  - 变更内容：
    1. `GET /api/contacts` 新增 `all` 查询参数
    2. `type=customer&all=true` 时无需传 `customer_id`，返回所有客户联系人（`customer_id IS NOT NULL`）
    3. `list_contacts` service 函数新增 `all_customers` 参数
  - 关联任务：前端需要拉取所有客户联系人

---

## 2026-06-26 (新增)

### 新增
- **邮件模板签名字段 + 测试发送 API**
  - 影响文件：`backend/src/template/models.py`, `backend/src/template/schemas.py`, `backend/src/template/api.py`, `backend/src/mail/renderer.py`, `backend/src/mail/subscribers.py`, `backend/src/mail/api.py`
  - 变更内容：
    1. `EmailTemplate` 模型新增 `signature_html` 字段（TEXT, nullable），邮件签名（HTML）
    2. `EmailTemplateCreate`、`EmailTemplateUpdate`、`EmailTemplateResponse` Schema 均补上 `signature_html: Optional[str]`
    3. 新增 `TemplateTestSendRequest` / `TemplateTestSendResponse` Schema
    4. `render_template()` 函数新增 `signature_html` 参数，渲染 body 后自动拼接 `<!-- signature -->\n{signature_html}`
    5. 新增 `POST /api/templates/{id}/test-send` 接口：根据 contact ids 查邮箱 → 渲染模板 → SMTP 发送，不写 EmailLog
    6. `subscribers.py` 和 `mail/api.py` 中 `render_template` 调用同步传入 `signature_html`
  - 数据库变更：`ALTER TABLE cronmail.email_template ADD COLUMN signature_html TEXT NULL COMMENT '邮件签名'`
  - 关联任务：邮件模板增加签名字段 + 测试发送 API

---

## 2026-06-26 (修改)

### 修改
- **GET /api/rentals 列表响应扩展为全字段**
  - 影响文件：`backend/src/rental/schemas.py`, `backend/src/rental/api.py`
  - 变更内容：`RentalRecordListResponse` 从 8 个字段扩展到 23 个字段，对齐详情接口但不含 `root_password`、`contacts`、`email_logs`
  - 新增字段：`cpu_model`, `memory_gb`, `gpu_info`, `system_disk_gb`, `data_disks`, `os_version`, `bandwidth_mbps`, `rack_location`, `public_ips`, `ssh_port`, `root_username`, `billing_model`, `auto_renew`, `remark`, `updated_at`
  - `_rental_to_list_item` 同步更新，处理 `data_disks` JSON 反序列化
  - 关联任务：后端租赁列表 API 返回全字段

---

## 2026-06-26 (新增)

### 新增
- **SMTP 支持 STARTTLS (端口 587) 和无加密 (端口 25)**
  - 影响文件：`backend/src/system/models.py`, `schemas.py`, `services.py`, `backend/src/mail/sender.py`, `subscribers.py`, `api.py`, `frontend/src/api/modules/system.ts`, `frontend/src/views/system/smtp.vue`, `docs/api-contracts.md`, `docs/backend/api.md`
  - 变更内容：
    1. `SmtpConfig` 模型新增 `encryption` 字段（VARCHAR(16)，默认 'tls'），保留旧 `use_tls` 字段标记为 DEPRECATED 兼容过渡
    2. Schema `SmtpConfigResponse` / `SmtpConfigUpdate` 中 `use_tls: bool` 改为 `encryption: str`，枚举 `tls | starttls | none`，带 validator 校验
    3. `send_email()` 参数 `use_tls: bool` → `encryption: str`，按三种模式分发：`tls`→SMTP_SSL，`starttls`→SMTP+starttls()，`none`→SMTP 明文
    4. `test_smtp_connection()` 同样按 encryption 三种模式分发，兼容旧 `use_tls` 字段
    5. 前端 `use_tls` 开关替换为加密方式下拉选择（SSL/TLS / STARTTLS / 无加密）
    6. 前端 API 类型 `SmtpConfig` / `SmtpConfigUpdate` 中 `use_tls` → `encryption`
    7. ⚠️ Breaking Change：API 契约 `use_tls: true` → `encryption: "tls"`，旧客户端传 `use_tls` 不再被识别
  - 数据库变更：`ALTER TABLE smtp_config ADD COLUMN encryption VARCHAR(16) DEFAULT 'tls'`，已有数据自动迁移（`use_tls=1` → `encryption='tls'`，`use_tls=0` → `encryption='none'`）
  - 关联任务：SMTP STARTTLS 支持
  - 备注：`subscribers.py` 和 `mail/api.py` 中所有 `send_email(use_tls=...)` 调用已同步改为 `encryption=`

---

## 2026-06-25 (修复)

### 修复
- ⚠️ **Celery Worker Pod OOMKilled 修复**：Worker 容器因 OOMKilled (exitCode: 137) 反复重启，共重启 177 次
  - 影响文件：`backend/src/scheduler/celery_app.py`, K8s Deployment `cronmail-backend-worker`
  - 根因1：`celery_app.py` 未调用 `autodiscover_tasks`，导致 `[tasks]` 列表为空
  - 根因2：Celery 默认 concurrency 为 CPU 核数（gpu-01 节点 192 核），prefork 192 个子进程远超 384Mi 内存限制
  - 修复方式：
    1. `celery_app.py` 添加 `celery_app.autodiscover_tasks(['src.scheduler'])` 自动发现任务
    2. `celery_app.py` 添加 `worker_concurrency` 配置，默认 4，通过 `CELERY_WORKER_CONCURRENCY` 环境变量覆盖
    3. `celery_app.py` 添加 `worker_prefetch_multiplier=1` 和 `worker_max_tasks_per_child=100` 避免内存泄漏
    4. K8s Deployment 设置 `CELERY_WORKER_CONCURRENCY=2` 环境变量，限制 Worker 进程数
  - 关联任务：Celery Worker 部署修复

---

## 2026-06-24 (修复)

### 修复
- **PUT /api/rentals/{id} 传入 data_disks 返回 500**：`model_dump(exclude_unset=True)` 已将 Pydantic 模型转为 dict，`update_rental` 中再次对 dict 调用 `.model_dump()` 导致 AttributeError
  - 影响文件：`backend/src/rental/services.py`
  - 修复方式：增加 `isinstance(disk, dict)` 检查，dict 直接使用，Pydantic 对象才调 `model_dump()`
  - 关联任务：BUG-001
  - 备注：contacts 路径的 `_replace_rental_contacts` 已正确处理 dict 和对象两种类型，无需修改

---

## 2026-06-24

### 新增
- **Dockerfile.backend**：后端容器镜像构建文件
  - 影响文件：`Dockerfile.backend`
  - 基于 `python:3.12-slim`，安装 gcc 编译工具链
  - 复制 `backend/requirements.txt` 并 pip install
  - 复制 `backend/` 全部代码
  - 默认 CMD 启动 `uvicorn main:app --host 0.0.0.0 --port 8000`
  - 同一镜像支持通过 K8s command 覆盖启动 Celery Worker/Beat
  - 关联任务：容器化与 K8s 部署

- **K8s 部署 YAML**：完整的 Kubernetes 部署清单
  - 影响文件：`k8s/namespace.yaml`, `k8s/configmap.yaml`, `k8s/secret.yaml`, `k8s/backend-api.yaml`, `k8s/backend-worker.yaml`, `k8s/backend-beat.yaml`, `k8s/ingress.yaml`
  - namespace: `cronmail`
  - ConfigMap: 非敏感配置（DATABASE_URL, CELERY_BROKER_URL, DEBUG 等）
  - Secret: 敏感配置（MAIL_ENCRYPTION_KEY, SMTP 密码等）
  - backend-api: Deployment(replicas:2) + Service(ClusterIP:8000)，含 HTTP 健康检查
  - backend-worker: Deployment(replicas:1)，Celery Worker，含进程存活检查
  - backend-beat: Deployment(replicas:1，单副本），Celery Beat，含进程存活检查
  - ingress: `/api/*` → backend Service，`/*` → frontend Service
  - 关联任务：容器化与 K8s 部署（ADR-007）

---

## 2025-07-17 (追加 - 第三批)

### 新增
- **Celery 定时任务**：Celery Beat 定时扫描到期/临期记录
  - 影响文件：`backend/src/scheduler/celery_app.py`, `backend/src/scheduler/tasks.py`
  - `check_expiring_rentals`：每天 08:00 扫描 end_date 在未来 3 天内的记录，更新 status 为 expiring，发布 `rental.expiring` 事件
  - `check_expired_rentals`：每天 02:00 扫描 end_date 已过期的记录，发布 `rental.expired` 事件发回收邮件，更新 status 为 reclaimed
  - Celery task 内自行创建 db session，不依赖 FastAPI 依赖注入
  - 单条记录失败不影响后续记录（try/except 包裹）
  - 关联任务：Celery 定时任务 + 事件订阅者

- **blinker 事件系统**：租赁事件定义与订阅
  - 影响文件：`backend/src/rental/events.py`
  - 4 个信号：`rental.provisioned`、`rental.expiring`、`rental.expired`、`rental.reclaimed`
  - 使用 blinker 库实现进程内发布/订阅

- **邮件事件订阅者**：监听租赁事件自动发送邮件
  - 影响文件：`backend/src/mail/subscribers.py`
  - `on_rental_provisioned` → provision 模板 → 开通邮件
  - `on_rental_expiring` → expiry_warning 模板 → 临期提醒邮件
  - `on_rental_expired` → reclaim 模板 → 回收邮件
  - `on_rental_reclaimed` → 记录日志
  - 订阅者内部自行创建 db session，复用模板渲染和邮件发送逻辑
  - 关联任务：同上

### 修改
- ⚠️ **rental API 邮件发送端点改为事件驱动**：`send-provision-email`、`send-expiry-reminder`、`reclaim` 三个接口不再直接调用邮件发送，改为发布 blinker 事件，由订阅者完成邮件发送
  - 影响文件：`backend/src/rental/api.py`
  - 响应格式不变（`SendEmailResponse` / `ReclaimResponse`）
  - blinker 信号是同步的，API 响应会等待邮件发送完成
  - 关联任务：同上

- **main.py 启动时注册事件订阅者**：`import src.mail.subscribers` 触发 blinker 连接
  - 影响文件：`backend/main.py`

---

## 2025-07-17 (追加 - 第二批)

### 新增
- **RentalRecord API**：租赁记录 CRUD + 邮件发送（开通/临期提醒/回收）
  - 影响文件：`backend/src/rental/api.py`, `backend/src/rental/services.py`, `backend/src/rental/schemas.py`
  - 路由前缀：`/api/rentals`
  - 支持列表过滤（`?customer_id=&status=&search=`）、分页
  - 创建/更新时 root_password 明文传入、Fernet 加密存储、详情解密返回
  - contacts 关联通过 rental_contact 中间表管理，支持全量替换
  - send-provision-email：手动发送开通邮件，Jinja2 渲染模板 → SMTP 发送 → 写 EmailLog
  - send-expiry-reminder：手动发送临期提醒，模板变量含 `days_until_expiry`
  - reclaim：手动回收（发回收邮件 + status→reclaimed）
  - 关联任务：租赁记录 + 邮件模板 + 邮件发送 + 发送日志 API

- **EmailTemplate API**：邮件模板 CRUD + 实时预览
  - 影响文件：`backend/src/template/api.py`, `backend/src/template/services.py`, `backend/src/template/schemas.py`
  - 路由前缀：`/api/templates`
  - 创建模板支持 trigger_type 枚举（provision/expiry_warning/reclaim）
  - PUT 更新时 version 自动 +1
  - POST /preview：Jinja2 SandboxedEnvironment 渲染，不依赖数据库
  - 关联任务：同上

- **邮件发送服务**：SMTP 邮件发送 + Jinja2 模板渲染
  - 影响文件：`backend/src/mail/sender.py`, `backend/src/mail/renderer.py`
  - `send_email()`：基于 smtplib + email.mime 构建 MIME 邮件
  - `render_template()`：Jinja2 SandboxedEnvironment 安全渲染
  - 关联任务：同上

- **EmailLog API**：邮件发送日志查询 + 重发
  - 影响文件：`backend/src/mail/api.py`, `backend/src/mail/services.py`, `backend/src/mail/schemas.py`
  - 路由前缀：`/api/logs`
  - 列表支持过滤（`?rental_id=&trigger_type=&status=`）
  - GET /{id} 返回完整邮件正文
  - POST /{id}/resend：重新渲染模板 → SMTP 发送 → 更新日志状态
  - 关联任务：同上

- **路由注册**：Rental、Template、Log 路由注册到 main.py
  - 影响文件：`backend/main.py`

### 修复
- Jinja2 `SandboxedEnvironment` 从 `jinja2.sandbox` 导入（非 `jinja2` 顶层）
- rental_contact 中间表查询改用原生 SQL + `text()` 避免 ORM Row 类型复杂性
- `_replace_rental_contacts` 兼容 Pydantic 对象和 dict 两种输入类型

---

## 2025-07-17 (追加)

### 新增
- **Customer API**：客户 CRUD 接口（列表/创建/详情/更新/软删除）
  - 影响文件：`backend/src/customer/api.py`, `backend/src/customer/services.py`, `backend/src/customer/schemas.py`
  - 路由前缀：`/api/customers`
  - 支持模糊搜索（`?search=`）、分页（`?page=&page_size=`）
  - code 唯一性校验，软删除（status=inactive）
  - 详情接口返回联系人数量

- **Contact API**：联系人 CRUD 接口（列表/创建/详情/更新/软删除）
  - 影响文件：`backend/src/customer/api.py`, `backend/src/customer/services.py`, `backend/src/customer/schemas.py`
  - 路由前缀：`/api/contacts`
  - 支持按类型查询：`type=customer`（需 customer_id）、`type=colleague`（customer_id IS NULL）
  - 软删除（is_active=false）

- **SmtpConfig API**：SMTP 配置管理 + 测试连接
  - 影响文件：`backend/src/system/api.py`, `backend/src/system/services.py`, `backend/src/system/schemas.py`
  - 路由前缀：`/api/system/smtp`
  - PUT 接口：upsert 逻辑（不存在则创建，存在则更新），密码明文传入加密存储
  - GET 接口：不返回密码
  - POST /test：使用 smtplib 发送测试邮件，返回 success + message

- **路由注册**：Customer、Contact、System 路由注册到 main.py
  - 影响文件：`backend/main.py`

- **UUIDColumn 兼容层**：MySQL CHAR(36) / SQLite String(36) 自动适配
  - 影响文件：`backend/src/core/database.py`

- **模型兼容更新**：所有模型改用 UUIDColumn 替代硬编码的 MySQL CHAR
  - 影响文件：`backend/src/customer/models.py`, `backend/src/rental/models.py`, `backend/src/template/models.py`, `backend/src/mail/models.py`, `backend/src/system/models.py`

## 2025-07-17

### 新增
- **项目脚手架搭建**：创建 FastAPI 后端项目骨架，包含完整目录结构
  - 影响文件：`backend/main.py`, `backend/requirements.txt`, `backend/.env`, `backend/alembic.ini`
  - 关联任务：后端脚手架 + 全部数据模型 + 核心基础设施
  - 备注：项目根目录 `backend/`，采用 FastAPI + SQLAlchemy 2.0 + MySQL 8.0

- **核心基础设施**：配置管理、数据库引擎、加密工具
  - `backend/src/core/config.py`：pydantic-settings 环境变量读取（DATABASE_URL, MAIL_ENCRYPTION_KEY 等）
  - `backend/src/core/database.py`：SQLAlchemy engine + SessionLocal + get_db 依赖注入
  - `backend/src/core/crypto.py`：基于 cryptography.fernet 的 encrypt_password / decrypt_password
  - 关联任务：后端脚手架 + 全部数据模型 + 核心基础设施

- **全部数据模型**：6 个模块共 7 张表
  - `backend/src/customer/models.py`：Customer（客户表）、Contact（联系人表）
  - `backend/src/rental/models.py`：RentalRecord（租赁记录表）、rental_contact（中间表）
  - `backend/src/template/models.py`：EmailTemplate（邮件模板表）
  - `backend/src/mail/models.py`：EmailLog（邮件发送日志表）
  - `backend/src/system/models.py`：SmtpConfig（SMTP 配置表）
  - `backend/src/scheduler/models.py`：占位，暂无模型
  - 所有模型使用 UUID 主键（CHAR(36)），完整的外键和 relationship 定义
  - 关联任务：后端脚手架 + 全部数据模型 + 核心基础设施

- **健康检查端点**：`GET /api/health` 返回 `{"status": "ok"}`
  - 影响文件：`backend/main.py`
  - CORS 中间件已配置（开发阶段允许所有来源）
  - 数据库连接失败不阻止服务启动
  - 关联任务：后端脚手架 + 全部数据模型 + 核心基础设施

- **Alembic 迁移配置**：`backend/alembic.ini` + `backend/alembic/env.py` + `backend/alembic/script.py.mako`
  - 影响文件：`backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
  - 关联任务：后端脚手架 + 全部数据模型 + 核心基础设施

---

## 2026-07-17 (部署) — 后端镜像重新构建部署 (第三次)

### 部署
- **后端镜像构建 + K8s 滚动更新**
  - 影响文件：`Dockerfile.backend`
  - 变更内容：
    1. Docker 构建 `harbor.xhwltech.com/xhcloud/cronmail-backend:latest`（镜像 ID: `24d322b7f47d`）
    2. 推送镜像到 Harbor（digest: `sha256:7ac0cc0ae548b4bcef2dc4ea411934a5e9216149a9abc6bb71b19cb8d5dba45c`）
    3. 滚动重启 `cronmail-backend-api` Deployment（`kubectl rollout restart`）
    4. 部署成功，`cronmail-backend-api` successfully rolled out
  - 构建代理：`http://192.168.180.251:7890`
  - 关联任务：后端部署

---

## 2026-07-17 (部署) — 后端镜像重新构建部署 (第三次)

### 部署
- **后端镜像构建 + K8s 滚动更新**
  - 影响文件：`Dockerfile.backend`
  - 变更内容：
    1. Docker 构建 `harbor.xhwltech.com/xhcloud/cronmail-backend:latest`（镜像 ID: `da3897757668`）
    2. 推送镜像到 Harbor（digest: `sha256:2a8f2ada47443e112bdc87f066a403efe2341da87f5701ce5b4d40640f99b8a6`）
    3. 滚动重启 `cronmail-backend-api` Deployment（`kubectl rollout restart`）
    4. 部署成功，`cronmail-backend-api` successfully rolled out
  - 构建代理：`http://192.168.180.251:7890`
  - 关联任务：后端部署

---

## 2026-07-17 (部署) — 后端镜像重新构建部署 (第二次)

### 部署
- **后端镜像构建 + K8s 滚动更新**
  - 影响文件：`Dockerfile.backend`
  - 变更内容：
    1. Docker 构建 `harbor.xhwltech.com/xhcloud/cronmail-backend:latest`（镜像 ID: `4da85e1497fb`）
    2. 推送镜像到 Harbor（digest: `sha256:3d5a56b2fa181ef6ac3d6b0b76fd3a0f5325ed58a15d935310016b9fa8e735e8`）
    3. 滚动重启 `cronmail-backend-api` Deployment（`kubectl rollout restart`）
    4. 新 Pod `cronmail-backend-api-65488f7694-kvhcc` 就绪，1/1 Running
    5. 健康检查 `GET /api/health` 200 OK，应用环境 PRODUCTION
  - 构建代理：`http://192.168.180.251:7890`
  - 关联任务：后端部署
