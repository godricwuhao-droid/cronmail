# ADR-026: 机房层级模型升级（排→机柜→机架）

## Status
Accepted（部分取代 ADR-021 的 rack 单层模型、ADR-023 的 rack.power_on 归属、ADR-025 的"按命名前缀推导列"方案；ADR-024 点选上架与位置字段统一、ADR-022 设备 rack_id+u_position 占用语义不变）

## Context
用户澄清机房物理层级为四级：**机房 → 排机柜（如 A排）→ 机柜（A01）→ 机架（A10-24U）→ 设备**。现状是两级：机房 → rack（A01，capacity_u），"A列"靠机架名首字母前端推导（ADR-025，无库表、无命名/备注属性），且 rack 层语义上实为"机柜"，缺少"机架"级。用户要求：
1. 机柜套机架（一个机柜含多个机架），点位图细化到机架级
2. 排列入库（可命名、备注，机柜创建必须选所属排）
3. 提供完整的"添加排 / 添加机柜 / 添加机架"能力

## Decision

### 1. 数据模型（asset_ops 库）
```
MachineRoom（现有，不变）
└─ RackRow（新表 排）: id, machine_room_id(无硬FK，现有风格), name(排内唯一), note, created_at
   └─ Cabinet（新表 机柜）: id, rack_row_id(无硬FK), name(排内唯一), power_on(从 rack 迁来), created_at
      └─ Rack（现有表 机架）: +cabinet_id(可空→迁移后 NOT NULL 语义，无硬FK)；name(机柜内唯一), capacity_u
         └─ RentalRecord（现有）: rack_id + u_position（语义不变，仍指最小单元 rack）
```
- **rack.power_on 上移 cabinet**：电源状态是机柜属性（整柜断电），`rack.power_on` 列迁移后 **DROP**（该列上线仅数天，无历史包袱）
- 无硬 FK，归属在查询层保证（与模块现有风格一致）
- **存量迁移**（脚本 `backend/scripts/migrate_rack_hierarchy.py`，幂等 + `--dry-run`）：
  - 按机架名首字母归组 → 建排 `A排`（已存在则复用）
  - 每个存量 rack（如 A01,42U,power_on）→ 建机柜 `A01`（power_on 迁移）→ rack 改挂 cabinet_id，机架名改为 `A01-42U`（对齐用户机架命名惯例「编号-容量U」）
  - 设备 rack_id 不变（指向同一 rack 行）

### 2. API 契约（`/api/machine-rooms` 域整体重构）
```
排：
GET/POST   /api/machine-rooms/{room_id}/rows
PUT/DELETE /api/machine-rooms/{room_id}/rows/{row_id}      # 删除有机柜 → 409
机柜：
GET/POST   /api/machine-rooms/{room_id}/rows/{row_id}/cabinets   # 创建 {name, power_on=true}
PUT/DELETE /api/cabinets/{cabinet_id}                        # 删除有机架 → 409
机架：
GET/POST   /api/cabinets/{cabinet_id}/racks                  # 创建 {name, capacity_u}
PUT/DELETE /api/racks/{rack_id}                              # 删除有设备 → 409（现有保护）
点位图（替代旧 /{room_id}/points，前端唯一消费方，直接替换）：
GET /api/machine-rooms/{room_id}/point-map
→ { room, rows: [{id,name,note, cabinets: [{id,name,power_on,
       racks: [{id,name,capacity_u,u_cells:[…]}]}]}], unlocated:[…], warehoused:[…] }
级联选择源（设备表单用，轻量版）：
GET /api/machine-rooms/{room_id}/locations
→ {rows: [{id,name, cabinets: [{id,name, racks: [{id,name,capacity_u}]}]}]}
```
- 旧 `/{room_id}/racks`、`/{room_id}/points` 路由**删除**（前端同步切换，smoke 脚本同步更新）
- 设备 rental 列表/详情的 `rack_name` 字段**保留字段名**，值改为层级路径 `机柜名/机架名`（如 `A01/A10-24U`）；`formatRackLocation` 前端无需改逻辑（拼接 `-U{n}` 即可）
- `warehoused`、`search`、409 占用校验等 rental 域行为不变

### 3. 前端交互（machine-rooms/detail.vue 重做 + 设备表单）
- **tab = 排（真实实体）**：`A排（2柜） | B排（1柜） | 仓库（N）`；删除后回落逻辑保留
- **内容区**：当前排的机柜**并排分组**渲染——机柜组头一行（机柜名 + 通电/未通电开关 + 容量合计 + 编辑/删除机柜 + 「+添加机架」），组内各机架横向排列（每机架 = U位号列 + 设备格列，ADR-023 样式）；行序 capacity→1（maxU 取当前排所有机架最大值）
- **横幅**：当前排口径（沿用 ADR-025）
- **三级添加**：工具栏「+ 添加排」（排名+备注）、「+ 添加机柜」（当前排，名称+电源开关）；机架在机柜组头内添加（名称+容量）
- **点选 U 位上架**：不变（rack_id+u_position 语义未动）
- **设备表单**（rentals/create.vue）：原「机房下拉 + 机架下拉 + U位」改为 机房下拉 → **排/机柜/机架三级 el-cascader**（数据源 /locations）→ U位输入；409 提示、解绑语义不变
- **术语**：UI 文案中原"机架"（旧概念）统一改称"机柜"，新 rack 概念称"机架"

## Consequences
**变容易的**：
- 层级与物理机房一致，排/机柜可命名、备注、电源状态归位到正确层级
- "添加 A 柜 / 添加 B 排"有了明确的操作路径（排 tab → 添加机柜；排内机柜头 → 添加机架）
- 设备侧几乎零改动：rack_id+u_position、409 校验、点选上架全部保留

**变难的**：
- 两张新表 + 一套三层 CRUD + 一次存量迁移（脚本必须幂等，迁移窗口内需停写）
- 点位图嵌套加深一层（排→机柜→机架），表格双层表头渲染复杂度上升
- 旧 points/racks 接口删除属 Breaking（单前端消费方 + smoke 脚本，风险可控）
- 设备表单三级级联比原两级长（cascader 交互换复杂度，可接受）

## 可逆性
中：迁移脚本幂等可重复执行，但 rack.power_on 列删除 + 机架改名（A01→A01-42U）非无损——回滚需反向脚本（排/机柜合并回 rack）。存量设备数据（rack_id/u_position）全程不变，核心资产安全。

## 决策记录
- 2026-10-19：用户澄清四级物理层级，确认机柜套机架两层结构、排列入库；ADR-021 rack 单层模型、ADR-023 rack.power_on、ADR-025 前缀推导列 被本 ADR 取代
- 2026-10-19（迁移策略）：存量机架语义为"机柜"，迁移为 排(A排)+机柜(原rack名)+机架(原rack名-容量U)；rack_name 展示值改层级路径
