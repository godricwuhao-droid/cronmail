# 数据库文档

## 库划分（ADR-019 平台拆分）

| 库 | 属主平台 | 说明 |
|----|---------|------|
| `asset_ops` | 资产运营管理平台（platform-asset-ops 分支） | 独立库，2026-10-07 创建（utf8mb4），含 17 张资产侧表 |
| `cronmail` | 原 CronMail 全功能平台（main 分支） | 原库，保留全部 25 张表（含项目侧 project_* 表），只读参考 |

### 属主约定

- **资产侧表**（`asset_ops` 库，17 张）：`customer`、`contact`、`rental_record`、`rental_contact`、`contract`、`contract_rental`、`contract_contact`、`change_log`、`email_template`、`email_log`、`smtp_config`、`dingtalk_config`、`system_config`、`attachment_category`、`attachment_item`、`attachment`、`attachment_status`
- **项目侧表**（仅存在于 `cronmail` 库，不迁入 `asset_ops`）：`project_type`、`project_contract`、`project_service_line`、`project_contract_payment`，以及卫星/算力服务侧 `satellite_data_contract`、`compute_service_contract`、`contract_service_line`
- 数据流向：`cronmail` → `asset_ops` 单向复制（`backend/scripts/migrate_to_asset_ops.py`，幂等可重跑）；`cronmail` 库在任何迁移操作中保持只读
- 过滤约定：`attachment` / `attachment_status` / `attachment_category` 仅复制 `contract_type='compute_leasing'` 行；`attachment_item` 仅复制 compute_leasing 分类子项；`system_config` 排除 `llm_*` 与 project 相关键

## asset_ops 库表结构（17 表，2026-10-07 建表 + 迁移）

建表方式：应用模型 `Base.metadata.create_all`（与 `backend/src/*/models.py` 定义一致）。

### customer（客户）
- PK: `id` CHAR(36)
- 字段: name, code, status, business_types(JSON), created_at, updated_at

### contact（联系人）
- PK: `id`
- 字段: customer_id(FK→customer), name, email, phone, department, is_active, created_at, updated_at

### rental_record（设备/租赁记录）
- PK: `id`
- 字段: customer_id(FK→customer), machine_model, cpu_model, memory_gb, gpu_info, system_disk, data_disks(JSON), os_version, bandwidth_mbps, rack_location, private_ip, public_ips(JSON), ssh_port, root_username, root_password_enc, billing_model, start_date, end_date, auto_renew, status, remark, created_at, updated_at

### rental_contact（设备-联系人中间表）
- PK: (rental_id, contact_id)
- 字段: rental_id(FK→rental_record), contact_id(FK→contact), recipient_type

### contract（算力租赁合同）
- PK: `id`
- 字段: customer_id(FK→customer), name, contract_no, start_date, end_date, billing_model, status, remark, amount(DECIMAL(12,2)), history_rental_ids(JSON), renewed_from_id(FK→contract，自引用，续期来源), sort_order, created_at, updated_at

### contract_rental（合同-设备中间表）
- PK: (contract_id, rental_id)
- 字段: contract_id(FK→contract), rental_id(FK→rental_record), created_at

### contract_contact（合同-联系人中间表）
- PK: (contract_id, contact_id, recipient_type)
- 字段: contract_id(FK→contract), contact_id(FK→contact), recipient_type(to/cc)

### change_log（变更记录）
- PK: `id`
- 字段: target_type, target_id, content, created_at

### email_template（邮件模板）
- PK: `id`
- 字段: name, trigger_type, subject_tpl, body_html, variables_desc(JSON), signature_html, is_active, version, created_at, updated_at

### email_log（邮件发送日志）
- PK: `id`
- 字段: rental_id(FK→rental_record), template_id(FK→email_template), trigger_type, recipient, recipient_type, subject, body, status, error_msg, sent_at, created_at, extra_data(JSON)

### smtp_config（SMTP 配置）
- PK: `id`
- 字段: host, port, username, password_enc, sender_name, sender_email, encryption, use_tls(废弃), created_at, updated_at

### dingtalk_config（钉钉机器人配置）
- PK: `id`
- 字段: webhook_url, secret, is_active, created_at, updated_at

### system_config（系统配置，key-value）
- PK: `id`；`key` 唯一
- 字段: key, value, description, updated_at
- 迁移后仅含资产侧键：check-expired-rentals / check-expiring-rentals / check-reclaim-expired / expiry_warning_days / reclaim_time（llm_* 键未迁入）

### attachment_category（附件分类）
- PK: `id`
- 字段: contract_type（仅 compute_leasing）, name, code, sort_order, is_active, created_at
- 注意：asset_ops 中无 `project_type` 列（源库 cronmail 该表残留此列，迁移时已剔除）

### attachment_item（附件子项）
- PK: `id`
- 字段: category_id(FK→attachment_category), name, description, expected_type, sort_order, is_active, created_at

### attachment（附件文件）
- PK: `id`
- 字段: contract_type（仅 compute_leasing）, contract_id, item_id(FK→attachment_item), filename, file_path, file_size, mime_type, uploaded_at

### attachment_status（附件子项确认状态）
- PK: `id`
- 字段: contract_type（仅 compute_leasing）, contract_id, item_id(FK→attachment_item), file_count, confirmed, confirmed_at, created_at

## 迁移记录

- 2026-10-07：`asset_ops` 库创建（`CREATE DATABASE ... CHARACTER SET utf8mb4`），17 表由 `Base.metadata.create_all` 建立
- 2026-10-07：执行 `backend/scripts/migrate_to_asset_ops.py`（source=cronmail，target=asset_ops），逐表行数与 dry-run 计划一致；逐行 MD5 哈希全量比对 17 表全部 MATCH；抽样核对（合同金额/邮件日志/客户）通过；`asset_ops` 无 project_* 数据；`cronmail` 库未受影响
- 迁移脚本特性：幂等（DELETE 过滤范围内 + INSERT）、源库只读、迁移期间临时关闭目标库外键检查（contract 自引用外键）、原生 SELECT/INSERT 保证 JSON 列存储形式保真
