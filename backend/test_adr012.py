"""ADR-012 集成测试"""
import os
os.environ['DATABASE_URL'] = 'sqlite:///test_adr012.db'

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
# 测试 1: 创建客户
# ============================================================
print("1. Create Customer")
resp = client.post('/api/customers', json={'name': '测试公司-ADR012', 'remark': 'ADR-012测试'})
check("status 2xx", resp.status_code in (200, 201), f"got {resp.status_code}: {resp.text}")
cust = resp.json()
customer_id = cust.get('id')
check("customer_id present", customer_id is not None, str(cust))

# ============================================================
# 测试 2: 创建算力服务合同（带 service_lines）
# ============================================================
print("\n2. Create Contract with service_lines")
contract_data = {
    'customer_id': customer_id,
    'name': 'ADR-012 测试合同',
    'contract_no': 'ADR012-001',
    'contract_type': 'sales',
    'party_a_name': '甲方公司',
    'party_b_name': '乙方公司',
    'start_date': '2026-07-01',
    'end_date': '2027-06-30',
    'remark': 'ADR-012 功能测试',
    'service_lines': [
        {
            'category': '计算资源',
            'item_name': 'GPU A100',
            'specification': {'gpu': 'A100', 'count': 8},
            'vcpu_count': '64',
            'memory_gb': '256',
            'storage_gb': '1000',
            'unit': '台/月',
            'quantity': '2',
            'period_months': 12,
            'unit_price': '50000',
            'total_price': '1200000',
            'sort_order': 0,
        },
        {
            'category': '存储资源',
            'item_name': '对象存储',
            'unit': 'TB/月',
            'quantity': '10',
            'period_months': 12,
            'unit_price': '1000',
            'total_price': '120000',
            'sort_order': 1,
        },
    ],
}
resp = client.post('/api/compute-service-contracts', json=contract_data)
check("status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text}")
contract = resp.json()
contract_id = contract.get('id')
check("contract_type=sales", contract.get('contract_type') == 'sales')
check("party_a_name", contract.get('party_a_name') == '甲方公司')
check("party_b_name", contract.get('party_b_name') == '乙方公司')
check("amount auto-calc", contract.get('amount') is not None, f"amount={contract.get('amount')}")
check("amount_auto_calc", contract.get('amount_auto_calc') is not None, f"auto_calc={contract.get('amount_auto_calc')}")
check("service_lines count=2", len(contract.get('service_lines', [])) == 2, f"got {len(contract.get('service_lines', []))}")
check("start_date", contract.get('start_date') == '2026-07-01')
check("end_date", contract.get('end_date') == '2027-06-30')
print(f"   amount={contract.get('amount')}, auto_calc={contract.get('amount_auto_calc')}")

# ============================================================
# 测试 3: 创建第二个合同（背靠背关联）
# ============================================================
print("\n3. Create Related Contract")
contract2_data = {
    'customer_id': customer_id,
    'name': 'ADR-012 关联采购合同',
    'contract_no': 'ADR012-002',
    'contract_type': 'procurement',
    'party_a_name': '我方公司',
    'party_b_name': '供应商公司',
    'related_contract_id': contract_id,
    'remark': '背靠背关联测试',
}
resp = client.post('/api/compute-service-contracts', json=contract2_data)
check("status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text}")
contract2 = resp.json()
contract2_id = contract2['id']
check("contract_type=procurement", contract2.get('contract_type') == 'procurement')
check("related_contract present", contract2.get('related_contract') is not None)
print(f"   related_contract: {json.dumps(contract2.get('related_contract'), ensure_ascii=False)}")

# ============================================================
# 测试 4: 获取合同详情（验证双向关联）
# ============================================================
print("\n4. Get Contract Detail - verify bidirectional related")
resp = client.get(f'/api/compute-service-contracts/{contract_id}')
check("status 200", resp.status_code == 200, f"got {resp.status_code}")
c1 = resp.json()
check("reverse related_contract", c1.get('related_contract') is not None, "should find contract2 via reverse lookup")
if c1.get('related_contract'):
    check("reverse related_contract.id", c1['related_contract']['id'] == contract2_id, f"expected {contract2_id}, got {c1['related_contract']['id']}")

# ============================================================
# 测试 5: 列表查询
# ============================================================
print("\n5. List Contracts")
resp = client.get('/api/compute-service-contracts')
check("status 200", resp.status_code == 200)
list_data = resp.json()
check("total >= 2", list_data.get('total', 0) >= 2, f"total={list_data.get('total')}")
item_with_lines = next((i for i in list_data.get('items', []) if i['id'] == contract_id), None)
check("service_lines_count=2", item_with_lines is not None and item_with_lines['service_lines_count'] == 2,
      f"got {item_with_lines.get('service_lines_count') if item_with_lines else 'None'}")
for item in list_data.get('items', []):
    print(f"   - {item['name']}: lines_count={item.get('service_lines_count')}, type={item.get('contract_type')}")

