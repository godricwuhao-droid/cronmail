# ADR-012: 算力服务合同 - 服务内容模型

## Status
Proposed

## Context

当前 `compute_service_contract` 表（ADR-011 创建）仅有基础归档字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `customer_id` | FK→Customer | 客户ID |
| `name` | VARCHAR(255) | 合同名称 |
| `contract_no` | VARCHAR(100) | 合同编号 |
| `remark` | TEXT | 备注 |
| `created_at` / `updated_at` | DateTime | 时间戳 |

无法满足以下需求：

1. **服务内容结构化存储**：算力服务合同的服务内容是三层结构（服务大类 → 服务项 → 明细行），需要逐行记录到合同下方，支持数量、单价、总价的统计
2. **缺少合同方信息**：甲方、乙方名称未独立存储
3. **缺少金额和日期**：无合同金额、开始/结束日期字段，无法做金额统计和到期管理
4. **缺少销售/采购区分**：同一客户既有我们卖算力给客户的合同（销售），也有我们从供应商采购算力的合同（采购），目前无法区分
5. **缺少背靠背合同关联**：同一笔算力服务，采购合同和销售合同是成对存在的，需要关联

## Decision

### 1. `compute_service_contract` 表新增以下字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `contract_type` | VARCHAR(10) NOT NULL DEFAULT 'sales' | 合同类型: `sales`（销售） / `procurement`（采购） |
| `party_a_name` | VARCHAR(255) | 甲方名称。销售合同时为客户方，采购合同时为我方；可从 customer 继承也支持独立填写 |
| `party_b_name` | VARCHAR(255) | 乙方名称。销售合同时为我方，采购合同时为供应商 |
| `amount` | Numeric(12,2) | 合同总金额，**由服务行自动汇总**，也支持手动覆盖 |
| `start_date` | Date | 合同开始日期 |
| `end_date` | Date | 合同到期日期 |
| `related_contract_id` | UUID NULLABLE FK→compute_service_contract.id | 背靠背关联：采购合同关联其对应的销售合同（或反之），非背靠背合同留空 |

**`contract_type` 与甲乙方语义：**

| contract_type | 甲方 (party_a) | 乙方 (party_b) |
|:---:|---|---|
| `sales` | 客户（买我们算力的一方） | 我们（提供算力的一方） |
| `procurement` | 我们（采购算力的一方） | 供应商（提供算力的一方） |

**背靠背关联示例：**

```
采购合同 A（向英伟达采购 100 GPU）
    └── related_contract_id ──→ 销售合同 B（卖给某客户 100 GPU）
```

**关联方向与双向展示：** 不限制用户从哪个方向建立关联（可以从销售指向采购，也可以从采购指向销售）。后端展示时做**双向查询**——无论关联从哪端建立，两个合同详情页都能看到对方：

```python
# 展示任意合同时，双向查找关联合同
related = session.query(ComputeServiceContract).filter(
    (ComputeServiceContract.related_contract_id == current.id)  # 谁关联了我
    | (ComputeServiceContract.id == current.related_contract_id) # 我关联了谁
).first()
```

这样用户不需要关心「应该从哪端操作」，两端自动同步展示。数据层只有一份 FK，无冗余、无一致性问题。

**为什么不用多对多中间表？** 当前背靠背场景是 1:1 关系（一笔采购对应一笔销售），一个简单 FK 足够。如果未来出现「一笔采购拆给多个客户」的 1:N 场景，再升级为中间表——迁移代价可控。

### 2. 新增 `contract_service_line` 子表

服务内容拆为独立子表，支持逐行存储和统计：

```sql
CREATE TABLE contract_service_line (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES compute_service_contract(id) ON DELETE CASCADE,
    category        VARCHAR(50)  NOT NULL,   -- 服务大类: 算力服务 / 算力优化服务 / 智能体服务
    item_name       VARCHAR(100) NOT NULL,   -- 服务项: 通用CPU容器实例 / 高性能GPU容器实例 / 存储 ...
    specification   JSON,                    -- 参数规格 {"vcpu":10,"frequency":"2.5GHz","memory":"32GB DDR4",...}  仅用于前端展示，不参与聚合
    vcpu_count      Numeric(10,2),           -- vCPU 核数（NULLABLE，有则填，用于跨合同资源聚合）
    memory_gb       Numeric(10,2),           -- 内存 GB 数（NULLABLE，统一单位，用于跨合同资源聚合）
    storage_gb      Numeric(10,2),           -- 存储 GB 数（NULLABLE，统一单位，用于跨合同资源聚合）
    unit            VARCHAR(20)  NOT NULL,   -- 单位: 个/月, 套/月, TB/月, license
    quantity        Numeric(12,2) NOT NULL,  -- 数量
    period_months   INTEGER NOT NULL DEFAULT 1, -- 周期(月)
    unit_price      Numeric(12,2) NOT NULL,  -- 单价
    total_price     Numeric(12,2) NOT NULL,  -- 总价 = quantity × period_months × unit_price
    sort_order      INTEGER DEFAULT 0,       -- 排序号
    created_at      TIMESTAMP DEFAULT NOW()
);
```

