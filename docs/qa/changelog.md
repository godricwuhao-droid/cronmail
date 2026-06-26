# 测试变更日志

## 2026-06-24

### 全功能测试报告

| 测试类别 | 端点 | 状态 | 备注 |
|---------|------|------|------|
| 健康检查 | GET /api/health | ✅ 通过 | 返回 `{"status":"ok"}`，HTTP 200 |
| **客户管理** | | | |
| 客户列表 | GET /api/customers | ✅ 通过 | 返回分页格式正确 |
| 创建客户 | POST /api/customers | ✅ 通过 | 返回 201，含 id 字段 |
| 客户详情 | GET /api/customers/{id} | ✅ 通过 | 返回 200，含完整信息 |
| 更新客户 | PUT /api/customers/{id} | ✅ 通过 | 返回 200，名称已更新 |
| **联系人管理** | | | |
| 创建客户联系人 | POST /api/contacts | ✅ 通过 | 返回 201，含 id |
| 创建内部同事 | POST /api/contacts (无customer_id) | ✅ 通过 | 返回 201，customer_id=null |
| 查询客户联系人 | GET /api/contacts?type=customer | ✅ 通过 | 正确返回该客户下的联系人 |
| 查询内部同事 | GET /api/contacts?type=colleague | ✅ 通过 | 正确返回内部同事 |
| **邮件模板管理** | | | |
| 模板列表 | GET /api/templates | ✅ 通过 | 分页格式正确 |
| 创建开通模板 | POST /api/templates (provision) | ✅ 通过 | 返回 201，含 id |
| 创建临期模板 | POST /api/templates (expiry_warning) | ✅ 通过 | 返回 201，含 id |
| 创建回收模板 | POST /api/templates (reclaim) | ✅ 通过 | 返回 201，含 id |
| 模板预览 | POST /api/templates/preview | ✅ 通过 | Jinja2 变量正确渲染 |
| **租赁记录管理** | | | |
| 创建租赁记录 | POST /api/rentals | ✅ 通过 | 返回 201，含完整信息 |
| 租赁列表 | GET /api/rentals | ✅ 通过 | 分页格式正确 |
| 租赁详情 | GET /api/rentals/{id} | ✅ 通过 | 密码明文解密、contacts、email_logs 完整 |
| 状态筛选 | GET /api/rentals?status=provisioned | ✅ 通过 | 筛选结果正确 |
| 更新租赁(部分字段) | PUT /api/rentals/{id} (仅remark) | ✅ 通过 | 返回 200 |
| 更新租赁(全量) | PUT /api/rentals/{id} (含contacts) | ❌ 失败 | **Bug #001**: 500 Internal Server Error |
| 删除租赁 | DELETE /api/rentals/{id} | ✅ 通过 | 返回 200，再次查询返回 404 |
| **邮件发送** | | | |
| 发送开通邮件 | POST /api/rentals/{id}/send-provision-email | ✅ 通过 | 返回 200（SMTP 未配置，事件触发但不发送） |
| 发送临期提醒 | POST /api/rentals/{id}/send-expiry-reminder | ✅ 通过 | 返回 200 |
| 回收操作 | POST /api/rentals/{id}/reclaim | ✅ 通过 | 状态变更为 reclaimed |
| 不存在ID发送 | POST /api/rentals/{nonexistent}/send-provision-email | ✅ 通过 | 返回 404 友好错误 |
| **发送日志** | | | |
| 日志列表 | GET /api/logs | ✅ 通过 | 分页格式正确（为空） |
| 日志详情 | GET /api/logs/{id} | ✅ 通过 | 不存在的 ID 返回 404 |
| **SMTP 配置** | | | |
| 获取配置 | GET /api/system/smtp | ✅ 通过 | 未配置时返回 404 友好提示 |
| 更新配置 | PUT /api/system/smtp | ✅ 通过 | 返回 200，密码不回显 |
| 测试连接 | POST /api/system/smtp/test | ✅ 通过 | 返回连接结果（成功/失败） |

### 测试环境
- 后端 API: http://192.168.180.170:30082/api
- 测试时间: 2026-06-24 13:46 ~ 13:50 UTC

### 使用的测试数据
- 客户1: c0441ac5-b27f-4876-b3fe-aec901a50217 (测试客户-已更新)
- 客户2: bbc3b5aa-4d70-4ce4-8631-e9c78ddd600e (测试客户2)
- 联系人(张三): fe2bd0b7-0763-4604-a7bf-6ce8e21c60fd
- 联系人(内部-李四): 3ce064c5-5d08-4d19-999f-aadffe99b335
- 模板(开通): 5a093ffc-da4a-4a38-8e33-2325fd24c6c1
- 模板(临期): 21fab83b-39e1-4224-9f6a-190444c61c61
- 模板(回收): 552f30cb-75f4-40df-be53-a4dbca52ef08
- 租赁记录1: 9616fbd8-b7b9-4af7-ab14-9ed3868f5486 (已回收)
- 租赁记录2: 09cc565b-5ba8-4c6a-a2a1-9345374f5f6d (已删除)