# ============================================================
# 测试 6: Service Lines 子路由 - 列表
# ============================================================
print("\n6. List Service Lines")
resp = client.get(f'/api/compute-service-contracts/{contract_id}/service-lines')
check("status 200", resp.status_code == 200)
lines = resp.json()
check("count=2", len(lines) == 2, f"got {len(lines)}")
for l in lines:
    print(f"   - {l['category']}/{l['item_name']}: qty={l['quantity']} total={l['total_price']}")

# ============================================================
# 测试 7: Service Lines 子路由 - 新增单行
# ============================================================
print("\n7. Create Service Line")
new_line = {
    'category': '网络资源',
    'item_name': '专线带宽',
    'unit': 'Mbps/月',
    'quantity': '100',
    'period_months': 12,
    'unit_price': '500',
    'total_price': '600000',
    'sort_order': 2,
}
resp = client.post(f'/api/compute-service-contracts/{contract_id}/service-lines', json=new_line)
check("status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text}")
line = resp.json()
line_id = line['id']
check("category=网络资源", line.get('category') == '网络资源')
print(f"   id={line_id}")

# ============================================================
# 测试 8: Service Lines 子路由 - 更新单行
# ============================================================
print("\n8. Update Service Line")
update_data = {'quantity': '200', 'total_price': '1200000'}
resp = client.put(f'/api/compute-service-contracts/{contract_id}/service-lines/{line_id}', json=update_data)
check("status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text}")
updated = resp.json()
check("quantity=200", updated['quantity'] == '200.00', f"got {updated['quantity']}")
check("total_price=1200000", updated['total_price'] == '1200000.00', f"got {updated['total_price']}")

# ============================================================
# 测试 9: Service Lines 子路由 - 删除单行
# ============================================================
print("\n9. Delete Service Line")
resp = client.delete(f'/api/compute-service-contracts/{contract_id}/service-lines/{line_id}')
check("status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text}")
resp = client.get(f'/api/compute-service-contracts/{contract_id}/service-lines')
check("remaining=2", len(resp.json()) == 2, f"got {len(resp.json())}")

# ============================================================
# 测试 10: Service Lines 批量保存（全量替换）
# ============================================================
print("\n10. Batch Save Service Lines")
batch_data = {
    'lines': [
        {
            'category': '计算资源',
            'item_name': 'GPU H100',
            'specification': {'gpu': 'H100', 'count': 4},
            'vcpu_count': '32',
            'memory_gb': '128',
            'unit': '台/月',
            'quantity': '4',
            'period_months': 6,
            'unit_price': '80000',
            'total_price': '1920000',
            'sort_order': 0,
        },
    ],
}
resp = client.post(f'/api/compute-service-contracts/{contract_id}/service-lines/batch', json=batch_data)
check("status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text}")
batch_lines = resp.json()
check("count=1", len(batch_lines) == 1, f"got {len(batch_lines)}")
check("item_name=GPU H100", len(batch_lines) > 0 and batch_lines[0]['item_name'] == 'GPU H100')
for l in batch_lines:
    print(f"   - {l['category']}/{l['item_name']}: total={l['total_price']}")

# ============================================================
# 测试 11: 验证详情中 amount_auto_calc 随 batch save 更新
# ============================================================
print("\n11. Verify amount_auto_calc after batch save")
resp = client.get(f'/api/compute-service-contracts/{contract_id}')
c = resp.json()
print(f"   amount={c.get('amount')}, amount_auto_calc={c.get('amount_auto_calc')}")
check("amount_auto_calc matches", c.get('amount_auto_calc') is not None)

# ============================================================
# 测试 12: 更新合同
# ============================================================
print("\n12. Update Contract")
update = {
    'name': 'ADR-012 测试合同（已修改）',
    'party_a_name': '新甲方',
    'remark': '已更新',
}
resp = client.put(f'/api/compute-service-contracts/{contract_id}', json=update)
check("status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text}")
c = resp.json()
check("name updated", c['name'] == 'ADR-012 测试合同（已修改）')
check("party_a_name updated", c['party_a_name'] == '新甲方')

# ============================================================
# 测试 13: 删除合同（级联删除 service_lines）
# ============================================================
print("\n13. Delete Contract (cascade)")
resp = client.delete(f'/api/compute-service-contracts/{contract_id}')
check("status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text}")
resp = client.get(f'/api/compute-service-contracts/{contract_id}/service-lines')
check("service lines deleted", resp.status_code == 404, f"got {resp.status_code}")

# ============================================================
# 测试 14: 删除第二个合同
# ============================================================
print("\n14. Delete Related Contract")
resp = client.delete(f'/api/compute-service-contracts/{contract2_id}')
check("status 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text}")

# ============================================================
# 测试 15: 清理客户
# ============================================================
print("\n15. Cleanup - Delete Customer")
resp = client.delete(f'/api/customers/{customer_id}')
check("status 200", resp.status_code in (200, 404), f"got {resp.status_code}: {resp.text}")

# ============================================================
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
print(f"{'='*60}")
PYEOF
