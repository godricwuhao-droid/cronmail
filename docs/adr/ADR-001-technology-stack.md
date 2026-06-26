# ADR-001: 技术栈选择

## Status
Accepted

## Context
需要从零构建一个邮件自动发送平台（CronMail），核心功能：
- 裸金属服务器租赁记录管理
- 基于 Jinja2 模板的邮件发送（开通通知、临期提醒、到期回收）
- 客户及联系人管理
- SMTP 邮件发送
- 前端管理界面

需要选择后端语言/框架、前端框架、数据库。

## Decision

### 后端：Python 3.12 + FastAPI

| 对比项 | Python + FastAPI | Go + Gin |
|--------|-----------------|----------|
| 邮件模板处理 | ✅ Jinja2 生态最成熟，模板继承/宏/过滤器 | ❌ html/template 功能弱 |
| API 开发效率 | ✅ FastAPI 自动文档、类型安全 | ⚠️ 手写较多 |
| 部署复杂度 | ⚠️ 需 Python 运行时 + 依赖 | ✅ 单二进制 |
| 性能 | ⚠️ 中等，邮件场景足够 | ✅ 高 |
| AI 生态 | ✅ rich | ⚠️ 一般 |

**选择 Python + FastAPI 的理由**：邮件模板是本平台核心价值，Jinja2 的模板能力是决定性因素。邮件发送场景对并发性能要求不高，Python 完全够用。

### 前端：Vue 3 + Element Plus

| 对比项 | Vue 3 + Element Plus | React + Ant Design |
|--------|---------------------|-------------------|
| 学习曲线 | 低 | 中 |
| 组件丰富度 | Element Plus 社区最活跃，Vue 3 生态事实标准 | Ant Design 同样丰富 |
| 社区生态 | ✅ Vue 3 生态最大，问题一搜就有 | ✅ 成熟 |
| TypeScript 支持 | ✅ 原生支持 | ✅ 原生支持 |

选择 Element Plus 的理由：Vue 3 生态中社区最大、使用者最多，遇到问题搜索方便，组件覆盖管理后台全部场景（表格、表单、穿梭框、树选择、标签页等），无需引入其他 UI 库。

### 数据库：MySQL 8.0

用户已明确要求使用 MySQL。JSON 字段可用 MySQL 5.7+ 原生 JSON 类型。

### 中间件：Redis

仅用于 Celery 的 Broker，不需要持久化。用户自行提供部署。

### 定时任务：Celery Beat + Redis

每天定时扫描到期记录，触发临期提醒和到期回收邮件。

## Consequences

### 变得容易
- 邮件模板编写和调试体验好（Jinja2 SandboxedEnvironment）
- API 自动文档（Swagger UI），前后端联调方便
- 前端开发效率高（Vue 3 组合式 API + Element Plus 开箱即用）

### 变得困难
- 部署需要 Python 运行时环境（非单二进制）
- Celery Worker 进程需要额外监控和守护
- Python 异步（FastAPI）与 Celery（同步）混用需注意线程安全

### 可逆性等级：中
- 后端换成 Go 需要重写全部业务逻辑，但模块边界清晰可逐步迁移
- 前端换成 React 工作量较大但可行
- MySQL 换成 PostgreSQL 迁移成本中等（主要是 JSON 操作语法差异）
