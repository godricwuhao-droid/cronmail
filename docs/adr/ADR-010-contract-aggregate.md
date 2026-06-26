# ADR-010: 引入合同（Contract）聚合根

## Status
Proposed

## Context

当前系统以 `RentalRecord` 为邮件发送粒度，存在以下问题：

1. **合并无据**：靠 `end_date` 碰运气合并设备，同客户但不同合同会错误合并
2. **重复发送**：多台设备分别点回收 → 多封邮件轰炸
3. **领域失真**：现实中设备属于合同，合同才是一封邮件的自然边界

## Decision

**引入 Contract（合同）作为聚合根，设备关联合同。**

### 领域模型

```
Customer ──1:N── Contact
Customer ──1:N── Contract ──M:N── RentalRecord  (contract_rental 中间表)
                   │
           Contract ──M:N── Contact  (contract_contact，替代原 rental_contact)
```

### Contract 核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `customer_id` | FK→Customer | 归属客户 |
| `name` / `contract_no` | VARCHAR | 合同名称 / 编号 |
| `start_date` | DATE | 合同开始日期 |
| `end_date` | DATE | 合同到期日期 |
| `billing_model` | ENUM | 计费方式（monthly/yearly） |
| `status` | ENUM | `active → expiring → expired → reclaimed` |
| `remark` | TEXT | 备注 |

### 关键规则

1. **设备关联独立**：`contract_rental` 中间表，支持随时关联/取消关联
2. **联系人挂在合同**：`contract_contact(to/cc)`，设备不再单独管联系人
3. **状态在合同维度**：定时扫描合同而非设备，状态流转统一
4. **设备去掉 `end_date`**：从合同继承；`billing_model` 也可继承（设备可覆盖）

### 邮件发送粒度

```
开通邮件   → 合同「首次签约」发送，含所有关联设备
临期提醒   → 合同到期前 3 天，一封邮件含所有关联设备
回收通知   → 合同到期当天，一封邮件含所有关联设备
```

### 模板变量结构不变

仍为 `{customer_name, rental_count, rentals: [...]}`，只是 `rentals` 来源从"按日期匹配"变为"按合同关联"。

### 旧数据迁移

1. 创建迁移脚本：同 `customer_id` + 同 `start_date` + 同 `end_date` + 同 `billing_model` 的设备自动归为一个 Contract
2. 联系人从 `rental_contact` 迁移到 `contract_contact`
3. `RentalRecord.end_date` 保留作为冗余（兼容过渡），但邮件发送以合同日期为准

### 拒绝的方案

- **设备保留 `end_date` 且合同也有的双日期方案**：增加歧义，不推荐
- **合同与设备 1:N（不可解除关联）**：不够灵活，用户明确要求可独立关联

## Consequences

### 变容易了
- 一封邮件 = 一个合同，边界清晰，不会多封轰炸
- 合同到期管理变为单点控制
- 邮件模板结构不变，迁移成本低

### 变难了
- 引入新表 `contract` + 2 个中间表，数据库复杂度增加
- 前端需要合同管理页面（CRUD + 设备关联/解除）
- 已有 API 需适配：租赁 CRUD 中去掉联系人字段，改为合同维度
- 定时任务需改为扫描合同

## Reversibility
中 —— 涉及数据库 schema 变更（2 新表 + 1 字段废弃），回滚需要数据回迁，但可在上线前通过测试环境充分验证。
