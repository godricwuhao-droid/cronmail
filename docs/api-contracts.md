# CronMail API 接口契约

## 通用约定

- Base URL: `/api`
- Content-Type: `application/json`
- 日期格式: `YYYY-MM-DD`
- 日期时间格式: ISO 8601 (`2026-06-24T18:00:00Z`)
- 列表接口分页: `?page=1&page_size=20`
- 列表接口响应包裹: `{"items": [...], "total": 100, "page": 1, "page_size": 20}`

---

## 1. 客户管理 (Customer)

### GET /api/customers

列表，支持以下查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `search` | string | 否 | 按客户名称模糊搜索 |
| `business_type` | string | 否 | 业务类型过滤，可选值：`算力租赁` / `卫星数据` / `算力服务`；命中 `business_types` JSON 数组中包含该值的客户；非法值被忽略 |
| `status` | string | 否 | 状态过滤：`active` / `inactive` |
| `page` | int | 否 | 页码，默认 1 |
| `page_size` | int | 否 | 每页条数，默认 20，最大 100 |

**响应**:
```json
{
  "items": [
    {"id": "uuid", "name": "某科技公司", "code": "KEJI", "status": "active", "business_types": ["算力租赁"], "created_at": "..."}
  ],
  "total": 1, "page": 1, "page_size": 20
}
```

**业务类型过滤示例**：

合同管理按业务类型划分三类：
- 算力租赁 → `?business_type=算力租赁`
- 卫星数据 → `?business_type=卫星数据`
- 算力服务 → `?business_type=算力服务`

实现说明：MySQL 通过 `JSON_CONTAINS(business_types, '"算力租赁"') > 0` 进行数组包含匹配，单一字段精确匹配，不做模糊。

### POST /api/customers

**请求**:
```json
{"name": "某科技公司", "code": "KEJI"}
```

### GET /api/customers/{id}

返回客户详情 + 联系人数量。

### PUT /api/customers/{id}

**请求**:
```json
{"name": "...", "code": "...", "status": "active"}
```

### DELETE /api/customers/{id}

---

## 2. 联系人管理 (Contact)

### GET /api/contacts?customer_id={id}&type={customer|colleague}

- `customer_id` 为空时返回内部同事（customer_id IS NULL）
- `customer_id` 有值时返回该客户下的联系人

**响应**:
```json
{
  "items": [
    {"id": "uuid", "customer_id": "uuid|null", "name": "张三", "email": "zhang@xx.com", "phone": "138...", "department": "技术部", "is_active": true}
  ],
  "total": 1
}
```

### POST /api/contacts

**请求**:
```json
{"customer_id": "uuid|null", "name": "张三", "email": "zhang@xx.com", "phone": "138...", "department": "技术部"}
```

### PUT /api/contacts/{id}

### DELETE /api/contacts/{id}

---

## 3. 租赁记录 (RentalRecord)

### GET /api/rentals

查询参数: `?customer_id=&status=&search=&page=&page_size=`

status 枚举: `provisioned | expiring | expired | reclaimed`

**响应**:
```json
{
  "items": [{
    "id": "uuid",
    "customer": {"id": "uuid", "name": "某科技公司"},
    "machine_model": "Dell R740",
    "private_ip": "10.0.0.1",
    "start_date": "2026-06-01",
    "end_date": "2026-12-01",
    "status": "provisioned",
    "created_at": "..."
  }],
  "total": 1, "page": 1, "page_size": 20
}
```

### POST /api/rentals

创建租赁记录（仅保存，不发送邮件）。

**请求**:
```json
{
  "customer_id": "uuid",
  "contacts": [
    {"contact_id": "uuid", "recipient_type": "to"},
    {"contact_id": "uuid", "recipient_type": "cc"}
  ],
  "machine_model": "Dell R740",
  "cpu_model": "2×Intel Xeon Gold 6248R 48C",
  "memory_gb": 256,
  "gpu_info": "8×NVIDIA A100 80GB",
  "system_disk_gb": 480,
  "data_disks": [{"size_gb": 2000, "type": "NVMe SSD"}, {"size_gb": 4000, "type": "SATA SSD"}],
  "os_version": "Ubuntu 22.04 LTS",
  "bandwidth_mbps": 1000,
  "rack_location": "A01-05-U12",
  "private_ip": "10.0.0.1",
  "public_ips": ["1.2.3.4"],
  "ssh_port": 22,
  "root_username": "root",
  "root_password": "TempPass123!",
  "billing_model": "monthly",
  "start_date": "2026-06-01",
  "end_date": "2026-12-01",
  "auto_renew": false,
  "remark": ""
}
```

### GET /api/rentals/{id}

返回完整租赁记录信息（含解密后的密码，仅用于内部管理展示）。

