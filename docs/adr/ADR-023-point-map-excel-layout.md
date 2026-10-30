# ADR-023: 点位图重做为 Excel 巡检表样式 + 机架电源状态

## Status
Accepted（部分修订 ADR-022 的前端布局决策；u_cells 数据结构与占用校验等 ADR-022 核心决策不变）

## Context
ADR-022 点阵图上线后，用户反馈与目标形态（机房巡检 Excel 表）不符，要求按参考图重做：
1. **布局**：参考图中每个机架占**两列**（左 U 位号列 + 右设备格列），U 位号在每组机架内部重复显示（45→1），当前实现是全局左侧一根 U 位列 + 每机架单列
2. **顶部横幅**：深色横幅显示 `机房名 + 共计 N 台设备（型号A n1 台, 型号B n2 台…）` 汇总统计，当前是普通工具栏文字
3. **机架电源状态**：机架表头显示「A01（通电）/ A02（未通电）」，当前数据模型无此字段（用户确认加字段）
4. **配色**：空格白底（U 号只留在各组左侧号列），断电红 / 在用绿需调整饱和度；当前空格是浅灰底带 U 号
5. **不做**：参考图中"千兆交换机"黄色格无数据依据，明确不建模（用户确认三色体系：红=断电 / 绿=在用 / 白=空）

## Decision
1. **Rack 模型加 `power_on` 布尔字段**（默认 True=通电）：
   - `POST /api/machine-rooms/{room_id}/racks`：body 增加可选 `power_on`（默认 true）
   - `PUT /api/machine-rooms/{room_id}/racks/{rack_id}`：body 增加可选 `power_on`（原来仅开放 capacity_u，现同时开放；机架名仍只读）
   - `GET .../points` 每个机架响应增加 `power_on: bool`
   - 部署 DDL（asset_ops）：`ALTER TABLE rack ADD COLUMN power_on BOOLEAN NOT NULL DEFAULT 1 COMMENT '通电状态（true=通电, false=未通电）';`
2. **前端点位图布局重做**（`views/machine-rooms/detail.vue`）：
   - 表格改为**每机架组两列**：组内左列=U 位号（窄列，自上而下 capacity→1），右列=设备格；表头每组为「U位」（窄）+「机架名（通电/未通电）」
   - 表顶深色横幅：`{机房名}  共计 {N} 台设备（{型号} {n} 台, …）`，统计来自各机架 u_cells 非空格按 machine_model 聚合；room.note 非空时追加「备注 {note}」
   - 配色：在用=绿底、断电=红底、空=**白底无文字**（U 号只留在各组号列）；保留 hover 加深与点击跳设备详情
   - 机架新建/编辑对话框增加 `power_on` el-switch（机架新建默认开）
3. **不变**：u_cells 数据结构、409 占用校验、未定位设备提示（unlocatedDevices）、仓库 tab、上架流程、`rack_location` 存量兼容逻辑

## Consequences
**变容易的**：
- 点位图与用户心智模型（巡检 Excel）完全一致，横向滚动时 U 位号随组走，定位格子更直观
- 机架电源状态入库后，"整柜未通电"一目了然，为将来断电告警留了数据基础

**变难的**：
- 每机架多一列窄列，横向空间占用变宽（8 机架 ≈ 16 数据列 + 8 号列），依赖横向滚动
- Rack 多一列需一次性 DDL（asset_ops）；旧镜像读新列会缺字段 → 需前后端同批滚动（power_on 有默认值，实际风险低）
- 横幅统计在前端聚合，机型种类多时文字会很长（接受：ellipsis 截断）

## 可逆性
高：power_on 为带默认值布尔列，布局为纯展示层；回滚 = 前端恢复 ADR-022 布局 + DDL 列保留无害。

## 决策记录
- 2026-10-19：用户提供巡检 Excel 参考图，确认加机架电源状态、不做黄色高亮；ADR-022 布局决策由本 ADR 修订
- 2026-10-19（实现期裁决）：backend-dev 发现 `RackUpdate` 原代码实际开放了 `name` 可改（与任务描述"仅开放 capacity_u"不符）。按本 ADR「机架名只读」裁决执行：**从 `RackUpdate` 移除 `name`**，传 name 被 Pydantic 静默忽略。前端编辑仅提交 `capacity_u + power_on`，无破坏。若将来确需改名场景（重命名机架），再出单独 ADR 并处理 `rack_location` 前缀匹配联动
