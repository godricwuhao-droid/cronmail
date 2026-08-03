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

## 智能合同解析 (Contract Parser)

### POST /api/contracts/parse

上传合同文件，AI 自动提取关键字段。**所有格式统一走 Vision 多模态图片识别。**

**支持的文件格式：**
- `.doc` / `.docx` — Word 文档（通过 document-converter 服务转为 PDF → 逐页拆图 → Vision LLM）
- `.pdf` — PDF 文档（逐页拆图 → Vision LLM）

**处理流程：**
```
.doc/.docx → document-converter (LibreOffice) → PDF → pdf2image 逐页拆图 → Vision LLM → JSON
.pdf → pdf2image 逐页拆图 → Vision LLM → JSON
```

请求：`POST /api/contracts/parse?contract_type=project`

请求参数：
- `file`（form-data, file, 必填）：上传的合同文件（最大 10MB）
- `contract_type`（query, string, 必填）：合同类型，`compute_leasing` / `satellite_data` / `compute_service` / `project`

**处理模式：累进式 Vision 管道**（逐页分析 + 上下文累积 + 最终汇总）

响应（PDF 实际测试结果）：
```json
{
  "fields": {
    "name": "Smart City AI Computing Platform Contract",
    "contract_no": "TEST-2025-001",
    "party_a_name": "Fengyun Times Technology Co., Ltd.",
    "party_b_name": "Anhui Tianshu Technology Co., Ltd.",
    "amount": "1500000.00",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "project_name": "Smart City AI Computing Platform",
    "contract_content": "Computing services including CPU and GPU containers",
    "service_lines": [
      {
        "category": "Computing Service",
        "item_name": "General CPU Container",
        "vcpu_count": 32,
        "memory_gb": 64,
        "gpu_count": 0,
        "unit": "unit/month",
        "quantity": 10,
        "unit_price": 5000
      }
    ]
  },
  "processing_info": {
    "file_size_kb": 2.1,
    "mode": "vision",
    "file_type": "pdf",
    "pdf_pages": 2,
    "extract_seconds": 0.4
  },
  "timing": {
    "pdf_to_images": {"seconds": 0.4, "pages": 2},
    "per_page": [
      {"page": 1, "seconds": 1.5, "found_fields": ["name", "contract_no", "party_a_name", "party_b_name", "amount", "start_date", "end_date", "project_name"]},
      {"page": 2, "seconds": 1.8, "found_fields": ["contract_content", "service_lines"]}
    ],
    "total_vision": {"seconds": 3.7}
  },
  "page_results": [
    {"page": 1, "seconds": 1.5, "found_fields": ["name", "contract_no", "party_a_name", "party_b_name", "amount", "start_date", "end_date", "project_name"]},
    {"page": 2, "seconds": 1.8, "found_fields": ["contract_content", "service_lines"]}
  ]
}
```

HTTP 状态码：200

关键字段：
- `fields.name`（string|null）：合同名称
- `fields.contract_no`（string|null）：合同编号
- `fields.party_a_name`（string|null）：甲方名称
- `fields.party_b_name`（string|null）：乙方名称
- `fields.amount`（number）：合同总金额，仅数字
- `fields.start_date`（string|null）：合同开始日期 YYYY-MM-DD
- `fields.end_date`（string|null）：合同结束日期 YYYY-MM-DD
- `fields.project_name`（string|null）：所属项目名称
- `fields.contract_content`（string|null）：合同主要内容概述
- `fields.delivery_requirements`（string|null）：交付要求
- `fields.remark`（string|null）：备注
- `fields.service_lines`（array）：服务行列表（表格数据），每行含 category/item_name/specification(JSON，含vcpu/内存/存储/GPU/带宽等规格参数)/unit/quantity/period_months/unit_price/service_description
- `fields.resource_summary`（object）：资源汇总，含 summary_text（总体概述）和 by_category[{category, resources}] 分组汇总描述
- `processing_info.mode`（string）：固定为 `"vision"`
- `processing_info.file_type`（string）：原始文件类型（doc/docx/pdf）
- `processing_info.converted_from`（string，仅 Word 文件）：原始格式（doc/docx），表示经过了转换
- `processing_info.pdf_pages`（int）：PDF 页数
- `processing_info.extract_seconds`（number）：PDF 转图片耗时（秒）
- `timing.pdf_to_images`（object）：PDF 转图片耗时 `{seconds, pages}`
- `timing.per_page`（array）：逐页 LLM 调用耗时，每项含 `page`（页码）、`seconds`（该页耗时）、`found_fields`（该页发现的字段名列表）
- `timing.final_summary`（object，仅 >3 页时出现）：最终汇总耗时 `{seconds}`
- `timing.total_vision`（object）：Vision 管道总耗时 `{seconds}`
- `page_results`（array）：每页分析记录，同 `timing.per_page`，方便前端展示逐页进度

