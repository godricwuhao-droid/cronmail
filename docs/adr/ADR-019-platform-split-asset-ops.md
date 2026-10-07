# ADR-019: 平台拆分——资产运营管理平台（分支隔离 + namespace 隔离）

## Status
Accepted

## Context
需要将现有单平台拆分为两个独立平台：**资产运营管理平台**（设备管理核心：邮件、定时任务、合同管理-算力租赁合同、客户管理、仪表盘、系统配置、发送日志）与**项目管理平台**（项目三公司台账、项目附件、LLM 解析、回款）。经只读代码评估（详见本次会话调研）：
- 后端模块化单体，`main.py` 单入口注册 13 组路由；project 模块与邮件/合同侧业务零互调，仅共享 attachment（contract_type 多态共表）与 contract_parser（LLM）
- 前端无全局状态、无共享组件库，views/projects/ 与 A 侧页面零互引，历史上以"整文件复制"方式扩展
- 全系统无 JWT 认证层、无 Alembic（create_all 建表），拆分阻力小

## Decision
采用**分支隔离 + namespace 隔离**方案，不复制目录、不拆仓库：

### 1. 代码
- 以当前分支为基准拉出 **`platform-asset-ops`** 分支，在其上裁剪出资产运营管理平台
- **当前分支（主线）暂保持完整版不动**，项目管理平台的裁剪后续单独出任务
- 两分支约定：**禁止互相 merge**，需同步的内容（attachment/LLM 模块等）用 diff 手工移植并在 changelog 标注"双平台同步"

### 2. 资产运营管理平台（platform-asset-ops 分支）
| 项 | 值 |
|---|---|
| 保留模块 | customer / contact / rental / contract（算力租赁合同）/ template / mail / scheduler(Celery) / attachment(仅 contract 类型) / system(SMTP/钉钉/内部同事/临期提醒/通知时间/附件分类) |
| 裁掉模块 | project / compute_service / satellite / contract_parser(LLM) / system 的 LLM 端点与配置段 / 前端 projects 全部视图、卫星数据与算力服务合同页、项目报表、LLM 配置段 |
| 数据库 | **新建独立库 `asset_ops`**：create_all 建表后从 `cronmail` 复制资产平台相关表的数据（不含 project_* 表）；`cronmail` 库全程不改动 |
| namespace | `asset-ops` |
| 镜像 | `harbor.xhwltech.com/xhcloud/asset-ops-backend:latest` / `asset-ops-frontend:latest` |
| NodePort | 前端 30083 / 后端 30084 |
| 共享设施 | 文件存储 PVC（同 PV 新 PVC）、document-converter（环境变量指向现有 ClusterIP，跨 namespace） |
| Celery | 保留（临期/到期/回收定时邮件全部属资产平台） |

### 3. 部署
- 现有 `cronmail` namespace（30081/30082）**全程不动**
- 回滚 = `kubectl delete ns asset-ops`，对现有平台零影响

## Consequences
**变容易的**：
- 两平台独立部署、独立端口、独立 namespace、**独立数据库**，故障域与数据域完全隔离
- 零文件迁移（共享 PVC，附件按存储路径寻址）
- 保留 git 历史，两分支 diff 即平台差异，便于模块同步对照
- 可逆性高：删除 asset-ops namespace 即完整回滚；`cronmail` 库未动，随时可弃用 `asset_ops` 库；将来真要独立仓库可 `git clone --branch` 抽离

**变难的**：
- 两分支长期分叉，attachment 模块与（主线保留的）LLM 模块同步升级需手工移植两处，靠 changelog 约定约束
- 一次性数据迁移：新建 `asset_ops` 库后需从 `cronmail` 复制资产侧表数据（不含 project_* 表），迁移期间两库数据不一致——迁移脚本须幂等可重跑，并附行数/关键字段核对
- 后续两库 schema 各自演进，attachment 等"同名表"在两边结构可能漂移，修改需双分支同步（changelog 标注）
- 跨 namespace 依赖（converter ClusterIP、同 PV 的 PVC）在 k8s 清单中需显式声明，运维心智成本略增

## 决策记录
- 2026-10-07：用户确认拆分方向、分支/namespace 命名（资产运营管理平台）
- 2026-10-07：数据库改为**独立库**——新建 `asset_ops` 库并复制 `cronmail` 资产侧数据，原库不做任何改动
