# CronMail API 接口文档

## 系统接口

### GET /api/health

健康检查端点，用于监控服务是否正常运行。

请求：`GET /api/health`

响应：
```json
{"status":"ok"}
```

HTTP 状态码：200

关键字段：
- `status`（string）：固定值 `"ok"`，表示服务正常运行

---

## 客户管理 (Customer)

### GET /api/customers

获取客户列表，支持模糊搜索和分页。

请求：`GET /api/customers?search=星辰&page=1&page_size=20`

响应：
```json
{
  "items": [
    {
      "id": "f292a694-d59c-4e0e-8f29-3671588d9587",
      "name": "星辰科技",
      "code": "XINGCHEN",
      "status": "active",
      "contact_count": 0,
      "created_at": "2026-06-24T10:56:20.881227",
      "updated_at": "2026-06-24T10:56:20.881232"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

关键字段：
- `items`（array）：客户列表
- `total`（int）：总数
- `page`（int）：当前页码
- `page_size`（int）：每页条数
- `items[].contact_count`（int）：该客户下的活跃联系人数量

查询参数：
- `search`（string，可选）：按名称模糊搜索
- `page`（int，默认 1，最小 1）
- `page_size`（int，默认 20，最小 1，最大 100）

---

### POST /api/customers

创建客户。

请求：`POST /api/customers`
```json
{"name": "某科技公司", "code": "KEJI"}
```

响应（201）：
```json
{
  "id": "6d2f0d9b-ef37-4c3c-bec8-a66884d85dfb",
  "name": "某科技公司",
  "code": "KEJI",
  "status": "active",
  "contact_count": 0,
  "created_at": "2026-06-24T10:56:20.850132",
  "updated_at": "2026-06-24T10:56:20.850140"
}
```

HTTP 状态码：201

关键字段：
- `name`（string，必填，1-128 字符）
- `code`（string，必填，1-64 字符，唯一）

错误：
- 400：`{"detail": "客户编码 'KEJI' 已存在"}` — code 重复

---

### GET /api/customers/{id}

获取客户详情，包含联系人数量。

请求：`GET /api/customers/6d2f0d9b-ef37-4c3c-bec8-a66884d85dfb`

响应：
```json
{
  "id": "6d2f0d9b-ef37-4c3c-bec8-a66884d85dfb",
  "name": "某科技公司(已更名)",
  "code": "KEJI",
  "status": "active",
  "contact_count": 1,
  "created_at": "2026-06-24T10:56:20.850132",
  "updated_at": "2026-06-24T10:56:41.815728"
}
```

HTTP 状态码：200

错误：
- 404：`{"detail": "客户不存在"}`

---

### PUT /api/customers/{id}

更新客户信息。

请求：`PUT /api/customers/{id}`
```json
{"name": "某科技公司(已更名)", "code": "KEJI", "status": "active"}
```

响应：
```json
{
  "id": "6d2f0d9b-ef37-4c3c-bec8-a66884d85dfb",
  "name": "某科技公司(已更名)",
  "code": "KEJI",
  "status": "active",
  "contact_count": 1,
  "created_at": "2026-06-24T10:56:20.850132",
  "updated_at": "2026-06-24T10:56:41.815728"
}
```

HTTP 状态码：200

关键字段：所有字段均为可选，只更新传入的字段。

错误：
- 404：客户不存在
- 400：`{"detail": "客户编码 'XXX' 已存在"}` — 修改 code 时与已有客户冲突

---

### DELETE /api/customers/{id}

软删除客户（将 status 设为 inactive）。

请求：`DELETE /api/customers/{id}`

响应：
```json
{"detail": "客户已删除（状态设为 inactive）"}
```

HTTP 状态码：200

错误：
- 404：`{"detail": "客户不存在"}`

---

## 联系人管理 (Contact)

### GET /api/contacts

获取联系人列表。

请求：
- 查询客户联系人：`GET /api/contacts?type=customer&customer_id={uuid}`
- 查询所有客户联系人：`GET /api/contacts?type=customer&all=true`
- 查询内部同事：`GET /api/contacts?type=colleague`
- 分页：`GET /api/contacts?type=customer&customer_id={uuid}&page=1&page_size=20`

响应（客户联系人）：
```json
{
  "items": [
    {
      "id": "13504cf3-cf6e-4a57-b03b-c78e22a05346",
      "customer_id": "6d2f0d9b-ef37-4c3c-bec8-a66884d85dfb",
      "name": "王五",
      "email": "wang@keji.com",
      "phone": null,
      "department": "采购部",
      "is_active": true,
      "created_at": "2026-06-24T10:56:47.984018",
      "updated_at": "2026-06-24T10:56:47.984021"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

响应（内部同事）：
```json
{
  "items": [
    {
      "id": "f93f53f5-f6c0-4f43-bfd9-8fe5212198b4",
      "customer_id": null,
      "name": "李四",
      "email": "lisi@company.com",
      "phone": "13900002222",
      "department": "运维部",
      "is_active": true,
      "created_at": "2026-06-24T10:56:47.962009",
      "updated_at": "2026-06-24T10:56:47.962014"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

查询参数：
- `type`（string，可选）：`customer` 或 `colleague`
- `customer_id`（string，可选）：当 type=customer 时按客户过滤
- `all`（string，可选）：当 type=customer 且 `all=true` 时返回所有客户联系人（忽略 customer_id）
- `page`（int，默认 1）
- `page_size`（int，默认 20）

错误：
- 400：`{"detail": "type=customer 时必须提供 customer_id，或传 all=true 返回所有客户联系人"}`

---

### POST /api/contacts

创建联系人。

请求（客户联系人）：`POST /api/contacts`
```json
{"customer_id": "uuid", "name": "张三", "email": "zhang@keji.com", "phone": "13800001111", "department": "技术部"}
```

请求（内部同事，customer_id 为 null）：`POST /api/contacts`
```json
{"name": "李四", "email": "lisi@company.com", "phone": "13900002222", "department": "运维部"}
```

响应（201）：
```json
{
  "id": "dfa1836c-6d33-4382-8ff7-307cf2740d4f",
  "customer_id": "6d2f0d9b-ef37-4c3c-bec8-a66884d85dfb",
  "name": "张三",
  "email": "zhang@keji.com",
  "phone": "13800001111",
  "department": "技术部",
  "is_active": true,
  "created_at": "2026-06-24T10:56:47.936893",
  "updated_at": "2026-06-24T10:56:47.936897"
}
```

HTTP 状态码：201

关键字段：
- `name`（string，必填，1-128 字符）
- `email`（string，必填，需包含 @）
- `customer_id`（string 或 null，可选）：为 null 表示内部同事
- `phone`（string，可选）
- `department`（string，可选）

错误：
- 404：`{"detail": "客户不存在"}` — customer_id 指向不存在的客户

---

### GET /api/contacts/{id}

获取联系人详情。

请求：`GET /api/contacts/{id}`

响应：同创建响应格式。

HTTP 状态码：200

错误：
- 404：`{"detail": "联系人不存在"}`

---

### PUT /api/contacts/{id}

更新联系人。

请求：`PUT /api/contacts/{id}`
```json
{"phone": "13811112222", "department": "研发部"}
```

响应：同创建响应格式，所有字段可选更新。

HTTP 状态码：200

---

### DELETE /api/contacts/{id}

软删除联系人（将 is_active 设为 false）。

请求：`DELETE /api/contacts/{id}`

响应：
```json
{"detail": "联系人已删除（状态设为 inactive）"}
```

HTTP 状态码：200

---

## 系统配置 (System)

### GET /api/system/smtp

获取 SMTP 配置（不返回密码）。

请求：`GET /api/system/smtp`

响应：
```json
{
  "host": "mail.xhwltech.com",
  "port": 587,
  "username": "wuhao@xhwltech.com",
  "sender_name": "wuhao",
  "sender_email": "wuhao@xhwltech.com",
  "encryption": "tls"
}
```

HTTP 状态码：200

关键字段：
- `encryption`（string）：加密方式，枚举值 `tls`（SSL/TLS，端口 465）| `starttls`（STARTTLS，端口 587）| `none`（无加密，端口 25）

错误：
- 404：`{"detail": "SMTP 配置不存在，请先通过 PUT 接口创建"}`

---

### PUT /api/system/smtp

更新或创建 SMTP 配置。首次不存在则创建，已存在则更新。password 传入明文，后端加密存储。

请求：`PUT /api/system/smtp`
```json
{
  "host": "mail.xhwltech.com",
  "port": 587,
  "username": "wuhao@xhwltech.com",
  "password": "test123",
  "sender_name": "wuhao",
  "sender_email": "wuhao@xhwltech.com",
  "encryption": "tls"
}
```

响应：
```json
{
  "host": "mail.xhwltech.com",
  "port": 587,
  "username": "wuhao@xhwltech.com",
  "sender_name": "wuhao",
  "sender_email": "wuhao@xhwltech.com",
  "encryption": "tls"
}
```

HTTP 状态码：200

关键字段：
- `host`（string，必填）
- `port`（int，必填，1-65535）
- `username`（string，可选）
- `password`（string，可选）：明文传入，后端 Fernet 加密后存入 password_enc，不返回
- `sender_name`（string，可选）
- `sender_email`（string，可选）
- `encryption`（string，默认 "tls"）：加密方式，枚举 `tls` | `starttls` | `none`。非法值返回 400 校验错误

---

### POST /api/system/smtp/test

测试 SMTP 连接。用当前配置发送一封测试邮件到指定地址。

请求：`POST /api/system/smtp/test`
```json
{"test_email": "admin@company.com"}
```

响应（成功）：
```json
{"success": true, "message": "测试邮件已发送到 admin@company.com"}
```

响应（失败）：
```json
{"success": false, "message": "发送失败：[Errno -2] Name or service not known"}
```

HTTP 状态码：200

错误：
- 404：SMTP 配置不存在

### GET /api/system/dingtalk

获取钉钉机器人配置。secret 脱敏显示 `"***"`。

请求：`GET /api/system/dingtalk`

响应：
```json
{
  "id": "57d6b8c2-62de-4f3e-9b48-ef62d6d7a673",
  "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test123",
  "secret": "***",
  "is_active": true,
  "created_at": "2026-06-26T16:28:28.305689",
  "updated_at": "2026-06-26T16:28:28.305704"
}
```

HTTP 状态码：200

错误：
- 404：钉钉配置不存在

关键字段：
- `webhook_url`（string）：钉钉机器人 Webhook URL
- `secret`（string）：脱敏后的加签密钥，有值显示 `"***"`，空则显示 `""`
- `is_active`（bool）：是否启用钉钉通知

---

### PUT /api/system/dingtalk

更新或创建钉钉机器人配置（upsert 逻辑）。

请求：`PUT /api/system/dingtalk`
```json
{
  "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "secret": "SECxxx",
  "is_active": true
}
```

响应：
```json
{
  "id": "57d6b8c2-62de-4f3e-9b48-ef62d6d7a673",
  "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "secret": "***",
  "is_active": true,
  "created_at": "2026-06-26T16:28:28.305689",
  "updated_at": "2026-06-26T16:28:32.655836"
}
```

HTTP 状态码：200

请求体：
- `webhook_url`（string，必填）：钉钉机器人 Webhook URL
- `secret`（string，可选）：加签密钥。传 `"***"` 表示保留原值不修改；传 `""` 表示清空密钥；传其他值表示更新
- `is_active`（bool，可选）：是否启用

关键字段：同 GET 响应

---

### POST /api/system/dingtalk/test

测试钉钉连接。发送一条测试 Markdown 消息到钉钉群。

请求：`POST /api/system/dingtalk/test`
```json
{"webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx", "secret": "SECxxx"}
```
（参数均可选，不传则使用已保存配置）

响应（成功）：
```json
{"success": true, "message": "发送成功"}
```

响应（失败）：
```json
{"success": false, "message": "token is not exist"}
```

HTTP 状态码：200

错误：
- 404：未提供 Webhook URL 且未保存配置

---

### GET /api/system/config

获取所有系统配置（键值对列表）。

请求：`GET /api/system/config`

响应：
```json
[
  {
    "key": "expiry_warning_days",
    "value": "7,3",
    "description": "临期提醒天数（逗号分隔）"
  }
]
```

HTTP 状态码：200

关键字段：
- `key`（string）：配置键
- `value`（string）：配置值
- `description`（string|null）：配置说明

---

### GET /api/system/config/schedules

获取所有通知调度时间配置。

请求：`GET /api/system/config/schedules`

响应：
```json
{
  "check-expiring-rentals": "08:00",
  "check-expired-rentals": "00:00",
  "check-reclaim-expired": "01:00"
}
```

HTTP 状态码：200

关键字段：
- `check-expiring-rentals`（string）：临期提醒调度时间（HH:MM）
- `check-expired-rentals`（string）：到期通知调度时间（HH:MM）
- `check-reclaim-expired`（string）：回收执行调度时间（HH:MM）

---

### PUT /api/system/config/schedules

批量更新通知调度时间，并触发 Beat 重启使配置生效。

请求：`PUT /api/system/config/schedules`
```json
{
  "check-expiring-rentals": "09:30",
  "check-expired-rentals": "00:30",
  "check-reclaim-expired": "02:00"
}
```

响应：
```json
{
  "detail": "通知时间配置已保存",
  "restart": "Beat 已触发重启"
}
```

HTTP 状态码：200

错误：
- 400：缺少必填字段 `{"detail": "缺少必填字段: check-reclaim-expired"}`
- 400：格式错误 `{"detail": "check-expiring-rentals 格式错误: 需要 HH:MM 格式, 实际 9:3"}`
- 400：时间超出范围 `{"detail": "check-expiring-rentals 时间超出范围: 25:00"}`

关键字段：
- 请求体三个字段均为必填，格式 HH:MM，范围 00:00~23:59
- `detail`（string）：操作结果描述
- `restart`（string）：Beat 重启结果（K8s 环境下自动触发，非 K8s 环境提示手动重启）

---

### GET /api/system/config/{key}

获取单个系统配置。

请求：`GET /api/system/config/expiry_warning_days`

响应：
```json
{
  "key": "expiry_warning_days",
  "value": "7,3",
  "description": "临期提醒天数（逗号分隔）"
}
```

HTTP 状态码：200

错误：
- 404：`{"detail": "配置 'xxx' 不存在"}`

---

### PUT /api/system/config/{key}

更新或创建系统配置。key 不存在则创建，存在则更新。

请求：`PUT /api/system/config/expiry_warning_days`
```json
{"value": "14,7,3"}
```

响应：
```json
{
  "key": "expiry_warning_days",
  "value": "14,7,3",
  "description": "临期提醒天数（逗号分隔）"
}
```

HTTP 状态码：200

关键字段：
- `value`（string，必填）：配置值
- `description`（string，可选）：配置说明，不传则保持旧值

---

### POST /api/system/trigger/{task_name}

调试端点：手动触发定时任务，支持模拟日期。

请求：`POST /api/system/trigger/check_expired_rentals`
```json
{"simulate_date": "2026-06-30"}
```

响应：
```json
{
  "task": "check_expired_rentals",
  "simulated_date": "2026-06-30",
  "result": "None"
}
```

HTTP 状态码：200

关键字段：
- `task_name`（path，必填）：任务名，可选值：`check_expiring_rentals` / `check_expired_rentals` / `check_reclaim_expired`
- `simulate_date`（body，可选）：模拟日期，格式 `YYYY-MM-DD`。不传则使用当前日期
- `result`（string）：任务执行结果（`None` 表示正常完成，含异常信息则返回错误描述）

错误：
- 400：`{"detail": "无效任务名，可选: check_expiring_rentals, check_expired_rentals, check_reclaim_expired"}`

---

## 租赁记录 (RentalRecord)

### GET /api/rentals

获取租赁记录列表，支持按客户、状态过滤和模糊搜索。返回全部业务字段（不含密码、联系人列表、邮件日志）。

请求：`GET /api/rentals?customer_id=&status=provisioned&search=Dell&unlinked_only=true&page=1&page_size=20`

查询参数：
- `customer_id`（string，可选）：按客户过滤
- `status`（string，可选）：设备物理状态：`运行中 | 维护中 | 已下架 | 故障`
- `search`（string，可选）：按机器型号模糊搜索
- `private_ip`（string，可选）：按内网 IP 模糊搜索
- `public_ip`（string，可选）：按公网 IP 模糊搜索（匹配 `public_ips` JSON 数组）
- `rack_location`（string，可选）：按机架位置模糊搜索
- `unlinked_only`（bool，默认 false）：仅返回未关联任何合同的设备
- `page`（int，默认 1）
- `page_size`（int，默认 20，最大 200）

响应：
```json
{
  "items": [
    {
      "id": "9616fbd8-b7b9-4af7-ab14-9ed3868f5486",
      "contract_id": "abc123-def456",
      "customer": {"id": "c0441ac5-b27f-4876-b3fe-aec901a50217", "name": "测试客户-已更新"},
      "machine_model": "Dell R740",
      "cpu_model": "2×Intel Xeon Gold 6248R",
      "memory_gb": 256,
      "gpu_info": "8×NVIDIA A100 80GB",
      "system_disk_gb": 480,
      "data_disks": [{"size_gb": 2000, "type": "NVMe SSD"}],
      "os_version": "Ubuntu 22.04 LTS",
      "bandwidth_mbps": 1000,
      "rack_location": "A01-05-U12",
      "private_ip": "10.0.0.1",
      "public_ips": ["1.2.3.4"],
      "ssh_port": 22,
      "root_username": "root",
      "billing_model": "monthly",
      "start_date": "2026-06-01",
      "end_date": "2026-12-01",
      "auto_renew": false,
      "remark": "QA修复测试-全量替换contacts",
      "status": "运行中",
      "created_at": "2026-06-24T13:47:28",
      "updated_at": "2026-06-24T14:25:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

关键字段：
- `items[].contract_id`（string|null）：已关联的合同ID，未关联时为 null
- `items[].customer`（object）：关联客户简要信息
- `items[].status`（string）：设备物理状态（运行中 / 维护中 / 已下架 / 故障）
- `items[].data_disks`（array|null）：数据盘列表，每项含 `size_gb`(int) 和 `type`(string)
- `items[].public_ips`（array|null）：公网 IP 列表
- `items[].ssh_port`（int）：SSH 端口
- `items[].root_username`（string|null）：root 用户名（不含密码）
- `items[].billing_model`（string）：计费模式 monthly / yearly
- `items[].auto_renew`（bool）：是否自动续期
- `items[].remark`（string|null）：备注
- `items[].updated_at`（datetime|null）：最后更新时间
- ⚠️ 列表接口不返回 `root_password`、`contacts`、`email_logs`，详情请用 GET /api/rentals/{id}

---

### POST /api/rentals

创建租赁记录（仅保存，不发邮件）。`root_password` 传入明文，后端加密存储。

请求：`POST /api/rentals`
```json
{
  "customer_id": "uuid",
  "contacts": [
    {"contact_id": "uuid", "recipient_type": "to"},
    {"contact_id": "uuid", "recipient_type": "cc"}
  ],
  "machine_model": "Dell R740",
  "cpu_model": "2xIntel Xeon Gold 6248R 48C",
  "memory_gb": 256,
  "gpu_info": "8xNVIDIA A100 80GB",
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

响应（201）：
```json
{
  "id": "cef1e7f7-8118-4af6-87af-9dc9955d9f90",
  "customer": {"id": "b8c79d87-aae6-43f7-b645-f0ed74eddf65", "name": "星辰科技"},
  "contacts": [
    {"contact_id": "3e1291b5-0c35-47ca-8a2e-d2d19b9e6c43", "name": "张三", "email": "zhang@keji.com", "recipient_type": "to"},
    {"contact_id": "d686976a-8e67-4035-af3b-d48d0488a8c2", "name": "李四", "email": "lisi@keji.com", "recipient_type": "cc"}
  ],
  "machine_model": "Dell R740",
  "root_password": "TempPass123!",
  "status": "运行中",
  "email_logs": [],
  "created_at": "2026-06-24T11:17:18.835762",
  "updated_at": "2026-06-24T11:17:18.835768"
}
```

HTTP 状态码：201

关键字段：
- `root_password`（string，请求时明文传入，响应时解密返回）
- `contacts`（array）：关联联系人，写入 rental_contact 中间表
- `data_disks`（array，可选）：数据盘列表

错误：
- 404：`{"detail": "客户不存在"}`
- 404：`{"detail": "联系人不存在: {id}"}`

---

### GET /api/rentals/{id}

获取租赁记录详情，包含客户信息、contacts 列表（含 name/email）、email_logs 列表。

请求：`GET /api/rentals/{id}`

响应：同 POST 响应，额外包含 `email_logs` 数组。

HTTP 状态码：200

错误：
- 404：`{"detail": "租赁记录不存在"}`

---

### PUT /api/rentals/{id}

全量更新租赁记录（含 contacts 替换）。所有字段可选，只更新传入的字段。

请求：`PUT /api/rentals/{id}`
```json
{"remark":"QA修复测试","data_disks":[{"size_gb":2000,"type":"NVMe SSD"}],"contacts":[{"contact_id":"fe2bd0b7-0763-4604-a7bf-6ce8e21c60fd","recipient_type":"to"}]}
```

响应：
```json
{
  "id": "9616fbd8-b7b9-4af7-ab14-9ed3868f5486",
  "customer": {"id": "c0441ac5-b27f-4876-b3fe-aec901a50217", "name": "测试客户-已更新"},
  "contacts": [{"contact_id": "fe2bd0b7-0763-4604-a7bf-6ce8e21c60fd", "name": "张三", "email": "zhangsan@test.com", "recipient_type": "to"}],
  "machine_model": "Dell R740",
  "cpu_model": "2×Intel Xeon Gold 6248R",
  "memory_gb": 256,
  "gpu_info": "8×NVIDIA A100 80GB",
  "system_disk_gb": 480,
  "data_disks": [{"size_gb": 2000, "type": "NVMe SSD"}],
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
  "remark": "QA修复测试",
  "status": "已下架",
  "email_logs": [],
  "created_at": "2026-06-24T13:47:28",
  "updated_at": "2026-06-24T14:24:49"
}
```

HTTP 状态码：200

关键字段：
- `data_disks`（array，可选）：数据盘列表，每个元素含 `size_gb`(int) 和 `type`(string)。传入时全量替换
- `contacts`（array，可选）：关联联系人列表。不传则保持旧值；传入时全量替换（传 `[]` 清空）
- `root_password`（string，可选）：明文传入，后端加密存储
- `status`（string，可选）：设备物理状态，人工可修改：`运行中 | 维护中 | 已下架 | 故障`

错误：
- 404：`{"detail": "租赁记录不存在"}`
- 404：`{"detail": "联系人不存在: {id}"}`

---

### DELETE /api/rentals/{id}

删除租赁记录（物理删除，同时删除中间表关联）。

请求：`DELETE /api/rentals/{id}`

响应：
```json
{"detail": "租赁记录已删除"}
```

HTTP 状态码：200

---

### POST /api/rentals/{id}/send-provision-email

手动发送开通邮件。以该设备所属合同为粒度合并发送（异步）。

请求：`POST /api/rentals/{id}/send-provision-email`
```json
{}
```

响应：
```json
{
  "email_log_ids": [],
  "recipient_count": 0,
  "message": "已提交异步发送任务（合同 主合同-2026，共 3 台设备）"
}
```

HTTP 状态码：200

发送逻辑（合同驱动）：
1. 验证锚点租赁记录存在
2. 找到该 rental 关联的合同（取第一个）
3. 提交 Celery 异步任务 `send_manual_email(contract_id, "provision")`
4. 异步任务中：从合同的 contract_rental 获取所有设备、从 contract_contact 获取所有联系人 → 合并发送

错误：
- 404：`{"detail": "租赁记录不存在"}`
- 400：`{"detail": "该设备未关联任何合同，请先创建合同并关联设备"}`

关键字段：
- `email_log_ids`（list[string]）：异步模式下为空数组
- `recipient_count`（int）：异步模式下为 0
- `message`（string）：含合同名称和设备数量的提示信息

---

### POST /api/rentals/{id}/send-expiry-reminder

手动发送临期提醒。以该设备所属合同为粒度合并发送（异步），并更新合同状态为 `expiring`。

请求：`POST /api/rentals/{id}/send-expiry-reminder`
```json
{}
```

响应：
```json
{
  "email_log_ids": [],
  "recipient_count": 0,
  "message": "已提交异步发送任务（合同 主合同-2026，共 3 台设备）"
}
```

HTTP 状态码：200

发送逻辑（合同驱动）：
1. 验证锚点租赁记录存在
2. 找到该 rental 关联的合同（取第一个）
3. 更新合同状态为 `expiring`
4. 提交 Celery 异步任务 `send_manual_email(contract_id, "expiry_warning")`

错误：
- 404：`{"detail": "租赁记录不存在"}`
- 400：`{"detail": "该设备未关联任何合同，请先创建合同并关联设备"}`

关键字段：
- `email_log_ids`（list[string]）：异步模式下为空数组
- `recipient_count`（int）：异步模式下为 0
- `message`（string）：含合同名称和设备数量的提示信息

---

### POST /api/rentals/{id}/reclaim

手动回收。以该设备所属合同为粒度合并发送（异步），状态更新在 Celery 任务中完成。

请求：`POST /api/rentals/{id}/reclaim`
```json
{}
```

响应：
```json
{
  "success": true,
  "message": "已提交异步发送任务（合同 主合同-2026，共 3 台设备），状态将在任务完成后更新",
  "email_log_ids": [],
  "recipient_count": 0
}
```

HTTP 状态码：200

发送逻辑（合同驱动）：
1. 验证锚点租赁记录存在
2. 找到该 rental 关联的合同（取第一个）
3. 提交 Celery 异步任务 `send_manual_email(contract_id, "reclaim")`
4. 异步任务中：先执行回收（更新合同状态为 `reclaimed`、更新所有关联设备状态为 `空闲中`）→ 再发送回收通知邮件

错误：
- 404：`{"detail": "租赁记录不存在"}`
- 400：`{"detail": "该设备未关联任何合同，请先创建合同并关联设备"}`

关键字段：
- `success`（bool）：是否成功提交任务
- `message`（string）：操作结果描述（含合同名称和设备数量）
- `email_log_ids`（list[string]）：异步模式下为空数组
- `recipient_count`（int）：异步模式下为 0

---

## 邮件模板 (EmailTemplate)

### GET /api/templates/variables

返回租赁记录所有可用模板变量的字段名和中文说明。字段来源与 RentalRecord 模型保持一致。

⚠️ **合并发送**：定时任务按客户合并发送时，模板上下文为：
- `customer_name`：客户名称
- `rental_count`：设备数量
- `rentals`：设备列表数组，每个元素的字段同单机变量（`machine_model`、`cpu_model` 等）

模板示例：
```jinja2
<h2>尊敬的 {{ customer_name }}：</h2>
<p>您有 {{ rental_count }} 台设备即将到期：</p>
<table>
{% for r in rentals %}
<tr><td>{{ r.machine_model }}</td><td>{{ r.end_date }}</td><td>{{ r.days_until_expiry }}天</td></tr>
{% endfor %}
</table>
```

请求：`GET /api/templates/variables`

响应：
```json
{
  "variables": [
    {"field": "customer_name", "label": "客户名称", "type": "string"},
    {"field": "rental_count", "label": "设备数量", "type": "number", "note": "合并发送时可用"},
    {"field": "rentals", "label": "设备列表", "type": "array", "note": "用 {% for r in rentals %} 遍历，r 的字段同单机变量（machine_model, cpu_model 等）"},
    {"field": "machine_model", "label": "机器型号", "type": "string"},
    {"field": "cpu_model", "label": "CPU 型号", "type": "string"},
    {"field": "memory_gb", "label": "内存(GB)", "type": "number"},
    {"field": "gpu_info", "label": "GPU 信息", "type": "string"},
    {"field": "system_disk_gb", "label": "系统盘(GB)", "type": "number"},
    {"field": "data_disks", "label": "数据盘列表", "type": "array", "note": "遍历: {% for disk in data_disks %}{{ disk.size_gb }}GB {{ disk.type }}{% endfor %}"},
    {"field": "os_version", "label": "操作系统", "type": "string"},
    {"field": "bandwidth_mbps", "label": "带宽(Mbps)", "type": "number"},
    {"field": "rack_location", "label": "机架位置", "type": "string"},
    {"field": "private_ip", "label": "内网 IP", "type": "string"},
    {"field": "public_ips", "label": "公网 IP 列表", "type": "array", "note": "遍历: {% for ip in public_ips %}{{ ip }}{% endfor %}"},
    {"field": "ssh_port", "label": "SSH 端口", "type": "number"},
    {"field": "root_username", "label": "SSH 账号", "type": "string"},
    {"field": "root_password", "label": "SSH 密码", "type": "string"},
    {"field": "billing_model", "label": "计费方式", "type": "string", "note": "monthly/quarterly/yearly"},
    {"field": "start_date", "label": "开通日期", "type": "date"},
    {"field": "end_date", "label": "到期日期", "type": "date"},
    {"field": "days_until_expiry", "label": "距到期天数", "type": "number", "note": "仅临期/到期模板可用"},
    {"field": "auto_renew", "label": "自动续期", "type": "boolean"},
    {"field": "remark", "label": "备注", "type": "string"}
  ],
  "updated_at": "2026-06-25T16:10:21.948077"
}
```

HTTP 状态码：200

关键字段：
- `variables`（array）：变量列表，每个元素包含 `field`（变量名）、`label`（中文说明）、`type`（类型）、`note`（可选，使用说明）
- `updated_at`（string）：接口更新时间（ISO 8601）
- ⚠️ 新增 `rental_count`（设备数量）和 `rentals`（设备列表数组），用于定时任务合并发送场景

---

### GET /api/templates

获取模板列表。

请求：`GET /api/templates?page=1&page_size=20`

响应：
```json
{
  "items": [
    {
      "id": "00bef557-259c-48fa-9173-54426b028336",
      "name": "资源开通通知",
      "trigger_type": "provision",
      "subject_tpl": "【CronMail】您的服务器 {{ machine_model }} 已开通",
      "body_html": "<h2>尊敬的 {{ customer_name }}：</h2>...",
      "variables_desc": {"machine_model": "机器型号"},
      "signature_html": "<p style=\"color:#999;\">-- CronMail 系统</p>",
      "is_active": true,
      "version": 1,
      "created_at": "2026-06-24T11:17:29.410786",
      "updated_at": "2026-06-24T11:17:29.410792"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

---

### POST /api/templates

创建邮件模板。

请求：`POST /api/templates`
```json
{
  "name": "资源开通通知",
  "trigger_type": "provision",
  "subject_tpl": "【CronMail】您的服务器 {{ machine_model }} 已开通",
  "body_html": "<h2>尊敬的 {{ customer_name }}：</h2>...",
  "variables_desc": {"machine_model": "机器型号"},
  "signature_html": "<p style=\"color:#999;\">-- CronMail 系统</p>",
  "is_active": true
}
```

响应（201）：同 GET 列表项。

关键字段：
- `trigger_type`（string，必填）：`provision | expiry_warning | expiry_notice | reclaim`
- `subject_tpl` / `body_html`（string，必填）：Jinja2 模板
- `variables_desc`（object，可选）：变量说明
- `signature_html`（string，可选）：邮件签名（HTML），渲染时自动拼接在正文末尾

---

### GET /api/templates/{id}

获取模板详情。

请求：`GET /api/templates/{id}`

响应：同创建响应。

HTTP 状态码：200

错误：
- 404：`{"detail": "模板不存在"}`

---

### PUT /api/templates/{id}

更新模板，version 自动 +1。所有字段可选，包括 `signature_html`。

请求：`PUT /api/templates/{id}`（所有字段可选）

响应：同创建响应，`version` 字段自动递增。

HTTP 状态码：200

---

### DELETE /api/templates/{id}

删除模板。

请求：`DELETE /api/templates/{id}`

响应：
```json
{"detail": "模板已删除"}
```

HTTP 状态码：200

---

### POST /api/templates/preview

实时预览模板（不依赖数据库）。使用 Jinja2 SandboxedEnvironment 渲染。

请求：`POST /api/templates/preview`
```json
{
  "subject_tpl": "{{ customer_name }} 机器开通通知",
  "body_html": "<p>机器型号: {{ machine_model }}</p>",
  "sample_data": {
    "customer_name": "测试公司",
    "machine_model": "Dell R740"
  },
  "signature_html": "<hr><p>此致<br>CronMail 团队</p>"
}
```

响应：
```json
{
  "subject_rendered": "测试公司 机器开通通知",
  "body_rendered": "<p>机器型号: Dell R740</p>\n<!-- signature -->\n<hr><p>此致<br>CronMail 团队</p>"
}
```

HTTP 状态码：200

关键字段：
- `signature_html`（string，可选）：邮件签名（HTML），渲染时自动拼接在 body 末尾
- `subject_rendered`（string）：渲染后的主题
- `body_rendered`（string）：渲染后的正文（含签名拼接）

错误：
- 400：`{"detail": "主题模板渲染失败: 模板变量缺失: ..."}`

---

### POST /api/templates/{id}/test-send

测试发送邮件。使用模板渲染后发送给指定联系人，不写 EmailLog。

⚠️ **变量结构变更**：后端自动将 `sample_data` 包装为统一结构 `{customer_name, rental_count: 1, rentals: [sample_data]}`，
因此模板中请使用 `{{ customer_name }}`、`{{ rental_count }}`、`{% for r in rentals %}{{ r.machine_model }}{% endfor %}` 等变量。

请求：`POST /api/templates/17086793-9496-4ec3-bb3d-fc8fe9ece671/test-send`
```json
{
  "to_contact_ids": ["3ce064c5-5d08-4d19-999f-aadffe99b335"],
  "sample_data": {
    "machine_model": "SA5.2XLARGE16",
    "private_ip": "10.0.0.1",
    "cpu_model": "Intel Xeon",
    "memory_gb": 16,
    "os_version": "Ubuntu 22.04",
    "end_date": "2026-07-15"
  }
}
```

响应（成功）：
```json
{
  "success": true,
  "message": "测试邮件发送成功",
  "to_emails": ["wuhao@xhwltech.com"],
  "cc_emails": [],
  "subject_rendered": "【CronMail】裸金属服务器资源回收通知 - "
}
```

响应（失败）：
```json
{
  "success": false,
  "message": "发送失败: SMTP 连接失败：无法连接到 mail.example.com:587",
  "to_emails": ["test@example.com"],
  "cc_emails": [],
  "subject_rendered": "【CronMail】裸金属服务器资源回收通知 - "
}
```

HTTP 状态码：200

关键字段：
- `to_contact_ids`（array，必填，至少一个）：收件人 contact id 列表
- `cc_contact_ids`（array，可选，默认 []）：抄送 contact id 列表
- `sample_data`（object，可选）：单条设备的模板变量数据（平铺字段如 `machine_model`、`private_ip` 等），不传则使用模板默认 `variables_desc`。后端自动包装为 `{customer_name, rental_count: 1, rentals: [sample_data]}` 统一结构
- `success`（bool）：发送是否成功
- `message`（string）：结果描述
- `to_emails` / `cc_emails`（array）：实际发送到的邮箱地址列表
- `subject_rendered`（string）：渲染后的邮件主题

发送逻辑：
1. 查模板（含 signature_html）
2. 根据 contact ids 查 Contact 表获取邮箱
3. 取 sample_data，包装为统一结构 `{customer_name, rental_count: 1, rentals: [sample_data]}`
4. 渲染 subject + body_html（拼接 signature_html）
5. 查 SMTP 配置并发送邮件
6. 不写 EmailLog（测试邮件不记录）

错误：
- 404：`{"detail": "模板不存在"}`
- 400：`{"detail": "未找到有效的收件人邮箱"}`
- 400：`{"detail": "SMTP 配置不存在，请先配置 SMTP"}`
- 400：`{"detail": "主题模板渲染失败: ..."}`
- 400：`{"detail": "正文模板渲染失败: ..."}`

---

## 合同管理 (Contract)

### GET /api/contracts

获取合同列表，支持按客户、状态过滤和模糊搜索。

请求：`GET /api/contracts?customer_id=&status=active&search=主合同&page=1&page_size=20`

查询参数：
- `customer_id`（string，可选）：按客户过滤
- `status`（string，可选）：`active | expiring | expired | reclaimed`
- `search`（string，可选）：按合同名称模糊搜索
- `page`（int，默认 1，最小 1）
- `page_size`（int，默认 20，最小 1，最大 100）

响应：
```json
{
  "items": [
    {
      "id": "e5ac205c-dc6b-40c6-b081-1654ba76de2d",
      "customer_id": "ab512a89-7cc8-4d9d-8349-c616f46a1bab",
      "customer_name": "测试客户",
      "name": "主合同-2026",
      "contract_no": "CT-2026-001",
      "start_date": "2026-06-01",
      "end_date": "2026-12-31",
      "billing_model": "monthly",
      "status": "active",
      "remark": "测试合同",
      "rental_count": 1,
      "contact_count": 1,
      "created_at": "2026-06-25T10:05:48.646038",
      "updated_at": "2026-06-25T10:05:48.646044"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

关键字段：
- `items[].customer_name`（string|null）：关联客户名称
- `items[].rental_count`（int）：关联设备数量
- `items[].contact_count`（int）：关联联系人数量
- `items[].billing_model`（string）：计费方式 monthly / quarterly / yearly
- `items[].status`（string）：合同状态 active / expiring / expired / reclaimed

---

### POST /api/contracts

创建合同，可同时关联设备和联系人。

请求：`POST /api/contracts`
```json
{
  "customer_id": "ab512a89-7cc8-4d9d-8349-c616f46a1bab",
  "name": "主合同-2026",
  "contract_no": "CT-2026-001",
  "start_date": "2026-06-01",
  "end_date": "2026-12-31",
  "billing_model": "monthly",
  "remark": "测试合同",
  "rental_ids": ["58b18fe0-0470-4b9d-bd1c-372e9e917ce5"],
  "contacts": [{"contact_id": "07971a25-01f7-4493-94b3-b39094882790", "recipient_type": "to"}]
}
```

响应（201）：
```json
{
  "id": "e5ac205c-dc6b-40c6-b081-1654ba76de2d",
  "customer_id": "ab512a89-7cc8-4d9d-8349-c616f46a1bab",
  "customer_name": "测试客户",
  "name": "主合同-2026",
  "contract_no": "CT-2026-001",
  "start_date": "2026-06-01",
  "end_date": "2026-12-31",
  "billing_model": "monthly",
  "status": "active",
  "remark": "测试合同",
  "rental_count": 1,
  "contact_count": 1,
  "created_at": "2026-06-25T10:05:48.646038",
  "updated_at": "2026-06-25T10:05:48.646044",
  "rentals": [
    {
      "id": "58b18fe0-0470-4b9d-bd1c-372e9e917ce5",
      "machine_model": "Dell R740",
      "private_ip": null,
      "public_ips": [],
      "os_version": null,
      "status": "运行中"
    }
  ],
  "contacts": [
    {
      "contact_id": "07971a25-01f7-4493-94b3-b39094882790",
      "name": "张三",
      "email": "zhang@test.com",
      "recipient_type": "to"
    }
  ]
}
```

HTTP 状态码：201

关键字段：
- `name`（string，必填，1-255 字符）
- `customer_id`（string，必填）
- `start_date` / `end_date`（date，必填）
- `billing_model`（string，默认 "monthly"）：monthly / quarterly / yearly
- `contract_no`（string，可选，最长 100）
- `remark`（string，可选）
- `rental_ids`（array，可选）：创建时关联的设备 ID 列表
- `contacts`（array，可选）：创建时关联的联系人列表，每项含 `contact_id` 和 `recipient_type`（"to"/"cc"）。后端自动按 `(contact_id, recipient_type)` 去重，重复项只保留第一条

错误：
- 404：`{"detail": "客户不存在"}`

---

### GET /api/contracts/{id}

获取合同详情，包含关联设备和联系人列表。

请求：`GET /api/contracts/e5ac205c-dc6b-40c6-b081-1654ba76de2d`

响应：同 POST 响应格式，包含 `rentals` 和 `contacts` 数组。

HTTP 状态码：200

错误：
- 404：`{"detail": "合同不存在"}`

---

### PUT /api/contracts/{id}

更新合同。所有字段可选，只更新传入的字段。`contacts` 传入时全量替换。**已过期或已回收的合同不允许修改。**

请求：`PUT /api/contracts/{id}`
```json
{"name": "主合同-2026（已更新）", "status": "active", "remark": "更新后的备注"}
```

响应：同详情格式（含 `rentals` 和 `contacts`）。

HTTP 状态码：200

关键字段：
- `contacts`（array，可选）：关联联系人列表。不传则保持旧值；传入时全量替换（传 `[]` 清空）

错误：
- 404：`{"detail": "合同不存在"}`
- 422：`{"detail": "已过期或已回收的合同不允许修改"}` — 合同状态为 `expired` 或 `reclaimed` 时拒绝修改

---

### DELETE /api/contracts/{id}

删除合同（物理删除，CASCADE 删除中间表关联）。

请求：`DELETE /api/contracts/{id}`

响应：
```json
{"detail": "合同已删除"}
```

HTTP 状态码：200

错误：
- 404：`{"detail": "合同不存在"}`

---

### POST /api/contracts/{id}/rentals

关联设备到合同。跳过已存在的关联（避免 duplicate key）。**已过期或已回收的合同不允许关联设备。**

请求：`POST /api/contracts/{id}/rentals`
```json
{"rental_ids": ["58b18fe0-0470-4b9d-bd1c-372e9e917ce5"]}
```

响应：
```json
{"detail": "已关联 1 台设备"}
```

HTTP 状态码：200

错误：
- 404：`{"detail": "合同不存在"}`
- 422：`{"detail": "已过期或已回收的合同不允许关联设备"}` — 合同状态为 `expired` 或 `reclaimed` 时拒绝关联

---

### DELETE /api/contracts/{id}/rentals

取消关联设备。**已过期或已回收的合同不允许取消关联。**

请求：`DELETE /api/contracts/{id}/rentals`
```json
{"rental_ids": ["58b18fe0-0470-4b9d-bd1c-372e9e917ce5"]}
```

响应：
```json
{"detail": "已取消关联 1 台设备"}
```

HTTP 状态码：200

错误：
- 404：`{"detail": "合同不存在"}`
- 422：`{"detail": "已过期或已回收的合同不允许取消关联"}` — 合同状态为 `expired` 或 `reclaimed` 时拒绝取消关联

---

### GET /api/contracts/dashboard/stats

获取仪表盘合同运营概览统计（总数、临期数、已回收数、临期合同详情）。

请求：`GET /api/contracts/dashboard/stats`

响应：
```json
{
  "total_contracts": 3,
  "expiring": 1,
  "reclaimed": 2,
  "expiring_contracts": [
    {
      "contract_id": "0f94afd6-a801-4712-9121-96c0e95e41d3",
      "contract_name": "4090算力租赁",
      "customer_name": "江苏东蓝信息技术有限公司",
      "end_date": "2026-07-06",
      "status": "active",
      "rental_count": 2,
      "rentals": [
        {
          "id": "44dc99cb-de64-4156-bb84-6e45b450cd5f",
          "machine_model": "R8428A12",
          "private_ip": "192.168.100.125",
          "public_ips": ["116.169.215.245"],
          "os_version": "Ubuntu 22.04 TLS",
          "status": "租赁中",
          "rack_location": "E09-18U"
        },
        {
          "id": "e8fa71bd-82bd-4e2f-b6dd-b459d80e18b0",
          "machine_model": "R8428A12",
          "private_ip": "192.168.100.124",
          "public_ips": ["116.169.215.244"],
          "os_version": "Ubuntu 22.04 TLS",
          "status": "租赁中",
          "rack_location": "E09-24U"
        }
      ]
    }
  ]
}
```

HTTP 状态码：200

关键字段：
- `total_contracts`（int）：合同总数
- `expiring`（int）：临期数量（end_date <= today+max_days 且 >= today，max_days 从 system_config.expiry_warning_days 读取，默认 7）
- `reclaimed`（int）：已回收数量（status == 'reclaimed'）
- `expiring_contracts`（array）：临期合同详情列表（最多 10 条），含关联设备

---

### GET /api/contracts/changelog

获取变更记录列表。

请求：`GET /api/contracts/changelog?target_type=contract&target_id=abc-123`

查询参数：
- `target_type`（string，必填）：`contract` 或 `rental`
- `target_id`（string，必填）：目标 ID

响应：
```json
[
  {
    "id": "log-uuid-1",
    "content": "续费至 2027 年",
    "created_at": "2026-07-03T10:30:00"
  },
  {
    "id": "log-uuid-2",
    "content": "客户申请提前解约",
    "created_at": "2026-07-02T14:00:00"
  }
]
```

HTTP 状态码：200

关键字段：
- `content`（string）：变更内容（人工输入）
- `created_at`（string，ISO 8601）：创建时间

---

### POST /api/contracts/changelog

创建变更记录。

请求：`POST /api/contracts/changelog`
```json
{
  "target_type": "contract",
  "target_id": "abc-123",
  "content": "续费至 2027 年"
}
```

响应（201 Created）：
```json
{
  "id": "log-uuid-1",
  "content": "续费至 2027 年",
  "created_at": "2026-07-03T10:30:00"
}
```

HTTP 状态码：201

关键字段：
- `target_type`（string，必填）：`contract` 或 `rental`
- `target_id`（string，必填）：目标 ID
- `content`（string，必填）：变更内容

---

## 发送日志 (EmailLog)

### GET /api/logs

获取邮件日志列表，支持按租赁记录、触发类型、状态过滤。

请求：`GET /api/logs?rental_id=&trigger_type=provision&status=failed&page=1&page_size=20`

查询参数：
- `rental_id`（string，可选）
- `trigger_type`（string，可选）：`provision | expiry_warning | expiry_notice | reclaim`
- `status`（string，可选）：`sent | failed`
- `page`（int，默认 1）
- `page_size`（int，默认 20，最大 100）

响应：
```json
{
  "items": [
    {
      "id": "fd5c7b52-c2a6-4e9d-8fd4-85687a2911bc",
      "rental_id": "cef1e7f7-8118-4af6-87af-9dc9955d9f90",
      "template_id": "00bef557-259c-48fa-9173-54426b028336",
      "trigger_type": "provision",
      "recipient": "zhang@keji.com",
      "recipient_type": "to",
      "subject": "【CronMail】您的服务器 Dell R740 已开通",
      "status": "failed",
      "error_msg": "发送失败：[Errno 111] Connection refused",
      "sent_at": null,
      "created_at": "2026-06-24T11:17:45.741813"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

关键字段：
- `items[].status`（string）：`sent` 或 `failed`
- `items[].error_msg`（string|null）：失败原因
- `items[].extra_data`（object|null）：合并发送时的关联信息，包含 `rental_ids`（关联设备ID列表）、`to_emails`、`cc_emails`

---

### GET /api/logs/{id}

获取邮件日志详情，包含完整邮件正文 `body`。

请求：`GET /api/logs/{id}`

响应：同列表项 + `body` 字段（HTML 邮件正文）。

HTTP 状态码：200

错误：
- 404：`{"detail": "日志不存在"}`

---

### POST /api/logs/{id}/resend

重发失败的邮件。

请求：`POST /api/logs/{id}/resend`

响应（成功）：
```json
{
  "success": true,
  "message": "邮件重发成功",
  "email_log_id": "uuid"
}
```

响应（失败）：
```json
{
  "success": false,
  "message": "重发失败: Connection refused",
  "email_log_id": "uuid"
}
```

HTTP 状态码：200

重发逻辑：
1. 找到 log 对应的 rental record
2. 重新渲染模板 → 重新发送给同一个收件人
3. 成功则更新 log status 为 sent；失败则更新 error_msg

错误：
- 404：`{"detail": "日志不存在"}`
- 422：`{"detail": "该邮件已发送成功，无需重发"}`
- 400：`{"detail": "SMTP 配置不存在，请先配置 SMTP"}`

---

## 合同管理 (Contract)

### POST /api/contracts

创建合同，可同时关联设备和联系人。

请求：`POST /api/contracts`
```json
{
  "customer_id": "1b995881-437b-4295-a4d3-0084c70dbf5c",
  "name": "4090算力租赁",
  "contract_no": "GYJY-001",
  "start_date": "2026-06-29",
  "end_date": "2026-07-06",
  "billing_model": "monthly",
  "rental_ids": ["e8fa71bd-82bd-4e2f-b6dd-b459d80e18b0", "44dc99cb-de64-4156-bb84-6e45b450cd5f"],
  "contacts": [
    {"contact_id": "3ce064c5-5d08-4d19-999f-aadffe99b335", "recipient_type": "to"},
    {"contact_id": "3ce064c5-5d08-4d19-999f-aadffe99b335", "recipient_type": "cc"}
  ]
}
```

响应（201 Created）：
```json
{
  "id": "0f94afd6-a801-4712-9121-96c0e95e41d3",
  "customer_id": "1b995881-437b-4295-a4d3-0084c70dbf5c",
  "customer_name": "江苏东蓝信息技术有限公司",
  "name": "4090算力租赁",
  "contract_no": "GYJY-001",
  "start_date": "2026-06-29",
  "end_date": "2026-07-06",
  "billing_model": "monthly",
  "status": "active",
  "remark": null,
  "rental_count": 2,
  "contact_count": 1,
  "created_at": "2026-06-29T20:10:46",
  "updated_at": "2026-06-29T20:10:46",
  "rentals": [
    {"id": "44dc99cb-de64-4156-bb84-6e45b450cd5f", "machine_model": "R8428A12", "private_ip": "192.168.100.125", "public_ips": ["116.169.215.245"], "os_version": "Ubuntu 22.04 TLS", "status": "租赁中", "rack_location": "E09-18U"},
    {"id": "e8fa71bd-82bd-4e2f-b6dd-b459d80e18b0", "machine_model": "R8428A12", "private_ip": "192.168.100.124", "public_ips": ["116.169.215.244"], "os_version": "Ubuntu 22.04 TLS", "status": "租赁中", "rack_location": "E09-24U"}
  ],
  "contacts": [
    {"contact_id": "3ce064c5-5d08-4d19-999f-aadffe99b335", "name": "吴浩", "email": "wuhao@xhwltech.com", "recipient_type": "cc"},
    {"contact_id": "3ce064c5-5d08-4d19-999f-aadffe99b335", "name": "吴浩", "email": "wuhao@xhwltech.com", "recipient_type": "to"}
  ]
}
```

HTTP 状态码：201

关键字段：
- `rental_ids`（array, optional）：关联设备 ID 列表，创建后设备状态自动变为"租赁中"
- `contacts`（array, optional）：联系人列表，支持同一联系人在同一合同中同时作为 to 和 cc（`recipient_type` 区分）
- `billing_model`（string）：计费方式，枚举 `monthly | quarterly | yearly`
- 设备关联去重：同一设备只能关联一个合同（`contract_rental.rental_id` 有唯一约束），重复关联会跳过
- 联系人去重：按 `(contact_id, recipient_type)` 去重，同一联系人 + 同一角色只存一条

错误：
- 409：`{"detail": "设备 xxx 已被其他合同关联"}`
- 422：`{"detail": "..."}`（参数校验失败）
