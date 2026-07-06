# CronMail 架构全景

## 项目概述

CronMail 是一个面向裸金属服务器租赁业务的自动邮件发送平台。

### 核心功能

1. **租赁记录管理**：创建和管理服务器租赁记录，含完整硬件、网络、凭证信息
2. **客户及联系人管理**：客户维度的联系人池，支持收件人(to)和抄送(cc)选择
3. **邮件模板编辑**：Monaco 编辑器 + Jinja2 后端实时预览
4. **手动邮件发送**：开通通知、临期提醒、到期回收，均支持手动触发
5. **定时自动提醒**：Celery Beat 每天扫描到期记录，自动发送临期/回收邮件

---

## 系统上下文（C4 Level 1）

```
                    ┌──────────────────────┐
                    │      管理员           │
                    │   (浏览器访问)        │
                    └──────────┬───────────┘
                               │ HTTPS
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      CronMail 平台                          │
│                                                              │
│  ┌─────────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │   Vue 3 SPA     │  │  FastAPI    │  │  Celery Beat   │  │
│  │ (Element Plus)  │  │  REST API   │  │  + Worker      │  │
│  └────────┬────────┘  └──────┬──────┘  └───────┬────────┘  │
│           │                  │                   │           │
│           └──────────┬───────┘                   │           │
│                      │                           │           │
└──────────────────────┼───────────────────────────┼───────────┘
                       │                           │
          ┌────────────▼──────┐         ┌──────────▼─────────┐
          │      MySQL 8.0    │         │       Redis         │
          │   (业务数据)       │         │   (Celery Broker)   │
          └───────────────────┘         └────────────────────┘
                                                   │
                                       ┌───────────▼─────────┐
                                       │   企业 SMTP 服务器    │
                                       │  (自建邮件服务器)     │
                                       └────────────────────┘
                                                   │
                                       ┌───────────▼─────────┐
                                       │   钉钉 Webhook       │
                                       │  (邮件失败告警)      │
                                       └─────────────────────┘
```

---

## 容器图（C4 Level 2）

```
┌─────────────────────────────────────────────────────────────────┐
│                        CronMail Platform                        │
│                                                                 │
│  ┌───────────────────┐    HTTP/REST     ┌────────────────────┐ │
│  │  Frontend (Vue 3) │◄───────────────►│  Backend (FastAPI) │ │
│  │                   │                  │                    │ │
│  │  • 仪表盘         │                  │  • customer/       │ │
│  │  • 客户管理       │                  │  • contract/       │ │
│  │  • 合同管理       │                  │  • rental/         │ │
│  │  • 设备管理       │                  │  • template/       │ │
│  │  • 模板编辑       │                  │  • mail/           │ │
│  │  • 发送日志       │                  │  • system/         │ │
│  │  • 系统配置       │                  │  • core/           │ │
│  │  • 钉钉通知       │                  │                    │ │
│  └───────────────────┘                  └────────┬───────────┘ │
│                                                  │              │
│  ┌───────────────────┐                  ┌────────▼───────────┐ │
│  │  Celery Beat      │                  │  Celery Worker     │ │
│  │  (定时调度)        │─── 投递任务 ───►│  (异步执行)        │ │
│  │                   │                  │                    │ │
│  │  • 临期扫描 08:00 │                  │  • 发临期提醒邮件   │ │
│  │  • 到期提醒 08:00 │                  │  • 发到期提醒邮件   │ │
│  │  • 回收执行 00:01 │                  │  • 执行回收+发通知  │ │
│  └───────────────────┘                  │  • 手动邮件异步发送 │ │
│                                          └────────────────────┘ │
│                                                                 │
│  进程内通信: blinker Signal (审计/日志)                         │
│  手动发送: Celery 异步任务 send_manual_email                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 模块内部结构

每个业务模块遵循统一结构：

```
backend/src/{module}/
├── __init__.py
├── models.py         # SQLAlchemy ORM 模型
├── schemas.py        # Pydantic 请求/响应 schema
├── services.py       # 业务逻辑（核心）
├── api.py            # FastAPI 路由（仅薄层，调 service）
├── events.py         # blinker 信号定义（如有）
└── subscribers.py    # 事件订阅者（如有）
```

---

## 数据模型关系

```
Customer (客户)
  ├── id, name, code, status
  │
  ├── 1──N → Contact (联系人)
  │    ├── id, name, email, phone, department
  │    ├── customer_id (FK, NULL=内部同事)
  │    └── is_active
  │
  │
  ├── 1──N → Contract / 算力租赁合同 (contract 表)
  │    ├── id, customer_id (FK → Customer)
  │    ├── name, contract_no
  │    ├── start_date, end_date, billing_model (monthly/quarterly/yearly)
  │    ├── status(ENUM): active | expiring | expired | reclaimed
  │    ├── history_rental_ids (JSON, 回收时快照)
  │    ├── remark
  │    │
  │    ├── M──N → RentalRecord via contract_rental
  │    │    (rental_id UNIQUE, 一设备一合同)
  │    │
  │    └── M──N → Contact via contract_contact
  │         └── recipient_type(ENUM): 'to' | 'cc'
  │
  ├── 1──N → SatelliteDataContract / 卫星数据合同 (satellite_data_contract 表)
  │    └── id, customer_id, name, contract_no, remark（纯归档，无邮件流程）
  │
  └── 1──N → ComputeServiceContract / 算力服务合同 (compute_service_contract 表)
       └── id, customer_id, name, contract_no, remark（纯归档，无邮件流程）