**响应**: 同创建请求体 + `contacts: [{contact_id, name, email, recipient_type}]` + `email_logs: [...]`

### PUT /api/rentals/{id}

同 POST 请求结构，全量更新。

### DELETE /api/rentals/{id}

### POST /api/rentals/{id}/send-provision-email

手动发送开通邮件。后端自动查出同一客户、同一 `start_date` 的所有 `provisioned` 记录，合并为一封邮件发送。

**请求**（可选）:
```json
{}
```

**响应**:
```json
{"email_log_ids": ["uuid", "uuid"], "recipient_count": 2}
```

### POST /api/rentals/{id}/send-expiry-reminder

手动发送临期提醒。后端自动查出同一客户、未来 3 天内到期的所有 `provisioned`/`expiring` 记录，合并为一封邮件发送，并批量更新状态为 `expiring`。

**响应**:
```json
{"email_log_ids": ["uuid"], "recipient_count": 1}
```

### POST /api/rentals/{id}/reclaim

手动回收。后端自动查出同一客户、同一 `end_date` 的所有 `provisioned`/`expiring` 记录，合并发送回收邮件，并批量更新状态为 `reclaimed`。

**响应**:
```json
{
  "success": true,
  "message": "已发送回收邮件（合并 3 台设备）并更新状态为 reclaimed",
  "email_log_ids": ["uuid", "uuid", "uuid"],
  "recipient_count": 2
}
```

---

## 4. 邮件模板 (EmailTemplate)

### 模板颜色约定

不同触发类型的邮件模板建议使用以下主色调，以保持视觉一致性：

| 触发类型 | 说明 | 建议主色 | 色值 |
|----------|------|----------|------|
| `provision` | 资源开通通知 | 绿色系 | `#67C23A` |
| `expiry_warning` | 临期提醒 | 黄色系 | `#E6A23C` |
| `reclaim` | 回收通知 | 红色系 | `#F56C6C` |

> 前端模板编辑页不限制用户自定义颜色，用户可在 HTML 中自由编写样式。以上仅为推荐约定。

---

### GET /api/templates

**响应**:
```json
{
  "items": [{
    "id": "uuid",
    "name": "资源开通通知",
    "trigger_type": "provision",
    "subject_tpl": "您的服务器 {{ machine_model }} 已开通",
    "is_active": true,
    "version": 1,
    "updated_at": "..."
  }]
}
```

### POST /api/templates

**请求**:
```json
{
  "name": "资源开通通知",
  "trigger_type": "provision",
  "subject_tpl": "【CronMail】您的服务器 {{ machine_model }} 已开通",
  "body_html": "<h2>尊敬的客户：</h2><p>您租赁的 {{ machine_model }} 已就绪。</p><table>...</table>",
  "variables_desc": {"machine_model": "机器型号", "private_ip": "内网IP"},
  "is_active": true
}
```

### GET /api/templates/{id}

### PUT /api/templates/{id}

更新时 version 自动 +1。

### DELETE /api/templates/{id}

### POST /api/templates/preview

实时预览（不保存）。

**请求**:
```json
{
  "subject_tpl": "{{ machine_model }} 已开通",
  "body_html": "<p>IP: {{ private_ip }}</p>",
  "sample_data": {
    "machine_model": "Dell R740",
    "private_ip": "10.0.0.1",
    "public_ips": ["1.2.3.4"],
    "cpu_model": "2×Intel Xeon Gold 6248R",
    "memory_gb": 256,
    "gpu_info": "8×NVIDIA A100 80GB",
    "system_disk_gb": 480,
    "data_disks": [{"size_gb": 2000, "type": "NVMe SSD"}],
    "os_version": "Ubuntu 22.04 LTS",
    "bandwidth_mbps": 1000,
    "rack_location": "A01-05-U12",
    "ssh_port": 22,
    "root_username": "root",
    "root_password": "TempPass123!",
    "start_date": "2026-06-01",
    "end_date": "2026-12-01",
    "billing_model": "monthly",
    "customer_name": "某科技公司"
  }
}
```

**响应**:
```json
{
  "subject_rendered": "Dell R740 已开通",
  "body_rendered": "<p>IP: 10.0.0.1</p>"
}
```

---

## 5. 发送日志 (EmailLog)

### GET /api/logs

查询参数: `?rental_id=&trigger_type=&status=&page=&page_size=`

trigger_type: `provision | expiry_warning | reclaim`

status: `sent | failed`

**响应**:
```json
{
  "items": [{
    "id": "uuid",
    "rental_id": "uuid",
    "template_id": "uuid",
    "trigger_type": "provision",
    "recipient": "zhang@xx.com",
    "recipient_type": "to",
    "subject": "您的服务器 Dell R740 已开通",
    "status": "sent",
    "error_msg": null,
    "sent_at": "2026-06-24T10:00:00Z"
  }],
  "total": 1
}
```

