"""ADR-013 集成测试：算力服务合同新增 4 字段"""
import os
os.environ['DATABASE_URL'] = 'sqlite:///test_adr013.db'

# 先创建表，再初始化 app
from src.core.database import engine, Base
# 导入所有模型确保 metadata 完整
import src.customer.models        # noqa
import src.rental.models          # noqa
import src.contract.models        # noqa
import src.template.models        # noqa
import src.mail.models            # noqa
import src.system.models           # noqa
import src.scheduler.models       # noqa
import src.attachment.models      # noqa
import src.satellite.models       # noqa
import src.compute_service.models # noqa

Base.metadata.create_all(bind=engine)

from main import app
from fastapi.testclient import TestClient
import json

client = TestClient(app)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {detail}")

# ============================================================
# 创建客户
# ============================================================
print("0. Create Customer")
resp = client.post('/api/customers', json={'name': '测试公司-ADR013', 'remark': 'ADR-013测试'})
check("status 2xx", resp.status_code in (200, 201), f"got {resp.status_code}: {resp.text}")
cust = resp.json()
customer_id = cust.get('id')

# ============================================================
# 测试 1: POST 创建合同 - 传入新字段
# ============================================================
print("\n1. POST - Create with new fields")
contract_data = {
    'customer_id': customer_id,
    'name': 'ADR-013 测试合同',
    'contract_no': 'ADR013-001',
    'contract_type': 'sales',
    'party_a_name': '甲方公司',
    'party_b_name': '乙方公司',
    'project_name': '深空探测项目',
    'contract_content': '本合同约定算力服务内容...',
    'delivery_requirements': '1. 按时交付\n2. 质量保证',
    'process_records': '2026-07-20: 合同起草\n2026-07-21: 内部审核',
    'remark': 'ADR-013 功能测试',
}
resp = client.post('/api/compute-service-contracts', json=contract_data)
check("status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text}")
contract = resp.json()
contract_id = contract.get('id')
check("project_name returned", contract.get('project_name') == '深空探测项目', f"got: {contract.get('project_name')}")
check("contract_content returned", contract.get('contract_content') == '本合同约定算力服务内容...', f"got: {contract.get('contract_content')}")
check("delivery_requirements returned", contract.get('delivery_requirements') == '1. 按时交付\n2. 质量保证', f"got: {contract.get('delivery_requirements')}")
check("process_records returned", contract.get('process_records') == '2026-07-20: 合同起草\n2026-07-21: 内部审核', f"got: {contract.get('process_records')}")

# ============================================================
# 测试 2: POST 创建合同 - 不传新字段（向后兼容）
# ============================================================
print("\n2. POST - Create without new fields (backward compat)")
contract2_data = {
    'customer_id': customer_id,
    'name': 'ADR-013 无新字段合同',
    'contract_type': 'sales',
}
resp = client.post('/api/compute-service-contracts', json=contract2_data)
check("status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text}")
c2 = resp.json()
contract2_id = c2.get('id')
check("project_name is None", c2.get('project_name') is None, f"got: {c2.get('project_name')}")
check("contract_content is None", c2.get('contract_content') is None)
check("delivery_requirements is None", c2.get('delivery_requirements') is None)
check("process_records is None", c2.get('process_records') is None)

# ============================================================
# 测试 3: GET 详情 - 返回新字段
# ============================================================
print("\n3. GET Detail - new fields in response")
resp = client.get(f'/api/compute-service-contracts/{contract_id}')
check("status 200", resp.status_code == 200)
detail = resp.json()
check("project_name in detail", detail.get('project_name') == '深空探测项目')
check("contract_content in detail", detail.get('contract_content') == '本合同约定算力服务内容...')
check("delivery_requirements in detail", detail.get('delivery_requirements') == '1. 按时交付\n2. 质量保证')
check("process_records in detail", detail.get('process_records') == '2026-07-20: 合同起草\n2026-07-21: 内部审核')

# ============================================================
# 测试 4: GET 列表 - 返回新字段
# ============================================================
print("\n4. GET List - new fields in response")
resp = client.get('/api/compute-service-contracts')
check("status 200", resp.status_code == 200)
list_data = resp.json()
item = next((i for i in list_data.get('items', []) if i['id'] == contract_id), None)
check("project_name in list", item is not None and item.get('project_name') == '深空探测项目', f"item: {item}")
check("contract_content in list", item is not None and item.get('contract_content') == '本合同约定算力服务内容...')

# ============================================================
# 测试 5: PUT 更新新字段
# ============================================================
print("\n5. PUT - Update new fields")
update = {
    'project_name': '深空探测项目（二期）',
    'contract_content': '更新后的合同内容...',
    'delivery_requirements': '更新后的交付要求',
    'process_records': '2026-07-23: 合同修订',
}
resp = client.put(f'/api/compute-service-contracts/{contract_id}', json=update)
check("status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text}")
updated = resp.json()
check("project_name updated", updated.get('project_name') == '深空探测项目（二期）')
check("contract_content updated", updated.get('contract_content') == '更新后的合同内容...')
check("delivery_requirements updated", updated.get('delivery_requirements') == '更新后的交付要求')
check("process_records updated", updated.get('process_records') == '2026-07-23: 合同修订')

# ============================================================
# 测试 6: PUT 更新 - 只更新部分新字段
# ============================================================
print("\n6. PUT - Partial update new fields")
partial_update = {'project_name': '深空探测项目（三期）'}
resp = client.put(f'/api/compute-service-contracts/{contract_id}', json=partial_update)
check("status 200", resp.status_code == 200)
p = resp.json()
check("project_name partial updated", p.get('project_name') == '深空探测项目（三期）')
check("contract_content preserved", p.get('contract_content') == '更新后的合同内容...', f"got: {p.get('contract_content')}")

# ============================================================
# 测试 7: 清空新字段（设为 None）
# ============================================================
print("\n7. PUT - Clear new fields (set to null)")
clear_update = {
    'project_name': None,
    'contract_content': None,
}
resp = client.put(f'/api/compute-service-contracts/{contract_id}', json=clear_update)
check("status 200", resp.status_code == 200)
cleared = resp.json()
check("project_name cleared", cleared.get('project_name') is None, f"got: {cleared.get('project_name')}")
check("contract_content cleared", cleared.get('contract_content') is None)

# ============================================================
# 清理
# ============================================================
print("\nCleanup")
client.delete(f'/api/compute-service-contracts/{contract_id}')
client.delete(f'/api/compute-service-contracts/{contract2_id}')
client.delete(f'/api/customers/{customer_id}')

# ============================================================
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
print(f"{'='*60}")
