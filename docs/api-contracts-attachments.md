# CronMail API 接口契约（新增部分：多类型合同 + 附件）

> 已有合同（算力租赁）API 不变，路径不变：`/api/contracts/*`
> 以下为新增接口

---

## 7. 卫星数据合同 (SatelliteDataContract)

### GET /api/satellite-data-contracts

列表，支持 `?search=&customer_id=&page=&page_size=`

**响应**:
```json
{
  "items": [
    {"id": "uuid", "customer_id": "uuid", "customer_name": "某公司", "name": "卫星数据合同-001", "contract_no": "WX-2026-001", "remark": null, "created_at": "...", "updated_at": "..."}
  ],
  "total": 1, "page": 1, "page_size": 20
}
```

### POST /api/satellite-data-contracts

**请求**:
```json
{"customer_id": "uuid", "name": "卫星数据合同-001", "contract_no": "WX-2026-001", "remark": ""}
```

### GET /api/satellite-data-contracts/{id}

### PUT /api/satellite-data-contracts/{id}

### DELETE /api/satellite-data-contracts/{id}

---

## 8. 算力服务合同 (ComputeServiceContract)

### GET /api/compute-service-contracts

列表，支持 `?search=&customer_id=&page=&page_size=`

**响应**:
```json
{
  "items": [
    {"id": "uuid", "customer_id": "uuid", "customer_name": "某公司", "name": "算力服务合同-001", "contract_no": "FW-2026-001", "remark": null, "created_at": "...", "updated_at": "..."}
  ],
  "total": 1, "page": 1, "page_size": 20
}
```

### POST /api/compute-service-contracts

### GET /api/compute-service-contracts/{id}

### PUT /api/compute-service-contracts/{id}

### DELETE /api/compute-service-contracts/{id}

---

## 9. 附件分类管理 (AttachmentCategory)

### GET /api/system/attachment-categories?contract_type=compute_leasing|satellite_data|compute_service

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "contract_type": "compute_leasing",
      "name": "合同协议",
      "code": "contract_agreement",
      "sort_order": 1,
      "is_active": true,
      "items": [
        {"id": "uuid", "name": "合同扫描件", "description": "合同扫描件PDF", "expected_type": "pdf", "sort_order": 1, "is_active": true}
      ]
    }
  ]
}
```

### POST /api/system/attachment-categories

**请求**:
```json
{"contract_type": "satellite_data", "name": "合同协议", "code": "contract_agreement", "sort_order": 1}
```

### PUT /api/system/attachment-categories/{id}

### DELETE /api/system/attachment-categories/{id}

软删除（设 is_active=false）。

### PUT /api/system/attachment-categories/{id}/reorder

**请求**:
```json
{"sort_order": 2}
```

### POST /api/system/attachment-categories/{category_id}/items

**请求**:
```json
{"name": "数据交付报告", "description": "...", "expected_type": "pdf", "sort_order": 1}
```

### PUT /api/system/attachment-items/{item_id}

### DELETE /api/system/attachment-items/{item_id}

软删除（设 is_active=false）。

### PUT /api/system/attachment-items/{item_id}/reorder

---

## 10. 附件文件 (Attachment)

### GET /api/attachments?contract_type=compute_leasing&contract_id={id}

**响应**:
```json
{
  "categories": [
    {
      "category_id": "uuid",
      "category_name": "合同协议",
      "items": [
        {
          "item_id": "uuid",
          "item_name": "合同扫描件",
          "expected_type": "pdf",
          "files": [
            {"id": "uuid", "filename": "租赁协议-正本.pdf", "file_size": 2048000, "mime_type": "application/pdf", "uploaded_at": "..."}
          ],
          "file_count": 1,
          "confirmed": true,
          "confirmed_at": "..."
        }
      ]
    }
  ]
}
```

### POST /api/attachments/upload?contract_type={type}&contract_id={id}&item_id={id}

multipart/form-data，字段 `file`（可多文件上传）。

**响应**:
```json
{"attachments": [{"id": "uuid", "filename": "xxx.pdf", "file_size": 2048000}]}
```

### GET /api/attachments/{id}/download

返回文件流，Content-Disposition: attachment。

### DELETE /api/attachments/{id}

---

## 11. 附件完成确认

### POST /api/attachments/status/{item_id}/confirm

**请求**:
```json
{"contract_type": "compute_leasing", "contract_id": "uuid"}
```

**响应**:
```json
{"confirmed": true}
```

### POST /api/attachments/status/{item_id}/unconfirm

同上。

### GET /api/attachments/status/summary?contract_type={type}&contract_id={id}

返回该合同所有分类的完成汇总（用于列表页和详情页展示附件状态图标）。

**响应**:
```json
{
  "total_items": 5,
  "confirmed_items": 3,
  "all_confirmed": false,
  "items": {
    "contract_agreement": {"confirmed": true, "file_count": 3},
    "acceptance_material": {"confirmed": false, "file_count": 0},
    "process_material": {"confirmed": true, "file_count": 2}
  }
}
```

---

## 12. 前端路由变更

```
合同管理
  /contracts/compute-leasing          → 算力租赁列表（原 /contracts）
  /contracts/compute-leasing/create   → 新建
  /contracts/compute-leasing/:id      → 详情
  /contracts/compute-leasing/:id/edit → 编辑
  /contracts/compute-leasing/:id/attachments → 附件管理

  /contracts/satellite-data           → 卫星数据列表
  /contracts/satellite-data/create
  /contracts/satellite-data/:id
  /contracts/satellite-data/:id/edit
  /contracts/satellite-data/:id/attachments

  /contracts/compute-service          → 算力服务列表
  /contracts/compute-service/create
  /contracts/compute-service/:id
  /contracts/compute-service/:id/edit
  /contracts/compute-service/:id/attachments

系统配置
  /system/attachment-categories       → 附件分类管理
```
