# ADR-021: 机房管理模块 + 设备变更记录自动化

## Status
Accepted（其中"机房管理-点位图"部分被 **ADR-022 机柜 U 位点阵式点位图** 取代；其余部分——机房/机架模型、仓库未上架、变更自动记录——仍有效）

## Context
1. 需要机房维度管理能力：机房点位图（机架/机位可视化）、机房设备信息、仓库未上架设备的管理。现状：设备（RentalRecord）只有 `rack_location` 自由文本，无机房概念，位置无法校验、不可视化
2. 设备字段修改后无自动变更记录。现状：`change_log` 表仅 4 字段（target_type/target_id/content/created_at），内容全靠人工在详情页录入；rental 更新接口不写日志
3. 用户要求：机房管理为独立一级菜单；设备增加"所属机房"下拉（可空）；通过"所属机房 + 机架位置"关联机房与点位图

## Decision

### 1. 机房管理模块（新 module：backend/src/machine_room/）

**数据模型**：
```
MachineRoom:        id, name(唯一), code(唯一), address, note, created_at, updated_at
Rack:               id, machine_room_id(FK), name(机房内唯一, 如 "A-01"), capacity_u(整数, 如 42), created_at
```
- 机架 = 点位图的最小结构化单元；**机位（U 位/端口级）不进数据库**——U 位分配继续用设备现有 `rack_location` 自由文本，避免过度设计（U 位数据格式各机房不统一，强行建模维护成本高）
- 点位图 UI：机房详情内按机架卡片网格渲染，每卡片显示机架名、设备数/capacity_u 进度；**不做像素级机柜绘图**（可逆性考虑：卡片布局数据需求低、迭代快，将来要精细图可在卡片内加组件）

**设备关联**：
- `RentalRecord` 加可空字段 `machine_room_id`（无 FK 硬约束，与项目现有 attachment.contract_id 风格一致；查询时 join 取机房名）
- 设备表单加"所属机房"下拉（可空，来自机房列表 API）；`rack_location` 保持文本
- **仓库未上架设备**：`machine_room_id IS NULL` 即"未上架/在库"，机房详情页列出本机房设备，仓库视图 = 未关联机房的设备列表（机房管理页内的 tab 或独立子页），**不新增 status 枚举**（现有三态 status 语义不动，上架/在库是位置属性不是设备状态）
- 列表页 /rentals 增加"所属机房"筛选（可空=全部/未上架）

**API**（/api/machine-rooms）：
- CRUD 机房；CRUD 机架（含 capacity_u）
- `GET /api/machine-rooms/{id}/points`：点位图数据（机架列表 + 每机架设备摘要）
- `GET /api/machine-rooms/warehoused`：未上架设备列表
- 删除机房前校验：有机房设备则 409 拒绝（软保护，不做级联）

**前端**：一级菜单"机房管理"（插在设备管理之后）：
- `views/machine-rooms/index.vue`：机房列表 + 新建/编辑
- `views/machine-rooms/detail.vue`：机架卡片点位图 + 每机架设备清单（点击设备跳设备详情）+ 仓库 tab（本机房未上架设备，可一键"上架"选机架）
- 设备表单（rentals/create.vue）加所属机房下拉；设备列表加机房列与筛选

### 2. 设备变更记录自动化

- `ChangeLog.content` 升级为**结构化 JSON 字符串**：`[{"field":"内存","old":"64","new":"128"}, ...]`，无操作人列（全系统无认证，维持现状）
- `update_rental` 服务层：`model_dump` 前后 diff，逐字段生成中文标签映射（field label map），只记录**实际变化**的字段；敏感字段（root_password）只记录"已修改"不记录值
- 存量兼容：前端变更记录展示页兼容两种格式（旧纯文本直接展示，新 JSON 渲染"字段：旧值 → 新值"）
- 本期范围：仅 rental 设备；合同（contract）的自动记录同模式，留后续
- 写 change_log 与主更新**同事务**（失败一起回滚，不允许设备改了日志丢了）

## Consequences
**变容易的**：
- 设备位置从自由文本升级为"机房(结构化) + 机架位置(自由)"两级，点位可视化、仓库设备可查
- 设备变更可追溯（自动、结构化、同事务）

**变难的**：
- 机房/机架数据需要人工初始维护（无导入则空库）
- change_log 双格式共存期（旧文本+新JSON），展示层需长期兼容
- 机架 capacity_u 与实际 U 位占用无强校验（rack_location 是文本），点位图进度条是近似值——接受此精度换取低维护成本
- 删除机房的 409 保护意味着必须先迁走/解绑设备，操作步骤变多

## 可逆性
高：新增表+可空列，回滚 = 删菜单/路由/表（设备 machine_room_id 列可保留为空）。

## 决策记录
- 2026-10-07：用户确认需求（机房一级菜单、设备所属机房可空下拉、仓库未上架设备、变更自动记录）；U 位不入库存、卡片式点位图为 Architect 设计决策