### GET /api/logs/{id}

返回完整邮件正文 `body`。

### POST /api/logs/{id}/resend

重发失败的邮件。

---

## 6. 系统配置 (SystemConfig)

### GET /api/system/smtp

**响应**:
```json
{
  "host": "smtp.example.com",
  "port": 465,
  "username": "noreply@example.com",
  "sender_name": "CronMail",
  "sender_email": "noreply@example.com",
  "encryption": "tls"
}
```
不返回密码。
encryption 枚举: `tls` (SSL/TLS, 端口 465) | `starttls` (STARTTLS, 端口 587) | `none` (无加密, 端口 25)

### PUT /api/system/smtp

**请求**:
```json
{
  "host": "smtp.example.com",
  "port": 465,
  "username": "noreply@example.com",
  "password": "new_password",
  "sender_name": "CronMail",
  "sender_email": "noreply@example.com",
  "encryption": "tls"
}
```
encryption 枚举: `tls` | `starttls` | `none`

### POST /api/system/smtp/test

测试 SMTP 连接。用配置的账号发送一封测试邮件到指定地址。

**请求**:
```json
{"test_email": "admin@company.com"}
```

**响应**:
```json
{"success": true, "message": "测试邮件已发送"}
```

---

## 8. 卫星数据合同 (SatelliteDataContract)

Base: `/api/satellite-data-contracts`

### 8.1 合同 CRUD

### GET /api/satellite-data-contracts

查询参数: `?customer_id=&search=&page=&page_size=`

**响应** (ADR-013 新增字段标注 🆕):
```json
{
  "items": [{
    "id": "uuid",
    "customer_id": "uuid",
    "customer_name": "某科技公司",
    "name": "卫星数据合同-2026",
    "contract_no": "SAT-2026-001",
    "contract_type": "数据采购",           // 🆕 自由文本
    "project_name": "某某卫星项目",        // 🆕
    "party_a_name": "某科技公司",          // 🆕
    "party_b_name": "我方公司",            // 🆕
    "start_date": "2026-07-01",           // 🆕
    "end_date": "2027-06-30",             // 🆕
    "amount": "800000.00",                // 🆕
    "contract_content": "合同主要内容描述",  // 🆕 Text
    "delivery_requirements": "交付标准要求", // 🆕 Text
    "process_records": "过程记录",          // 🆕 Text
    "remark": null,
    "created_at": "...",
    "updated_at": "..."
  }],
  "total": 1, "page": 1, "page_size": 20
}
```

### POST /api/satellite-data-contracts

**请求**:
```json
{
  "customer_id": "uuid",
  "name": "卫星数据合同-2026",
  "contract_no": "SAT-2026-001",
  "contract_type": "数据采购",           // 🆕 Optional, 自由文本
  "project_name": "某某卫星项目",        // 🆕 Optional
  "party_a_name": "某科技公司",          // 🆕 Optional
  "party_b_name": "我方公司",            // 🆕 Optional
  "start_date": "2026-07-01",           // 🆕 Optional
  "end_date": "2027-06-30",             // 🆕 Optional
  "amount": "800000.00",                // 🆕 Optional
  "contract_content": "合同主要内容描述",  // 🆕 Optional Text
  "delivery_requirements": "交付标准要求", // 🆕 Optional Text
  "process_records": "过程记录",          // 🆕 Optional Text
  "remark": null
}
```

### GET /api/satellite-data-contracts/{id}

响应同列表项结构。

### PUT /api/satellite-data-contracts/{id}

请求体同 POST，所有字段均为 Optional。

### DELETE /api/satellite-data-contracts/{id}

---

## 9. 算力服务合同 (ComputeServiceContract)

Base: `/api/compute-service-contracts`

### 9.1 合同 CRUD

### GET /api/compute-service-contracts

查询参数: `?customer_id=&search=&page=&page_size=`

**响应** (ADR-013 新增字段标注 🆕):
```json
{
  "items": [{
    "id": "uuid",
    "customer_id": "uuid",
    "customer_name": "某科技公司",
    "name": "算力服务合同-2026",
    "contract_no": "FW-2026-001",
    "contract_type": "sales",
    "party_a_name": "某科技公司",
    "party_b_name": "我方公司",
    "amount": "1500000.00",
    "start_date": "2026-07-01",
    "end_date": "2027-06-30",
    "related_contract_id": null,
    "project_name": "某某算力项目",        // 🆕
    "contract_content": "合同主要内容描述",  // 🆕 Text
    "delivery_requirements": "交付标准要求", // 🆕 Text
    "process_records": "过程记录",          // 🆕 Text
    "remark": null,
    "service_lines_count": 5,
    "created_at": "...",
    "updated_at": "..."
  }],
  "total": 1, "page": 1, "page_size": 20
}
```

