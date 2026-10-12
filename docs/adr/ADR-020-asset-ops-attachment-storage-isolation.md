# ADR-020: 资产平台附件存储物理隔离

## Status
Accepted

## Context
ADR-019 拆分后，asset-ops 平台与 cronmail 平台的附件 PV 均指向同一 NFS 路径 `192.168.180.50:/cronmail`，两平台附件混在同一目录树，仅靠 `contract_type/contract_id/item_id` 逻辑区分（contract_id 为各平台独立 UUID，不冲突但无平台级隔离）。用户要求算力租赁合同附件与现有平台数据物理隔离。另因两平台的 `compute_leasing` 合同附件同名目录，隔离必须以 asset_ops 库的 file_path 白名单精确迁移，不能整目录搬移。

## Decision
1. **存储根路径环境化**：`backend/src/attachment/services.py` 的 `UPLOAD_BASE_DIR` 改为 `os.environ.get("UPLOAD_BASE_DIR", "/app/uploads")`，默认值不变，cronmail 平台行为零变化
2. **asset-ops PV 指向独立子目录**：`k8s/asset-ops/pv-attachments.yaml` NFS path 改为 `/cronmail/asset-ops`（同一 NFS server 新子目录，NFS 天然支持多客户端，未动 cronmail 清单）；configmap 显式声明 `UPLOAD_BASE_DIR=/app/uploads`
3. **存量数据精确迁移**：新增 `backend/scripts/migrate_asset_ops_uploads.py`，以 **asset_ops 库 attachment 表 file_path 白名单**为准复制（避免误拷 cronmail 库同名目录数据），幂等、`--dry-run`、路径越界防护；仅复制不删源

## Consequences
**变容易的**：
- 两平台附件物理隔离，误删/权限/容量互相影响的 blast radius 消除
- 环境化后将来如需彻底换存储（独立 NFS/对象存储）只改 ConfigMap

**变难的**：
- 上线多两步：apply PV 变更 + 滚动重启 backend（挂载点切换）
- 迁移窗口内旧 Pod 仍读写共享目录，须按"先迁移文件 → 再切 PV → 最后滚动重启"顺序执行，顺序错误会短暂读不到文件
- cronmail 平台 `/cronmail/compute_leasing/` 中 asset 平台的源文件保留不删（回滚兜底），NFS 上有冗余直至人工确认清理

## 可逆性
高：文件只复制不删除，回滚 = PV path 改回 `/cronmail` + 滚动重启即回到共享状态。

## 决策记录
- 2026-10-07：用户提出附件隔离需求；代码与清单变更、迁移脚本就绪（未部署、未执行迁移）
- 2026-10-07：附件隔离上线完成（PV 已切 /cronmail/asset-ops，存量 13 文件迁移并验证可下载，源文件保留待人工确认清理）
