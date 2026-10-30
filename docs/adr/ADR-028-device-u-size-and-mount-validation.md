# ADR-028: 设备 U 数（多 U 占用）+ 上架空间校验 + 设备表单字段收敛

## Status
Accepted（升级 ADR-022 的"单设备占 1U"假设；ADR-026 层级模型与 ADR-027 视觉不变）

## Context
用户验收 ADR-027 后提出 4 点：
1. 设备要有 **U 数**（u_size）——设备占用多少 U（1U/2U/4U…），不再是隐式 1U（ADR-022 已知限制）
2. 点位图要有**空间判断**（用户给的两个校验场景）：
   - 45U 机架，4U 设备放 U45 → 报错（越界：45+4-1=48 > 45）
   - 28U 已有设备，26U 再放 4U 设备 → 报错（区间 [26,29] 与 [28,28] 重叠）
   - ⇒ 语义确认：**u_position = 设备底部 U，占用区间 [u_position, u_position + u_size - 1]，向上延伸**
3. 设备表单「所属机房」必须**下拉选择**机房数据，不能自由填写
4. 设备表单/列表字段调整：
   - 「机柜/机架位置」→ 改为**一个「机架」字段**：值 = 机架名（格式 `A01-12U`，即 ADR-026 命名"机柜号-容量U"），录入方式 = **下拉选择（支持搜索筛选）**，选项来源于机房管理点位图（locations），按机柜分组（"下拉的机柜数据来源于机房管理的点位图，机柜+U位拼接出可选机柜"= 机架名本身即拼接结果）
   - 表单的「U位」输入 → 改为「U数」（u_size）；**具体 U 位由点位图点选上架决定，表单不再录入 u_position**（选机架不选 U = 已定架未定位，复用现有 unlocated 机制）
   - 设备列表表头同步：「机柜/机架位置」→「机架」；「U位」列 →「U数」列

## Decision

### 1. 数据模型（asset_ops 库，1 条 DDL）
- `ALTER TABLE rental_record ADD COLUMN u_size INT NOT NULL DEFAULT 1 COMMENT '设备占用U数（自 u_position 底部起向上占用 u_size 个连续 U 位，默认 1）';`
- 存量数据默认 1，行为与现状等价，**无需迁移**
- 占用区间：`[u_position, u_position + u_size - 1]`（u_position 为设备底部；u_position 为 NULL 表示未定位，无区间）

### 2. 后端 API 变更
1. rental create/update：请求体新增 `u_size: int ≥ 1`（默认 1）；响应透出 `u_size`
2. **定位校验升级**（update 提交 rack_id + u_position 时，409 之前先校验）：
   - 越界：`u_position + u_size - 1 > rack.capacity_u` → **400**，detail：`4U 设备无法放置于 A01-45U 的 U45，超出机架容量（占用 U45~U48）`
   - 重叠：与同机架其他设备区间相交 → **409**（沿用），detail 说明冲突设备与区间：`与 A01-45U 的 {型号}（U28）位置冲突，所选 U26~U29 重叠`
   - 解绑/未定位（u_position=NULL）不做区间校验
3. `point-map` 的 `u_cells`：多 U 设备的**区间内每个 U 格**都标记该设备 brief（结构不变）；前端据此合并渲染跨 U 色块
4. `locations` 结构不变；新增前端下拉需要：按机柜分组的前端可自行从 locations 扁平化（cabinet.name → rack.name），不加接口
5. rental 列表/详情 `rack_name` 值改为**纯机架名**（`A01-45U`，去掉原"机柜/"路径前缀——用户明确机架字段格式为 A01-12U 风格）；新增 `u_size` 透出

### 3. 前端变更
1. **设备表单（rentals/create.vue）**：
   - 「所属机房」：el-select（机房列表，filterable）——若现状已下拉则确认搜索可用
   - 「机架」：单一字段 = el-select（filterable 搜索），**按机柜 el-option-group 分组**，option label = 机架名（A01-45U）；选机房后加载 locations 生成选项；选中即 rack_id
   - 「U数」：数字输入（u_size，默认 1，≥1，整数）
   - 表单不再录入 u_position：提交 machine_room_id + rack_id(可空) + u_size；选机架但不上架 = unlocated
   - 编辑回显：rack_id 反查机架选项、u_size 回显
2. **设备列表（rentals/index.vue）**：
   - 列「机柜/机架位置」→「机架」（显示 rack_name，即 A01-45U）
   - 列「U位」→「U数」（显示 `{u_size}U`）
   - 列设置 key 迁移兼容（旧 key 自动失效，新 key 默认列）
3. **点位图（machine-rooms/detail.vue）**：
   - **多 U 合并渲染**：同机架内同一 rental_id 的连续格合并为一个跨 u_size 行的色块（顶部对齐区间上端），块内型号+IP；点击块内任一格跳详情
   - **点选上架升级**：点击空格 U{n} = 设备底部位；放入设备对话框增加**预校验与占用预览**：
     - 选中设备后显示 `将占用 U{n}~U{n+size-1}`
     - 越界（n+size-1 > 容量）→ 红字提示「上方空间不足」，禁用确认
     - 冲突（区间被占）→ 红字提示，禁用确认（后端 409 仍保留为兜底）
   - 未定位提示（unlocated）语义不变
4. **设备详情**：U位（u_position）+ U数（u_size）均展示；`formatRackLocation` 相关展示随 rack_name 新格式自然适配（`A01-45U-U30`）
5. 视觉沿用 ADR-027，色块支持跨行（合并块高度 = u_size × 行高）

## Consequences
**变容易的**：
- 设备真实体积表达 + 空间判断，点位图从"格子填色"升级为"设备块摆放"（对齐 NetBox 多 U 设备渲染标准形态）
- 表单字段收敛：机架=下拉（数据即点位图），U 位完全交给点位图，表单心智 = "设备放哪排柜子里"
**变难的**：
- 区间校验与合并渲染复杂度上升（越界/重叠/多 U 块跨行/部分占用）
- 存量 1U 假设被打破：未来若有"设备改 U 数"的操作需要重新校验（本轮不改 u_size 时触发校验——编辑 u_size 需重新做区间校验，u_position 非空时）
- 列表「机架」列只显示机架名，机柜/排归属需去详情页看（用户明确格式如此）

## 可逆性
高：u_size 默认 1 兼容存量；校验为增量；回滚 = 忽略 u_size（恒 1）即恢复现状。

## 决策记录
- 2026-10-27：用户确认 U 数、空间判断两场景（底部起向上）、机房下拉化、机架单字段（A01-12U 格式下拉）+ U 位字段改 U 数；u_position 录入从表单迁移到点位图点选