### POST /api/compute-service-contracts

**请求**:
```json
{
  "customer_id": "uuid",
  "name": "算力服务合同-2026",
  "contract_no": "FW-2026-001",
  "contract_type": "sales",
  "party_a_name": "某科技公司",
  "party_b_name": "我方公司",
  "amount": null,
  "start_date": "2026-07-01",
  "end_date": "2027-06-30",
  "related_contract_id": null,
  "project_name": "某某算力项目",        // 🆕 Optional
  "contract_content": "合同主要内容描述",  // 🆕 Optional Text
  "delivery_requirements": "交付标准要求", // 🆕 Optional Text
  "process_records": "过程记录",          // 🆕 Optional Text
  "remark": null,
  "service_lines": [
    {
      "category": "算力服务",
      "item_name": "通用CPU容器实例",
      "specification": {"vcpu": 10, "frequency": "2.5GHz", "memory": "32GB DDR4", "storage": "500GB NVMe SSD"},
      "vcpu_count": 10,
      "memory_gb": 32,
      "storage_gb": 500,
      "unit": "个/月",
      "quantity": 5,
      "period_months": 12,
      "unit_price": 5000,
      "sort_order": 0
    }
  ]
}
```

- `contract_type`: `"sales"` | `"procurement"`，必填，默认 `"sales"`
- `amount`: 可选，不填则由 service_lines.total_price 自动汇总
- `service_lines`: 可选，创建后可单独管理
- `related_contract_id`: 可选，关联背靠背合同
- 🆕 `project_name`/`contract_content`/`delivery_requirements`/`process_records`: 均为 Optional，手动填写

### GET /api/compute-service-contracts/{id}

响应含完整 service_lines 和关联合同信息，以及 🆕 四个新增字段：

**响应**:
```json
{
  "id": "uuid",
  "customer_id": "uuid",
  "customer_name": "某科技公司",
  "name": "...",
  "contract_no": "...",
  "contract_type": "sales",
  "party_a_name": "...",
  "party_b_name": "...",
  "amount": "1500000.00",
  "amount_auto_calc": "1500000.00",
  "start_date": "2026-07-01",
  "end_date": "2027-06-30",
  "related_contract_id": "uuid-of-procurement",
  "related_contract": {
    "id": "uuid-of-procurement",
    "name": "采购合同-英伟达",
    "contract_no": "CG-2026-001",
    "contract_type": "procurement",
    "amount": "1200000.00"
  },
  "project_name": "某某算力项目",        // 🆕
  "contract_content": "合同主要内容描述",  // 🆕
  "delivery_requirements": "交付标准要求", // 🆕
  "process_records": "过程记录",          // 🆕
  "remark": null,
  "service_lines": [...],
  "created_at": "...",
  "updated_at": "..."
}
```

- `amount_auto_calc`: 由 service_lines 自动计算的总金额（SUM of total_price），前端用于与 `amount` 对比提示
- `related_contract`: **双向查询**——无论关联从哪端建立，两个合同详情都能看到对方

### PUT /api/compute-service-contracts/{id}

请求体同 POST。更新时 `service_lines` 如果传入则**全量替换**（先删后插）。

### DELETE /api/compute-service-contracts/{id}

级联删除关联的 service_lines。

---

### 9.2 服务行 CRUD

### GET /api/compute-service-contracts/{contract_id}/service-lines

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "category": "算力服务",
      "item_name": "通用CPU容器实例",
      "specification": {...},
      "vcpu_count": 10,
      "memory_gb": 32,
      "storage_gb": 500,
      "unit": "个/月",
      "quantity": 5,
      "period_months": 12,
      "unit_price": 5000,
      "total_price": 300000,
      "sort_order": 0
    }
  ]
}
```

### POST /api/compute-service-contracts/{contract_id}/service-lines

创建单行服务内容。请求体格式同 service_line 对象（不含 id/total_price，total_price 由后端计算）。

### PUT /api/compute-service-contracts/{contract_id}/service-lines/{line_id}

更新单行。

### DELETE /api/compute-service-contracts/{contract_id}/service-lines/{line_id}

删除单行。

### POST /api/compute-service-contracts/{contract_id}/service-lines/batch

批量保存（全量替换）:

**请求**:
```json
{
  "lines": [
    { "category": "...", "item_name": "...", ... }
  ]
}
```

---

## 错误响应格式

```json
{
  "detail": "错误描述",
  "code": "RENTAL_NOT_FOUND"
}
```

HTTP 状态码:
- 200 成功
- 201 创建成功
- 400 参数校验失败
- 404 资源不存在
- 422 业务逻辑错误（如状态不允许该操作）
- 500 服务器错误
