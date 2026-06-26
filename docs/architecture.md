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
│  │  • 客户管理       │                  │  • rental/         │ │
│  │  • 租赁管理       │                  │  • template/       │ │
│  │  • 模板编辑       │                  │  • mail/           │ │
│  │  • 发送日志       │                  │  • system/         │ │
│  │  • 系统配置       │                  │  • core/           │ │
│  └───────────────────┘                  └────────┬───────────┘ │
│                                                  │              │
│  ┌───────────────────┐                  ┌────────▼───────────┐ │
│  │  Celery Beat      │                  │  Celery Worker     │ │
│  │  (定时调度)        │─── 投递任务 ───►│  (异步执行)        │ │
│  │                   │                  │                    │ │
│  │  • 临期扫描 08:00 │                  │  • 发临期提醒邮件   │ │
│  │  • 到期扫描 02:00 │                  │  • 发到期回收邮件   │ │
│  └───────────────────┘                  └────────────────────┘ │
│                                                                 │
│  进程内通信: blinker Signal (rental → mail 事件)                │
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
  └── 1──N → Contact (联系人)
       ├── id, name, email, phone, department
       ├── customer_id (FK, NULL=内部同事)
       └── is_active

RentalRecord (租赁记录)
  ├── id, customer_id (FK → Customer)
  ├── machine_model, cpu_model, memory_gb, gpu_info
  ├── system_disk_gb, data_disks(JSON)
  ├── os_version, bandwidth_mbps, rack_location
  ├── private_ip, public_ips(JSON), ssh_port
  ├── root_username, root_password_enc (AES-256-GCM)
  ├── billing_model(ENUM), start_date, end_date, auto_renew
  ├── status(ENUM): PROVISIONED | EXPIRING | EXPIRED | RECLAIMED
  └── remark

rental_contact (中间表)
  ├── rental_id (FK → RentalRecord)
  ├── contact_id (FK → Contact)
  └── recipient_type(ENUM): 'to' | 'cc'

EmailTemplate (邮件模板)
  ├── id, name, trigger_type(ENUM)
  ├── subject_tpl (TEXT, Jinja2)
  ├── body_html (TEXT, Jinja2)
  ├── variables_desc(JSON), is_active, version

EmailLog (发送日志)
  ├── id, rental_id(FK), template_id(FK)
  ├── trigger_type, recipient, subject, body
  ├── status(ENUM): sent | failed
  ├── error_msg, sent_at

SmtpConfig (SMTP配置)
  ├── id, host, port, username
  ├── password_enc (AES加密)
  ├── sender_name, sender_email, use_tls
```

---

## 状态流转

```
                   管理员创建
                       │
                       ▼
                 ┌──────────┐
                 │ PROVISIONED│ ←── 使用中
                 └─────┬────┘
                       │
         到期前 ≤3 天    │  Celery Beat 自动
                       ▼
                 ┌──────────┐
                 │ EXPIRING  │ ←── 即将到期（每天发提醒）
                 └─────┬────┘
                       │
           管理员续期    │  end_date 过去
           (手动更新)    │
         ┌──────────────┼──────────────┐
         ▼              │              ▼
   ┌──────────┐         │       ┌───────────┐
   │PROVISIONED│        │       │  EXPIRED   │
   └──────────┘         │       └─────┬─────┘
                         │            │
                         │    Celery Beat 自动发回收邮件
                         │            │
                         │            ▼
                         │     ┌────────────┐
                         │     │ RECLAIMED  │ ←── 已回收
                         │     └────────────┘
                         │
                         │  任何状态均可手动触发发送
                         │  （通过详情页按钮）
```

---

## 关键流程

> **所有邮件发送（手动 + 定时）统一走 `send_merged_email()` 合并发送管道。**
> 单台设备场景下 `rentals` 为单元素数组，模板结构不受影响。

### 流程 1：开通邮件发送

```
管理员创建租赁记录（仅入库，不发邮件）
  → 点击「发送开通邮件」
  → POST /api/rentals/{id}/send-provision-email
  → 查出同一客户、同一 start_date 的所有 provisioned 记录
  → send_merged_email(records, customer, 'provision')
  → 一封邮件含该客户同日开通的所有设备
  → 写 EmailLog（每条记录一条）
  → 状态不变（保持 PROVISIONED）
```

### 流程 2：临期自动提醒

```
Celery Beat 每天 08:00（或手动触发）
  → 查询: end_date - today ≤ 3 AND end_date > today AND status IN (PROVISIONED, EXPIRING)
  → 按 customer_id 分组
  → 每组合并 → send_merged_email(group_records, customer, 'expiry_warning')
  → 状态更新为 EXPIRING
  → 写 EmailLog
```

### 流程 3：到期回收

```
Celery Beat 每天 02:00（或手动触发）
  → 手动: 查同一客户、同一 end_date 的记录
  → 定时: 查 end_date < today AND status IN (PROVISIONED, EXPIRING)，按 customer_id 分组
  → 每组合并 → send_merged_email(group_records, customer, 'reclaim')
  → 批量更新状态为 RECLAIMED
  → 写 EmailLog
```

---

## 前端路由设计

```
/                          → 仪表盘
/customers                 → 客户列表
/customers/:id/contacts    → 某客户的联系人管理
/rentals                   → 租赁记录列表
/rentals/create            → 创建租赁记录
/rentals/:id               → 租赁详情（含发送按钮）
/rentals/:id/edit          → 编辑租赁记录
/templates                 → 邮件模板列表
/templates/create          → 创建模板
/templates/:id/edit        → 编辑模板（Monaco + 预览）
/logs                      → 发送日志列表
/system/smtp               → SMTP 配置
/system/colleagues         → 内部同事管理
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
| Celery Worker | `celery -A scheduler.tasks worker` | 异步任务执行 |
| Celery Beat | `celery -A scheduler.tasks beat` | 定时调度器 |
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