错误：
- 400：`{"detail": "不支持的文件格式: .xxx，支持 .doc / .docx / .pdf"}` — 不支持的文件类型
- 400：`{"detail": "PDF 图片转换失败: ..."}` — PDF 转换图片失败
- 400：`{"detail": "PDF 无有效页面"}` — PDF 为空
- 413：`{"detail": "文件大小超过 10MB 限制"}`
- 502：`{"detail": "文档转换失败: ..."}` — document-converter 服务不可用或转换失败
- 502：`{"detail": "AI 解析服务暂时不可用: ..."}` — LLM 调用失败

---

### POST /api/contracts/parse/stream

SSE 流式解析合同：每完成一页推送一次事件（含图片 base64），前端实时展示。

请求：`POST /api/contracts/parse/stream?contract_type=project`

请求参数：
- `file`（form-data, file, 必填）：上传的合同文件（最大 10MB）
- `contract_type`（query, string, 必填）：合同类型，`compute_leasing` / `satellite_data` / `compute_service` / `project`

响应类型：`text/event-stream`（SSE）

SSE 事件流示例：
```
event: progress
data: {"step":"pdf_to_images","pages":5,"seconds":1.2}

event: page
data: {"page":1,"total":5,"seconds":2.3,"found_fields":["name","contract_no","party_a_name"],"image_base64":"/9j/4AAQ..."}

event: page
data: {"page":2,"total":5,"seconds":1.8,"found_fields":["amount","start_date"],"image_base64":"/9j/4AAQ..."}

...

event: progress
data: {"step":"final_summary","seconds":2.1}

event: done
data: {"fields":{"name":"合同名称","contract_no":"C-2025-001","party_a_name":"甲方公司","party_b_name":"乙方公司","amount":"1500000.00","start_date":"2025-01-01","end_date":"2025-12-31","project_name":"项目名","contract_content":"...","service_lines":[...],"resource_summary":{...},"_processing_info":{"mode":"vision","file_size_kb":120.5,"file_type":"pdf","elapsed_seconds":15.3}}}
```

SSE 事件类型说明：
| 事件类型 | 说明 |
|---------|------|
| `progress` | 处理进度通知，`data.step` 为 `pdf_to_images`（PDF 转图片完成）或 `final_summary`（最终汇总完成） |
| `page` | 单页分析完成，含 `page`（页码）、`total`（总页数）、`seconds`（该页耗时）、`found_fields`（本页发现的字段）、`image_base64`（该页 JPEG base64 图片） |
| `done` | 全部分析完成，`data.fields` 含完整提取结果 |
| `error` | 处理出错，`data.message` 含错误信息 |

关键字段：
- `page` 事件中 `image_base64`（string）：该页的 JPEG 图片 base64 编码，可直接用于 `<img src="data:image/jpeg;base64,...">`
- `page` 事件中 `found_fields`（array）：本页新发现的字段名列表
- `done` 事件中 `data.fields`（object）：完整的合同字段提取结果，结构与 `/parse` 接口的 `fields` 一致
- `done` 事件中 `data.fields._processing_info`（object）：处理元信息，含 `mode`、`file_size_kb`、`file_type`、`elapsed_seconds`

HTTP 状态码：200（SSE 流），413（文件过大）

错误事件示例：
```
event: error
data: {"message":"不支持的文件格式: .txt，支持 .doc / .docx / .pdf"}
```

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
      "id": "660fb9b1-7e84-4371-8cbe-80ae307a9bad",
      "customer_id": "dccb2936-081a-4f64-9c85-4d10cde5419e",
      "customer_name": "测试客户公司",
      "name": "测试原合同",
      "contract_no": null,
      "start_date": "2026-01-01",
      "end_date": "2026-06-30",
      "billing_model": "monthly",
      "status": "reclaimed",
      "amount": null,
      "remark": null,
      "rental_count": 0,
      "contact_count": 0,
      "renewed_from_id": null,
      "renewal_seq": 0,
      "has_renewal": true,
      "created_at": "2026-07-10T17:43:32.534350",
      "updated_at": "2026-07-10T17:43:37.252320"
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
- `items[].renewed_from_id`（string|null）：续期来源合同ID，null 表示非续期合同
- `items[].renewal_seq`（int|null）：续期序号（列表固定为 0，详情返回真实值）
- `items[].has_renewal`（bool）：是否已被后续合同续期

---

### POST /api/contracts

