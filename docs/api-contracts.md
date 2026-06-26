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

列表，支持 `?search=` 模糊搜索名称。

**响应**:
```json
{
  "items": [
    {"id": "uuid", "name": "某科技公司", "code": "KEJI", "status": "active", "created_at": "..."}
  ],
  "total": 1, "page": 1, "page_size": 20
}
```

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