**`specification` JSON vs 数值列的分工：**

| 用途 | 用哪个字段 | 为什么 |
|------|-----------|--------|
| 前端展示详细规格（如 "DDR4"、"NVMe SSD"） | `specification` JSON | 异构数据，适合自由展示 |
| 跨合同聚合「某客户总共有多少 vCPU」 | `vcpu_count` Numeric | 标准 SQL SUM，无需解析 JSON |
| 跨合同聚合「某客户总内存/存储」 | `memory_gb` / `storage_gb` Numeric | 统一单位（GB），标准聚合 |

3 个数值列均为 **NULLABLE**，没有对应资源的服务行（如纯存储行不需要填 vcpu_count）留空即可。前端这 3 个输入框与 specification 的展示内容相互独立，不互相覆盖。

**示例数据：**

```
行1: 通用CPU容器实例 | vcpu=10 | mem=32  | storage=500  | spec={"vcpu":10,"frequency":"2.5GHz","memory":"32GB DDR4","storage":"500GB NVMe SSD"}
行2: 高性能GPU实例   | vcpu=   | mem=128 | storage=2000 | spec={"tops":200,"fp16":312,"vram":"80GB HBM3","supported_models":["LLaMA","Qwen"]}
行3: 块存储扩容      | vcpu=   | mem=   | storage=1000 | spec={"type":"块存储","iops":10000}
```

**为什么不用 JSON 路径查询做聚合？** 因为 `specification` 是异构 JSON —— 不同服务行的字段名不统一、值可能是带单位的字符串（如 `"32GB DDR4"`），SQL `SUM` 无法处理。独立数值列是可靠的聚合方案。

### 3. 为什么是扁平表而非树形表？

图片中的层级结构（大类 → 中类 → 明细行）：

- 「大类」和「中类」本质是分组标签，`category` + `item_name` 两个字段即可覆盖
- 独立 category 表或 item 模板表会引入额外 JOIN，对当前数据量无实质收益
- 扁平表的统计 SQL 直观：

```sql
-- 按大类统计金额
SELECT category, SUM(total_price)
FROM contract_service_line
WHERE contract_id = ?
GROUP BY category;

-- 所有合同中 GPU 实例总数量
SELECT SUM(quantity)
FROM contract_service_line
WHERE item_name = '高性能GPU容器实例';

-- 按客户统计算力服务总金额
SELECT c.customer_id, SUM(l.total_price)
FROM compute_service_contract c
JOIN contract_service_line l ON c.id = l.contract_id
GROUP BY c.customer_id;

-- 某客户在所有销售合同中的总 vCPU / 内存 / 存储（线上聚合示例）
SELECT
    cus.name AS customer,
    SUM(l.vcpu_count)  AS total_vcpu,
    SUM(l.memory_gb)   AS total_memory_gb,
    SUM(l.storage_gb)  AS total_storage_gb
FROM compute_service_contract c
JOIN contract_service_line l ON c.id = l.contract_id
JOIN customer cus ON c.customer_id = cus.id
WHERE c.contract_type = 'sales'       -- 仅统计销售合同
  AND cus.id = ?
GROUP BY cus.id, cus.name;

-- 某客户各类服务金额（按 category + item_name 分组）
SELECT cus.name AS customer, l.category, l.item_name, SUM(l.total_price) AS subtotal
FROM compute_service_contract c
JOIN contract_service_line l ON c.id = l.contract_id
JOIN customer cus ON c.customer_id = cus.id
WHERE c.contract_type = 'sales'
  AND cus.id = ?
GROUP BY cus.name, l.category, l.item_name
ORDER BY l.category, subtotal DESC;

-- 查询背靠背合同对（采购 → 销售的金额对比）
SELECT
    proc.contract_no AS procurement_no,
    proc.amount       AS procurement_amount,
    sale.contract_no  AS sales_no,
    sale.amount       AS sales_amount
FROM compute_service_contract proc
JOIN compute_service_contract sale ON proc.related_contract_id = sale.id
WHERE proc.contract_type = 'procurement';
```

### 4. 为什么不支持「模型属性动态调整」？

用户提到未来可能需要在界面上自行增删服务行的属性维度（如新增「GPU TOPS」输入框）。

**暂不做，原因：**

动态属性本质是 EAV 模型（Entity-Attribute-Value），需要的改动：