创建合同，可同时关联设备和联系人。支持续期（传入 `renewed_from_id`）。

请求（普通创建）：`POST /api/contracts`
```json
{
  "customer_id": "dccb2936-081a-4f64-9c85-4d10cde5419e",
  "name": "测试原合同",
  "start_date": "2026-01-01",
  "end_date": "2026-06-30",
  "billing_model": "monthly",
  "amount": 10000
}
```

请求（续期创建）：`POST /api/contracts`
```json
{
  "customer_id": "dccb2936-081a-4f64-9c85-4d10cde5419e",
  "name": "测试续期合同-第1次",
  "start_date": "2026-07-01",
  "end_date": "2026-12-31",
  "billing_model": "monthly",
  "amount": 12000,
  "renewed_from_id": "660fb9b1-7e84-4371-8cbe-80ae307a9bad"
}
```

响应（201）：
```json
{
  "id": "5321c249-d262-4513-b48d-94b29b68167e",
  "customer_id": "dccb2936-081a-4f64-9c85-4d10cde5419e",
  "customer_name": "测试客户公司",
  "name": "测试续期合同-第1次",
  "contract_no": null,
  "start_date": "2026-07-01",
  "end_date": "2026-12-31",
  "billing_model": "monthly",
  "status": "active",
  "amount": null,
  "remark": null,
  "rental_count": 0,
  "contact_count": 0,
  "renewed_from_id": "660fb9b1-7e84-4371-8cbe-80ae307a9bad",
  "renewal_seq": 1,
  "has_renewal": false,
  "created_at": "2026-07-10T17:43:37.253120",
  "updated_at": "2026-07-10T17:43:37.253133",
  "rentals": [],
  "contacts": [],
  "renewal_chain": [
    {
      "id": "660fb9b1-7e84-4371-8cbe-80ae307a9bad",
      "name": "测试原合同",
      "status": "reclaimed",
      "start_date": "2026-01-01",
      "end_date": "2026-06-30",
      "is_current": false,
      "renewal_seq": 0
    },
    {
      "id": "5321c249-d262-4513-b48d-94b29b68167e",
      "name": "测试续期合同-第1次",
      "status": "active",
      "start_date": "2026-07-01",
      "end_date": "2026-12-31",
      "is_current": true,
      "renewal_seq": 1
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
- `renewed_from_id`（string，可选）：续期来源合同ID，传入即表示续期创建
- `rental_ids`（array，可选）：创建时关联的设备 ID 列表
- `contacts`（array，可选）：创建时关联的联系人列表，每项含 `contact_id` 和 `recipient_type`（"to"/"cc"）。后端自动按 `(contact_id, recipient_type)` 去重，重复项只保留第一条
- `renewed_from_id`（string|null）：续期来源合同ID，null 表示非续期
- `renewal_seq`（int）：续期序号，0=原合同，1=第一次续期，...
- `has_renewal`（bool）：是否已被后续合同续期
- `renewal_chain`（array）：续期链路，从原始合同到当前合同的所有节点

续期行为：
1. 传入 `renewed_from_id` 时，校验原合同存在且未被续期
2. 原合同自动标记为 `reclaimed`
3. 若传入 `rental_ids`，设备关联从原合同迁移到新合同，原合同保留设备ID快照

错误：
- 404：`{"detail": "客户不存在"}`
- 404：`{"detail": "续期来源合同不存在"}`
- 409：`{"detail": "该合同已被续期"}` — 同一合同只能被续期一次

---

### GET /api/contracts/{id}

获取合同详情，包含关联设备、联系人列表、续期链路。

请求：`GET /api/contracts/660fb9b1-7e84-4371-8cbe-80ae307a9bad`

响应：同 POST 响应格式，包含 `rentals`、`contacts`、`renewal_chain` 数组。

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

### GET /api/contracts/dashboard/overview-stats

获取运营概览图表统计数据（客户设备二维细分、机器型号分布、近12个月合同趋势）。

请求：`GET /api/contracts/dashboard/overview-stats`

响应：
```json
{
  "rental_by_customer": [
    {
      "customer_name": "A公司",
      "models": [
        {"machine_model": "4090", "count": 8},
        {"machine_model": "CPU6133", "count": 2}
      ]
    }
  ],
  "rental_by_model": [
    {"machine_model": "Dell R740", "count": 8}
  ],
  "contract_trend": [
    {"month": "2025-08", "created_count": 3, "expired_count": 1}
  ]
}
```

HTTP 状态码：200

关键字段：
- `rental_by_customer`（array）：各客户租赁中设备 TOP 10（按总设备数降序），每项含：
  - `customer_name`（string）：客户名称
  - `models`（array）：该客户下各机型的设备数量，每项含 `machine_model`（string）和 `count`（int）
- `rental_by_model`（array）：机器型号分布 TOP 10，每项含 `machine_model`（string）和 `count`（int）
- `contract_trend`（array）：近 12 个月合同趋势，每项含 `month`（string，格式 YYYY-MM）、`created_count`（int，当月新签合同数）、`expired_count`（int，当月到期合同数）

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

## 卫星数据合同 (SatelliteDataContract)

### GET /api/satellite-data-contracts

列表，支持 `?search=&customer_id=&page=&page_size=`

请求：`GET /api/satellite-data-contracts?page=1&page_size=20`

响应：
```json
{
  "items": [
    {
      "id": "55ddb5f9-343f-40bc-bb05-65887d53ac2d",
      "customer_id": "b2e9b24d-ed5b-42c9-9fdb-d5b9a358fcc7",
      "customer_name": "测试客户A",
      "name": "卫星数据合同-001",
      "contract_no": "WX-2026-001",
      "remark": "测试",
      "contract_type": null,
      "project_name": null,
      "party_a_name": null,
      "party_b_name": null,
      "start_date": null,
      "end_date": null,
      "amount": null,
      "contract_content": null,
      "delivery_requirements": null,
      "process_records": null,
      "created_at": "2026-07-03T17:20:04.572277",
      "updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

关键字段：
- `items`（array）：合同列表，含 `customer_name`（关联查询）
- `total`（int）：总数
- `contract_type`（string|null，ADR-013 新增）：合同子类型
- `project_name`（string|null，ADR-013 新增）：所属项目
- `party_a_name`（string|null，ADR-013 新增）：甲方名称
- `party_b_name`（string|null，ADR-013 新增）：乙方名称
- `start_date`（date|null，ADR-013 新增）：服务开始日期
- `end_date`（date|null，ADR-013 新增）：服务结束日期
- `amount`（decimal|null，ADR-013 新增）：合同金额
- `contract_content`（string|null，ADR-013 新增）：合同内容
- `delivery_requirements`（string|null，ADR-013 新增）：合同交付要求
- `process_records`（string|null，ADR-013 新增）：过程记录

### POST /api/satellite-data-contracts

请求（所有 ADR-013 新增字段均为可选）：
```json
{
  "customer_id": "uuid",
  "name": "卫星数据合同-001",
  "contract_no": "WX-2026-001",
  "remark": "",
  "contract_type": "data_purchase",
  "project_name": "项目Alpha",
  "party_a_name": "甲方公司",
  "party_b_name": "乙方公司",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "amount": "100000.00",
  "contract_content": "合同内容描述",
  "delivery_requirements": "交付要求描述",
  "process_records": "过程记录"
}
```

响应（201）：
```json
{
  "id": "55ddb5f9-343f-40bc-bb05-65887d53ac2d",
  "customer_id": "b2e9b24d-ed5b-42c9-9fdb-d5b9a358fcc7",
  "customer_name": "测试客户A",
  "name": "卫星数据合同-001",
  "contract_no": "WX-2026-001",
  "remark": "测试",
  "contract_type": "data_purchase",
  "project_name": "项目Alpha",
  "party_a_name": "甲方公司",
  "party_b_name": "乙方公司",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "amount": "100000.00",
  "contract_content": "合同内容描述",
  "delivery_requirements": "交付要求描述",
  "process_records": "过程记录",
  "created_at": "2026-07-03T17:20:04.572277",
  "updated_at": null
}
```

HTTP 状态码：201

### GET /api/satellite-data-contracts/{id}

响应格式同 POST 响应，包含所有 ADR-013 新增字段。

HTTP 状态码：200

### PUT /api/satellite-data-contracts/{id}

请求：所有字段均为可选，只更新传入的字段。ADR-013 新增的 10 个字段同样支持部分更新。

HTTP 状态码：200

### DELETE /api/satellite-data-contracts/{id}

响应：
```json
{"detail": "合同已删除"}
```

HTTP 状态码：200

---

## 算力服务合同 (ComputeServiceContract)

### GET /api/compute-service-contracts

列表，支持 `?search=&customer_id=&page=&page_size=`

请求：`GET /api/compute-service-contracts?page=1&page_size=20`

响应：
```json
{
  "items": [
    {"id": "189d753f-633a-4891-b421-5116282ffd6d", "customer_id": "b2e9b24d-ed5b-42c9-9fdb-d5b9a358fcc7", "customer_name": "测试客户A", "name": "算力服务合同-001", "contract_no": "FW-2026-001", "remark": null, "created_at": "2026-07-03T17:20:04.579058", "updated_at": null}
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

### POST /api/compute-service-contracts

请求：
```json
{"customer_id": "uuid", "name": "算力服务合同-001", "contract_no": "FW-2026-001", "remark": ""}
```

HTTP 状态码：201

### GET /api/compute-service-contracts/{id}

### PUT /api/compute-service-contracts/{id}

### DELETE /api/compute-service-contracts/{id}

---

## 合同 Excel 导出

三类合同均支持全量导出为 Excel 文件（.xlsx），复用列表筛选条件，不分页。

### GET /api/contracts/export

导出算力租赁合同列表为 Excel。

请求：`GET /api/contracts/export?customer_id=&status=active&search=算力`

查询参数：
- `customer_id`（string，可选）：按客户过滤
- `status`（string，可选）：`active | expiring | expired | reclaimed`
- `search`（string，可选）：按合同名称模糊搜索

响应：`.xlsx` 文件流，表头为 14 列中文标题，含浅蓝色背景和边框。

Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
Content-Disposition: `attachment; filename*=UTF-8''...`

Excel 表头：序号 | 所属类型 | 合同名称 | 合同类型 | 所属项目 | 甲方 | 乙方 | 服务开始 | 服务结束 | 合同金额（元） | 合同编号 | 合同内容 | 合同交付要求 | 过程记录

关键字段映射：
- `合同类型`：billing_model → 月付/季付/年付
- `所属类型`：固定值 "算力租赁"
- 所属项目/甲方/乙方/合同内容/合同交付要求/过程记录：算力租赁暂无，导出为空

HTTP 状态码：200

---

### GET /api/satellite-data-contracts/export

导出卫星数据合同列表为 Excel。

请求：`GET /api/satellite-data-contracts/export?customer_id=&search=卫星`

查询参数：
- `customer_id`（string，可选）
- `search`（string，可选）

响应：`.xlsx` 文件流，14 列，同上述表头。

关键字段映射：
- `所属类型`：固定值 "卫星数据"

HTTP 状态码：200

---

### GET /api/compute-service-contracts/export

导出算力服务合同列表为 Excel。

请求：`GET /api/compute-service-contracts/export?customer_id=&search=服务`

查询参数：
- `customer_id`（string，可选）
- `search`（string，可选）

响应：`.xlsx` 文件流，14 列，同上述表头。

关键字段映射：
- `合同类型`：contract_type → 销售/采购
- `所属类型`：固定值 "算力服务"

HTTP 状态码：200

---

## 算力服务合同 - 服务行 (Service Lines)

### GET /api/compute-service-contracts/{contract_id}/service-lines

获取合同的服务行列表。

请求：`GET /api/compute-service-contracts/{contract_id}/service-lines`

响应：
```json
[
  {
    "id": "uuid",
    "contract_id": "uuid",
    "category": "计算服务",
    "item_name": "GPU服务器",
    "specification": null,
    "vcpu_count": null,
    "memory_gb": null,
    "storage_gb": null,
    "unit": "台",
    "quantity": "2",
    "period_months": 12,
    "unit_price": "1000.00",
    "total_price": "24000.00",
    "manual_total_price": null,
    "sort_order": 0,
    "service_description": null,
    "gpu_count": null,
    "gpu_model": null,
    "gpu_memory_gb": null,
    "gpu_tops": null,
    "created_at": "2026-07-03T17:20:04.579058"
  }
]
```

HTTP 状态码：200

关键字段：
- `manual_total_price`（decimal|null）：手动覆盖总价，null 表示自动计算
- `total_price`（decimal）：最终总价（手动值或自动计算结果）

### POST /api/compute-service-contracts/{contract_id}/service-lines

新增服务行。`manual_total_price` 不传则自动计算（quantity × period_months × unit_price），传入则使用手动值。

请求：
```json
{
  "category": "计算服务",
  "item_name": "GPU服务器",
  "unit": "台",
  "quantity": "2",
  "period_months": 12,
  "unit_price": "1000.00",
  "manual_total_price": null,
  "sort_order": 0
}
```

HTTP 状态码：201

### PUT /api/compute-service-contracts/{contract_id}/service-lines/{line_id}

更新服务行。传 `manual_total_price` 为非 null 值则手动覆盖；传 `null` 则清回自动计算；不传该字段则自动重算（基于 quantity/period_months/unit_price）。

请求：
```json
{
  "manual_total_price": "9999.00"
}
```

HTTP 状态码：200

### DELETE /api/compute-service-contracts/{contract_id}/service-lines/{line_id}

HTTP 状态码：200

### POST /api/compute-service-contracts/{contract_id}/service-lines/batch

批量保存（全量替换）。`ContractServiceLineCreate` 数组中每项的 `manual_total_price` 同样支持手动覆盖。

请求：
```json
{
  "lines": [
    {"category": "...", "item_name": "...", "unit": "台", "quantity": "2", "period_months": 12, "unit_price": "1000.00", "manual_total_price": null}
  ]
}
```

HTTP 状态码：201

---

## 附件分类管理 (System - Attachment Categories)

### GET /api/system/attachment-categories?contract_type=compute_leasing

请求：`GET /api/system/attachment-categories?contract_type=compute_leasing`

响应：
```json
{
  "items": [
    {
      "id": "145a0a06-e84f-4053-b85a-3c37120d7635",
      "contract_type": "compute_leasing",
      "name": "合同协议",
      "code": "contract_agreement",
      "sort_order": 1,
      "is_active": true,
      "items": [
        {"id": "fa3e0431-51b9-4ece-a946-67adbe6a4e22", "name": "合同扫描件", "description": "合同扫描件PDF", "expected_type": "pdf", "sort_order": 1, "is_active": true}
      ],
      "created_at": "2026-07-03T17:20:04.226854"
    }
  ]
}
```

HTTP 状态码：200

关键字段：
- `items[].items`（array）：分类下的子项列表
- `contract_type`（string）：合同类型 compute_leasing / satellite_data / compute_service

### POST /api/system/attachment-categories

请求：
```json
{"contract_type": "satellite_data", "name": "合同协议", "code": "contract_agreement", "sort_order": 1}
```

HTTP 状态码：201

### PUT /api/system/attachment-categories/{id}

### DELETE /api/system/attachment-categories/{id}

软删除（设 is_active=false）。

### PUT /api/system/attachment-categories/{id}/reorder

请求：
```json
{"sort_order": 2}
```

### POST /api/system/attachment-categories/{category_id}/items

请求：
```json
{"name": "数据交付报告", "description": "...", "expected_type": "pdf", "sort_order": 1}
```

HTTP 状态码：201

### PUT /api/system/attachment-items/{item_id}

### DELETE /api/system/attachment-items/{item_id}

软删除（设 is_active=false）。

### PUT /api/system/attachment-items/{item_id}/reorder

请求：
```json
{"sort_order": 2}
```

---

## 附件文件 (Attachment)

### GET /api/attachments?contract_type=satellite_data&contract_id={id}

按合同获取附件列表（分类+子项结构）。

请求：`GET /api/attachments?contract_type=satellite_data&contract_id=55ddb5f9-343f-40bc-bb05-65887d53ac2d`

响应：
```json
{
  "categories": [
    {
      "category_id": "e586b648-0c8c-479f-baa0-9457024fdfc9",
      "category_name": "合同协议",
      "items": [
        {
          "item_id": "dede9939-dff2-4eea-a057-65877bd1445e",
          "item_name": "合同扫描件",
          "expected_type": "pdf",
          "files": [],
          "file_count": 0,
          "confirmed": false,
          "confirmed_at": null
        }
      ]
    }
  ]
}
```

HTTP 状态码：200

关键字段：
- `categories[].items[].files`（array）：文件列表，每个文件含 id/filename/file_size/mime_type/uploaded_at
- `categories[].items[].file_count`（int）：文件数量
- `categories[].items[].confirmed`（bool）：是否已确认完成

### POST /api/attachments/upload?contract_type={type}&contract_id={id}&item_id={id}

multipart/form-data，字段 `files`（可多文件上传）。

响应：
```json
{"attachments": [{"id": "uuid", "filename": "xxx.pdf", "file_size": 2048000, "mime_type": "application/pdf", "uploaded_at": "..."}]}
```

HTTP 状态码：200

关键字段：
- `files`（file, required）：上传文件，支持多文件（前端字段名 `files`）
- 文件大小限制：50MB
- 存储路径：`/app/uploads/{contract_type}/{contract_id}/{item_id}/{uuid}.ext`

### GET /api/attachments/{id}/download

返回文件流，`Content-Disposition` 使用 RFC 5987 编码（`filename*=UTF-8''...`），支持中文文件名。

响应头：
- `Content-Type`: 文件的 MIME 类型（如 `application/pdf`），未知类型回退为 `application/octet-stream`
- `Content-Disposition`: `attachment; filename="{ascii_fallback}"; filename*=UTF-8''{url_encoded_filename}`

错误码：
- `404`：文件不存在或已被删除

### DELETE /api/attachments/{id}

响应：
```json
{"detail": "文件已删除"}
```

HTTP 状态码：200

---

### GET /api/attachments/export

一键导出合同所有附件为 ZIP 包。目录结构从数据库动态读取分类和子项名称，不硬编码。

请求：`GET /api/attachments/export?contract_type=compute_leasing&contract_id={contract_id}`

查询参数：
- `contract_type`（string，必填）：合同类型，枚举 `compute_leasing` | `satellite_data` | `compute_service`
- `contract_id`（string，必填）：合同 ID

响应：
- 成功：返回 ZIP 文件流，`Content-Type: application/zip`，`Content-Disposition` 使用 RFC 5987 编码
- 下载文件名格式：`{合同名称}_附件_{YYYY-MM-DD}.zip`

ZIP 内部目录结构（动态）：
```
{合同名称}/
├── {分类名1}/          ← 来自 AttachmentCategory.name，运行时动态
│   ├── {子项名1}/       ← 来自 AttachmentItem.name
│   │   ├── file1.pdf
│   │   └── file2.docx
│   └── {子项名2}/
│       └── report.xlsx
└── {分类名2}/
    └── ...
```

HTTP 状态码：200

错误码：
- `404`：`{"detail": "合同不存在"}` — contract_type + contract_id 在对应合同表中未找到
- `404`：`{"detail": "该合同类型下无附件分类，请先在系统配置中配置"}` — AttachmentCategory 表中无该类型的活跃分类
- `404`：`{"detail": "该合同下无附件文件"}` — 所有分类/子项下均无附件文件

关键行为：
- 仅包含 `is_active=True` 的分类和子项
- 无文件的子项自动跳过（不创建空目录）
- 同一子项下重名文件自动加序号后缀：`file.pdf` → `file(2).pdf`、`file(3).pdf`
- 文件名含非法字符（`\ / : * ? " < > |`）时自动替换为下划线 `_`
- 磁盘上已不存在的文件自动跳过

---

## 附件完成确认

### GET /api/attachments/status/summary?contract_type={type}&contract_id={id}

返回该合同所有分类的完成汇总。

请求：`GET /api/attachments/status/summary?contract_type=satellite_data&contract_id=55ddb5f9-343f-40bc-bb05-65887d53ac2d`

响应：
```json
{
  "total_items": 4,
  "confirmed_items": 0,
  "all_confirmed": false,
  "items": {
    "contract_agreement": {"confirmed": false, "file_count": 0},
    "acceptance_material": {"confirmed": false, "file_count": 0},
    "process_material": {"confirmed": false, "file_count": 0}
  }
}
```

HTTP 状态码：200

关键字段：
- `total_items`（int）：总子项数
- `confirmed_items`（int）：已确认子项数
- `all_confirmed`（bool）：是否全部确认
- `items`（dict）：按分类 code 分组的确认状态

### POST /api/attachments/status/{item_id}/confirm

请求：
```json
{"contract_type": "satellite_data", "contract_id": "55ddb5f9-343f-40bc-bb05-65887d53ac2d"}
```

响应：
```json
{"confirmed": true}
```

HTTP 状态码：200

### POST /api/attachments/status/{item_id}/unconfirm

同上，响应 `{"confirmed": false}`。

---

## 项目管理合同 (Project Contract)

### GET /api/project-contracts

获取项目管理合同列表，按公司代码过滤。

请求：`GET /api/project-contracts?company=fengyun&search=&page=1&page_size=20`

响应：
```json
{
  "items": [
    {
      "id": "2bf33d62-08d3-44b1-bed6-242d475742b4",
      "company_code": "fengyun",
      "name": "风云项目测试合同",
      "contract_no": "FY-2026-001",
      "contract_type": "sales",
      "party_a_name": "甲方公司",
      "party_b_name": "乙方公司",
      "amount": "100000.00",
      "start_date": "2026-01-01",
      "end_date": "2026-12-31",
      "related_contract_id": null,
      "project_name": "风云一号项目",
      "contract_content": null,
      "delivery_requirements": null,
      "process_records": null,
      "remark": null,
      "sort_order": 0,
      "service_lines_count": 0,
      "created_at": "2026-07-28T09:00:37.731681",
      "updated_at": "2026-07-28T09:00:37.731700"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

HTTP 状态码：200

关键字段：
- `company`（query）：公司代码，必填，fengyun/tianshu/qianxing
- `search`（query）：按合同名称/编号模糊搜索
- `items[].service_lines_count`（int）：服务行数量

---

### POST /api/project-contracts

创建项目管理合同，支持内嵌 service_lines。

请求：`POST /api/project-contracts`
```json
{
  "company_code": "fengyun",
  "name": "风云项目测试合同",
  "contract_no": "FY-2026-001",
  "contract_type": "sales",
  "party_a_name": "甲方公司",
  "party_b_name": "乙方公司",
  "amount": 100000.00,
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "project_name": "风云一号项目",
  "service_lines": [
    {
      "category": "计算资源",
      "item_name": "GPU服务器",
      "specification": {"gpu_count": 8, "gpu_model": "A100", "vcpu": 64, "memory_gb": 512},
      "unit": "台",
      "quantity": 10,
      "period_months": 12,
      "unit_price": 5000.00
    }
  ]
}
```

响应：
```json
{
  "id": "2bf33d62-...",
  "company_code": "fengyun",
  "name": "风云项目测试合同",
  "contract_no": "FY-2026-001",
  "contract_type": "sales",
  "party_a_name": "甲方公司",
  "party_b_name": "乙方公司",
  "amount": "600000.00",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "related_contract_id": null,
  "project_name": "风云一号项目",
  "contract_content": null,
  "delivery_requirements": null,
  "process_records": null,
  "remark": null,
  "sort_order": 0,
  "service_lines": [
    {
      "id": "...",
      "contract_id": "...",
      "category": "计算资源",
      "item_name": "GPU服务器",
      "specification": {"gpu_count": 8, "gpu_model": "A100", "vcpu": 64, "memory_gb": 512},
      "unit": "台",
      "quantity": "10",
      "period_months": 12,
      "unit_price": "5000.00",
      "total_price": "600000.00",
      "sort_order": 0,
      "service_description": null,
      "created_at": "..."
    }
  ],
  "related_contract": null,
  "amount_auto_calc": "600000.00",
  "created_at": "...",
  "updated_at": "..."
}
```

HTTP 状态码：201

关键字段：
- `amount`：可选，不填则自动 SUM(service_lines.total_price)
- `service_lines`：可选，创建时内嵌服务行
- `amount_auto_calc`：自动汇总金额（response only）

---

### GET /api/project-contracts/{id}

获取项目管理合同详情。

请求：`GET /api/project-contracts/2bf33d62-...`

响应格式同 POST 创建响应，HTTP 状态码：200

---

### PUT /api/project-contracts/{id}

更新项目管理合同，支持 service_lines 全量替换。

请求：`PUT /api/project-contracts/2bf33d62-...`
```json
{
  "project_name": "风云一号项目-更新",
  "service_lines": [...]
}
```

响应格式同 POST 创建响应，HTTP 状态码：200

---

### DELETE /api/project-contracts/{id}

删除项目管理合同（级联删除 service_lines）。

请求：`DELETE /api/project-contracts/2bf33d62-...`

响应：
```json
{"detail": "合同已删除"}
```

HTTP 状态码：200

---

### GET /api/project-contracts/export

导出项目管理合同列表为 Excel（14列）。

请求：`GET /api/project-contracts/export?company=fengyun`

响应：Excel 文件流（`.xlsx`），Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

HTTP 状态码：200

---

### POST /api/project-contracts/{id}/service-lines/batch

批量保存服务行（全量替换：先删后插）。

请求：`POST /api/project-contracts/{id}/service-lines/batch`
```json
{
  "lines": [
    {
      "category": "计算资源",
      "item_name": "GPU服务器",
      "specification": {"gpu_count": 8, "gpu_model": "A100", "vcpu": 64},
      "unit": "台",
      "quantity": 10,
      "period_months": 12,
      "unit_price": 5000.00,
      "sort_order": 0
    }
  ]
}
```

响应：`[ProjectServiceLineResponse, ...]`，HTTP 状态码：201

---

### GET /api/project-contracts/{id}/service-lines

获取合同的所有服务行列表。

请求：`GET /api/project-contracts/{id}/service-lines`

响应：`[ProjectServiceLineResponse, ...]`，HTTP 状态码：200

---

### POST /api/project-contracts/{id}/service-lines

新增单条服务行。

请求：`POST /api/project-contracts/{id}/service-lines`，body 同 ProjectServiceLineCreate

响应：`ProjectServiceLineResponse`，HTTP 状态码：201

---

### PUT /api/project-contracts/{id}/service-lines/{line_id}

更新单条服务行。

请求：`PUT /api/project-contracts/{id}/service-lines/{line_id}`，body 同 ProjectServiceLineUpdate

响应：`ProjectServiceLineResponse`，HTTP 状态码：200

---

### DELETE /api/project-contracts/{id}/service-lines/{line_id}

删除单条服务行。

请求：`DELETE /api/project-contracts/{id}/service-lines/{line_id}`

响应：`{"detail": "服务行已删除"}`，HTTP 状态码：200