AttachmentCategory (附件分类，运行时管理)
  ├── id, contract_type, name, code, sort_order, is_active
  │
  └── 1──N → AttachmentItem (子项清单，运行时管理)
       ├── id, name, description, expected_type (pdf/excel/image/any)
       ├── sort_order, is_active
       │
       └── 1──N → Attachment (实际文件)
            ├── id, contract_type, contract_id, item_id
            ├── filename, file_path, file_size, mime_type
            └── uploaded_at

AttachmentStatus (附件子项完成确认)
  ├── (contract_type, contract_id, item_id) 联合唯一
  ├── file_count (冗余，方便列表展示)
  ├── confirmed (管理员手动确认)
  └── confirmed_at

RentalRecord (设备)
  ├── id, customer_id (FK → Customer)
  ├── machine_model, cpu_model, memory_gb, gpu_info
  ├── system_disk_gb, data_disks(JSON)
  ├── os_version, bandwidth_mbps, rack_location
  ├── private_ip, public_ips(JSON), ssh_port
  ├── root_username, root_password_enc (Fernet)
  ├── end_date (DEPRECATED ── 以合同日期为准)
  ├── billing_model (DEPRECATED ── 以合同计费方式为准)
  ├── status(ENUM): provisioned | expiring | expired | reclaimed
  └── remark

contract_rental (中间表)
  ├── contract_id (FK → Contract)
  ├── rental_id (FK → RentalRecord, UNIQUE)
  └── added_at

contract_contact (中间表)
  ├── contract_id (FK → Contract)
  ├── contact_id (FK → Contact)
  └── recipient_type(ENUM): 'to' | 'cc'

ChangeLog (变更日志)
  ├── id, target_type (contract|rental), target_id
  ├── action, field_name, old_value, new_value
  ├── operator, created_at

EmailTemplate (邮件模板)
  ├── id, name, trigger_type(ENUM: provision|expiry_warning|expiry_notice|reclaim)
  ├── subject_tpl (TEXT, Jinja2)
  ├── body_html (TEXT, Jinja2)
  ├── signature_html (TEXT, 签名区)
  ├── variables_desc(JSON), is_active, version

EmailLog (发送日志)
  ├── id, rental_id(FK), template_id(FK)
  ├── trigger_type, recipient, recipient_type
  ├── subject, body
  ├── status(ENUM): sent | failed
  ├── error_msg, sent_at

SmtpConfig (SMTP配置)
  ├── id, host, port, username
  ├── password_enc (Fernet加密)
  ├── sender_name, sender_email, encryption (tls|starttls|none)

SystemConfig (系统配置)
  ├── key, value, description
  ├── 通知调度时间: check-expiring-rentals, check-expired-rentals, check-reclaim-expired
  ├── 临期提醒天数: expiry_warning_days (如 "7,3")
  └── 钉钉通知: dingtalk_webhook, dingtalk_secret
```

---

## 状态流转

```
                   管理员创建
                       │
                       ▼
                 ┌──────────┐
                 │ active    │ ←── 使用中
                 └─────┬────┘
                       │
         到期前 ≤N 天    │  Celery Beat 自动（N 可配置）
                       ▼
                 ┌──────────┐
                 │ expiring  │ ←── 即将到期（每天发提醒）
                 └─────┬────┘
                       │
           管理员续期    │  end_date 到达当天
           (手动更新)    │
         ┌──────────────┼──────────────┐
         ▼              │              ▼
   ┌──────────┐         │       ┌───────────┐
   │  active   │         │       │  expired   │ ←── 到期（当天发提醒）
   └──────────┘         │       └─────┬─────┘
                         │            │
                         │    Celery Beat 次日 00:01
                         │    执行回收 + 发回收通知
                         │            │
                         │            ▼
                         │     ┌────────────┐
                         │     │ reclaimed  │ ←── 已回收
                         │     └────────────┘
                         │
                         │  任何状态均可手动触发发送
                         │  （通过详情页按钮，按合同维度）
```

> 注意：状态流转以 **Contract（合同）** 为维度，而非设备。合同下所有设备共享同一状态。

---

## 关键流程

> **所有邮件发送（手动 + 定时）统一走 `send_merged_email_by_contract()` 管道。**
> 合同是邮件发送的聚合边界，一个合同一封邮件，包含该合同下所有关联设备。

### 流程 1：开通邮件发送

```
管理员创建设备并关联合同（仅入库，不发邮件）
  → 点击「发送开通邮件」
  → POST /api/rentals/{id}/send-provision-email
  → 查设备关联合同 → 得合同下所有设备
  → send_manual_email.delay(contract_id, "provision")
  → Celery Worker: send_merged_email_by_contract(contract, 'provision')
  → 一封邮件含该合同下所有设备
  → 写 EmailLog（每条设备一条）
  → 状态不变
