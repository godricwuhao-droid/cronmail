# ADR-011: 多类型合同与附件管理

## Status
Proposed

## Context

当前系统只有「算力租赁」一种合同类型（`contract` 表），需要扩展支持：

1. **新增合同类型**：卫星数据、算力服务
2. **附件管理**：每种合同需要上传多类附件（合同协议、交付材料、过程材料等），每类下有多子项
3. **附件状态追踪**：管理员可手动确认各类材料是否已上传完成
4. **卫星数据和算力服务**仅做归档，不走邮件发送/状态流转

## Decision

### 1. 合同类型：独立表（非基表+子表）

```
contract                      （算力租赁，表名不变，字段不变）
satellite_data_contract       （卫星数据，全新）
compute_service_contract      （算力服务，全新）
```

**拒绝基表方案的理由**：三种合同差异是领域级别的（算力租赁有设备关联+邮件+状态流转，另两种没有），共享基表强行统一反而增加耦合。

### 2. 附件架构：分类 → 子项 → 文件

```
AttachmentCategory（附件分类，运行时管理）
  └── AttachmentItem（子项清单，运行时管理）
       └── Attachment（实际文件）
```

| 概念 | 说明 | 示例 |
|------|------|------|
| **分类** (category) | 按合同类型预定义，管理员可增删改排序 | 「合同协议」「交付材料」「过程材料」 |
| **子项** (item) | 每个分类下的具体材料项，管理员可增删改排序 | 「合同扫描件」「验收单扫描件」「资源交付清单」 |
| **文件** (attachment) | 挂在子项下的实际文件，支持多文件 | `租赁协议-正本.pdf` |

子项有 `expected_type` 提示（`pdf` / `excel` / `image` / `any`），仅用于前端展示引导，不强制校验。

### 3. 附件完成判定：子项级别手动确认

```
管理员上传文件到子项
  → 子项状态显示「待确认(N个文件)」
  → 管理员审查后点击「确认完成」
  → 子项状态变为「已确认(N个文件)」
  → 分类状态由子项汇总（全部确认 = 已完成）
  → 合同附件总状态由分类汇总
```

### 4. 文件存储：NFS + K8s PV

```
POD 容器: /data/uploads/
    ↕ PVC: cronmail-attachments-pvc
        ↕ PV: cronmail-attachments-pv (NFS)
            ↕ NFS Server: /data/nfs/cronmail/

存储结构:
/data/uploads/
  └── attachments/
      ├── compute_leasing/{contract_id}/{item_id}/
      ├── satellite_data/{contract_id}/{item_id}/
      └── compute_service/{contract_id}/{item_id}/
```

### 5. 初始数据

每种合同类型预设相同的分类+子项（管理员后续可自行扩展）：

```
合同协议
  └── 合同扫描件 (PDF, 多份)

交付材料
  └── 验收单扫描件 (PDF, 多份)

过程材料
  ├── 资源交付清单 (Excel)
  └── 资源开通邮件截图 (图片)
```

### 6. 前端路由

```
合同管理
  ├── /contracts/compute-leasing       算力租赁列表
  │   ├── /contracts/compute-leasing/create
  │   ├── /contracts/compute-leasing/:id
  │   ├── /contracts/compute-leasing/:id/edit
  │   └── /contracts/compute-leasing/:id/attachments
  ├── /contracts/satellite-data        卫星数据列表
  │   ├── ...
  │   └── /contracts/satellite-data/:id/attachments
  └── /contracts/compute-service       算力服务列表
      ├── ...
      └── /contracts/compute-service/:id/attachments

系统配置
  └── /system/attachment-categories    附件分类管理（增删改排序）
```

### 7. API 路由设计

```
附件分类管理:
GET    /api/system/attachment-categories?contract_type=compute_leasing
POST   /api/system/attachment-categories
PUT    /api/system/attachment-categories/{id}
DELETE /api/system/attachment-categories/{id}
PUT    /api/system/attachment-categories/{id}/reorder

子项管理:
GET    /api/system/attachment-categories/{id}/items
POST   /api/system/attachment-categories/{id}/items
PUT    /api/system/attachment-items/{id}
DELETE /api/system/attachment-items/{id}
PUT    /api/system/attachment-items/{id}/reorder

文件操作:
GET    /api/attachments?contract_type=compute_leasing&contract_id={id}
POST   /api/attachments/upload?contract_type={type}&contract_id={id}&item_id={id}
GET    /api/attachments/{id}/download
DELETE /api/attachments/{id}

完成确认:
GET    /api/attachments/status?contract_type={type}&contract_id={id}
POST   /api/attachments/status/{item_id}/confirm
POST   /api/attachments/status/{item_id}/unconfirm
```

## Consequences

### 变容易了
- 新增合同类型只需建新表 + 前端页面，不破坏现有 `contract` 表
- 附件分类/子项运行时管理，业务调整无需改代码
- 算力租赁已有代码（rental 关联、邮件发送、定时任务）零改动

### 变难了
- 三张独立合同表意味着跨类型统计需要 UNION 查询（目前无此需求）
- 附件使用多态关联（`target_type + target_id`），不是标准 FK
- 需要 NFS 环境 + K8s PV/PVC 配置

## Reversibility
中 —— `contract` 表不动，算力租赁随时可以单独回退。卫星数据和算力服务的新表初期数据少，回退成本低。附件表独立，删除不影响合同核心业务。

## 待定项
- NFS 服务器 IP 和共享路径（由运维提供）
- 卫星数据和算力服务的元数据字段（后续迭代补充，初期仅基础字段）
