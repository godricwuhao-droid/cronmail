# 缺陷跟踪记录

| 编号 | 日期 | 描述 | 严重程度 | 状态 | 指派 | 备注 |
|------|------|------|---------|------|------|------|
| #001 | 2026-06-24 | PUT /api/rentals/{id} 全量更新时传入 contacts 数组导致 500 Internal Server Error | 高 | 新建 | backend-dev | 见下方详情 |

---

## Bug #001: PUT /api/rentals/{id} 全量更新报 500

### 问题描述
当调用 PUT /api/rentals/{id} 传入完整请求体（含 contacts 和 data_disks 数组）时，后端返回 500 Internal Server Error。

### 复现步骤
1. 创建一条租赁记录（POST /api/rentals）
2. 调用 PUT /api/rentals/{id}，传入包含 contacts 和 data_disks 的完整请求体
3. 收到 500 错误

### 请求示例
```json
{
  "customer_id": "c0441ac5-...",
  "contacts": [{"contact_id": "fe2bd0b7-...", "recipient_type": "to"}],
  "data_disks": [{"size_gb": 2000, "type": "NVMe SSD"}],
  ...
}
```

### 实际行为
返回 500 Internal Server Error

### 根因分析
后端日志错误：
```
AttributeError: 'dict' object has no attribute 'model_dump'
```
位于 `src/rental/services.py` 第 115 行：
```python
update_data["data_disks"] = [disk.model_dump() for disk in disks]
```

`update_rental()` 方法中调用 `data.model_dump(exclude_unset=True)` 后，`data_disks` 字段的值已经被序列化为 `list[dict]` 而非 `list[DataDiskSchema]`，因此后续调用 `.model_dump()` 时失败。

### 修复建议
修改 `services.py` 第 112-117 行，判断 data_disks 元素类型：
```python
if "data_disks" in update_data:
    disks = update_data["data_disks"]
    if disks:
        if hasattr(disks[0], 'model_dump'):
            update_data["data_disks"] = [disk.model_dump() for disk in disks]
        # 已经是 dict 类型，不需要转换
    else:
        update_data["data_disks"] = None
```

### 变通方案
当前可以仅传需要更新的字段（部分更新），例如只传 `{"remark": "新备注"}` 可正常工作。

### 影响范围
- 端点: PUT /api/rentals/{id}
- 条件: 请求体中包含 data_disks 或 contacts 字段时触发
- 严重程度: 高（影响全量更新功能）

---

## Bug #002: 邮件发送端点返回空结果（设计缺陷/文档不一致）

### 问题描述
POST /api/rentals/{id}/send-provision-email、send-expiry-reminder、reclaim 等端点始终返回 `{"email_log_ids": [], "recipient_count": 0}`。

### 原因分析
邮件发送采用事件驱动架构（blinker），API 端点发布事件后立即返回，不等待邮件实际发送完成。订阅者异步处理邮件发送。因此 API 响应中无法反映实际发送结果。

### 影响
- 低：功能正常，邮件最终会通过事件订阅者发送
- API 文档未说明异步行为，客户端无法通过返回结果判断发送是否成功