```

### 流程 2：临期自动提醒

```
Celery Beat 每天 08:00（或手动触发）
  → 按合同维度扫描: 合同 end_date - today ≤ warning_days 且 end_date > today
  → 过滤 合同 status IN (active, expiring)
  → send_merged_email_by_contract(contract, 'expiry_warning')
  → 合同状态更新为 expiring
  → 写 EmailLog
```

### 流程 3：到期提醒

```
Celery Beat 每天 08:00
  → 按合同维度扫描: 合同 end_date = today
  → 过滤 合同 status IN (active, expiring)
  → send_merged_email_by_contract(contract, 'expiry_notice')
  → 合同状态更新为 expired
  → 写 EmailLog
```

### 流程 4：到期回收

```
Celery Beat 每天 00:01（或手动触发）
  → 按合同维度扫描: 合同 end_date < today AND status = expired
  → 快照设备 ID 到 history_rental_ids
  → send_merged_email_by_contract(contract, 'reclaim')
  → 合同+设备批量更新状态为 reclaimed
  → 写 EmailLog
```

---

## 前端路由设计

```
/                          → 重定向到 /dashboard
/dashboard                 → 仪表盘（运营概览 + 待处理提醒）
/customers                 → 客户列表
/customers/:id/contacts    → 某客户的联系人管理
/contracts                 → 合同列表
/contracts/create          → 新建合同
/contracts/:id             → 合同详情（含设备关联 + 发送按钮）
/contracts/:id/edit        → 编辑合同
/rentals                   → 设备列表
/rentals/create            → 创建设备（关联合同）
/rentals/:id               → 设备详情（含发送按钮）
/rentals/:id/edit          → 编辑设备
/templates                 → 邮件模板列表
/templates/create          → 创建模板
/templates/:id/edit        → 编辑模板（Monaco + 预览 + 测试发送）
/logs                      → 发送日志列表
/system/smtp               → SMTP 配置
/system/colleagues         → 内部同事管理
/system/config             → 系统配置（临期提醒天数 + 通知时间）
/system/dingtalk           → 钉钉通知配置
```

---

## 环境变量清单

```bash
# 数据库
DATABASE_URL=mysql+pymysql://user:pass@host:3306/cronmail

# Redis (Celery Broker)
CELERY_BROKER_URL=redis://host:6379/0

# 加密密钥
MAIL_ENCRYPTION_KEY=<Fernet.generate_key()>

# SMTP（可在管理后台配置，也支持环境变量兜底）
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USERNAME=noreply@example.com
SMTP_PASSWORD=xxx
SMTP_SENDER_NAME=CronMail
```

---

## 部署进程清单

| 进程 | 命令 | 说明 |
|------|------|------|
| API 服务 | `uvicorn main:app --host 0.0.0.0 --port 8000` | FastAPI 主服务 |
| Celery Worker | `celery -A src.scheduler.tasks worker` | 异步任务执行（含手动邮件发送） |
| Celery Beat | `celery -A src.scheduler.tasks beat` | 定时调度器（3 个定时任务） |
| 前端 | `nginx` 托管静态文件 | Vue 3 SPA 构建产物 |
| MySQL | 由用户提供 | 业务数据存储 |
| Redis | 由用户提供 | Celery Broker |

---

## Kubernetes 部署（ADR-007）

### 镜像构建

| 镜像 | Dockerfile | 说明 |
|------|-----------|------|
| `cronmail-backend` | `Dockerfile.backend` | Python 3.12-slim，同一镜像多进程 |
| `cronmail-frontend` | `Dockerfile.frontend` | node:20 build → nginx:alpine 多阶段 |

### K8s 资源

```
k8s/
├── namespace.yaml          # cronmail 命名空间
├── configmap.yaml          # 非敏感配置
├── secret.yaml             # DB密码、加密密钥、SMTP密码
├── backend-api.yaml        # Deployment(API, replicas≥2) + Service
├── backend-worker.yaml     # Deployment(Worker, replicas=1)
├── backend-beat.yaml       # Deployment(Beat, replicas=1 单副本)
├── frontend.yaml           # Deployment(Nginx, replicas≥2) + Service
└── ingress.yaml            # /api/* → backend, /* → frontend
```

### 部署拓扑

```
Ingress
├── /api/* → backend Service:8000 → backend-api Deployment (replicas: 2)
└── /*     → frontend Service:80  → frontend Deployment (replicas: 2)

backend-worker Deployment (replicas: 1)  → 连接 Redis (Celery Broker)
backend-beat Deployment (replicas: 1)    → 连接 Redis (调度器)

外部服务（用户提供）:
├── MySQL (通过 ConfigMap 配置连接地址)
└── Redis (Celery Broker)
```

### 关键约束

- Celery Beat **必须单副本**（`replicas: 1`），否则定时任务重复执行
- MySQL/Redis 不在 K8s 内管理，通过 Secret 配置外部连接地址
- 前端 Nginx 需要配置 SPA 路由（`try_files $uri /index.html`）