- 新增 `service_line_attr_definition` 表（属性元数据：名称、类型、默认值）
- 新增 `service_line_attr_value` 表（每行 × 每个属性的值，行数 = 服务行数 × 属性数）
- 前端从固定表单变为动态表单引擎（根据元数据自动渲染控件）
- 聚合 SQL 从 `SUM(col)` 变为多表 JOIN + CASE WHEN PIVOT

**当前评估：** 固定 3 个数值列（vcpu / memory / storage）+ `specification` JSON（存 GPU 参数等异构内容）已覆盖核心场景。真的需要加新维度时，`ALTER TABLE ADD COLUMN` 一分钟完成，远低于 EAV 的维护成本。等到「一个月要加 3 次列」时再考虑动态属性，届时迁移代价可控（数值列 → EAV 是单向写脚本即可完成的迁移）。

### 5. `specification` 为什么用 JSON 而非文本？

不同服务项的规格参数差异极大：

| 服务项 | 规格字段 |
|--------|---------|
| 通用CPU容器实例 | vCPU、主频、内存、存储 |
| 高性能GPU容器实例 | TOPS 算力、FP16、显存、支持模型列表 |
| 存储 / 优化服务 | 仅文本描述 |

JSON 的收益：
- 无需为每种服务项建独立表的 schema 膨胀
- PostgreSQL `->>` 路径查询支持按规格维度筛选（如「查 vcpu > 8 的所有行」）
- 前端渲染时直接遍历 key-value 展示

### 6. 金额汇总逻辑

合同主表 `amount` 的语义：

- **保存时自动汇总**：`amount = SUM(contract_service_line.total_price)`，用户无需手动算
- **允许手动覆盖**：业务中存在「合同金额 ≠ 服务行加总」的场景（如总价折扣、零头抹除），手动填写后以手动值为准
- **不一致时提示**：前端 `amount` 与自动汇总差异超过阈值（0.01）时给出提示，但不阻止保存

### 7. ER 关系（不变更现有表）

```
Customer
  ├── 1:N → Contract (算力租赁，现有，不动)
  ├── 1:N → SatelliteDataContract (卫星数据，现有，不动)
  └── 1:N → ComputeServiceContract (算力服务)
                │  contract_type: sales | procurement
                │  related_contract_id ──────→ ComputeServiceContract (背靠背自引用)
                │
                └── 1:N → ContractServiceLine  ← 新增
                              vcpu_count, memory_gb, storage_gb (NULLABLE 数值列)
                              specification (JSON, 展示用)
```

### 拒绝的方案

- **JSON 字段存整个服务内容树**：简单但无法 SQL 统计，无法按类目/金额维度查询，放弃
- **服务内容存为 HTML/富文本**：展示方便但无结构化，放弃
- **category 独立为模板表**：过度设计，当前无复用场景，放弃
- **动态属性模型（EAV）**：服务行属性维度可由管理员自由增删。对于当前 3 个核心维度（vcpu/memory/storage）来说过度设计，增加三张表的复杂度，SQL 聚合困难。等属性维度频繁变更时再考虑
- **背靠背用多对多中间表**：当前场景是 1:1，简单 FK 足够。真需要 1:N 时升级为中间表，迁移代价可控

## Consequences

### 变容易了
- 逐行统计金额、数量，支持 Dashboard 按服务大类/客户维度聚合
- 跨合同统计某客户的 vCPU、内存、存储总量（通过 vcpu_count / memory_gb / storage_gb）
- 服务内容结构化，未来可导出 Excel / 生成报价单
- 区分销售/采购合同，支持分别统计收入/成本
- 背靠背合同关联，可对比采购成本与销售收入
- `compute_service_contract` 新增字段为 NULLABLE，存量数据不受影响

### 变难了
- 新增 1 张子表，前端需要服务行编辑器（按大类分组、增删改行、自动计算总价、CPU/内存/存储独立输入框）
- 合同创建/编辑表单复杂度提升
- 需要在保存逻辑中加入金额汇总校验
- 销售/采购切换时，甲乙方语义需前端联动提示

## Reversibility
低 —— 新增字段均为 NULLABLE，新增表为独立子表，对现有 `compute_service_contract` 无破坏性变更。回退只需删除新增字段和新表，现有数据和 API 不受影响。

**各决策可逆性：**

| 决策 | 可逆性 | 回退方式 |
|------|:---:|------|
| vcpu_count / memory_gb / storage_gb 数值列 | 高 | DROP COLUMN，无数据依赖 |
| contract_type 字段 | 中 | 回退需迁移数据，但字段本身可删 |
| related_contract_id 自引用 | 高 | DROP COLUMN，不关联即可留空 |
| specification JSON | 高 | DROP COLUMN，或改为 TEXT |
| 不做动态属性 | 低（但可追加） | 未来需要时，从固定列迁移到 EAV 是单向写脚本 |
