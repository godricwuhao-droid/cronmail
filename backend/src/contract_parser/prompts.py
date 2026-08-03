"""合同解析 Prompt 模板"""

SYSTEM_PROMPT = """你是一个合同信息提取助手。请从以下合同文本中提取关键字段。
返回严格的 JSON 格式，不要任何额外文字、解释或 markdown 标记。
找不到的字段填 null，日期统一为 YYYY-MM-DD 格式。"""

# 按 contract_type 返回不同字段
FIELD_TEMPLATES = {
    "compute_service": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "party_a_name": "甲方名称",
  "party_b_name": "乙方名称",
  "amount": "合同总金额，仅数字，如 1500000.00，无则null",
  "start_date": "合同开始日期 YYYY-MM-DD",
  "end_date": "合同结束日期 YYYY-MM-DD",
  "project_name": "所属项目名称",
  "contract_content": "附件表格中一级服务清单内容，如计算资源、存储资源等服务项名称和规格，不超过300字",
  "delivery_requirements": "合同中关于交付的要求：交付时间要求、交付物要求、甲乙方交付负责人姓名及联系方式，不超过300字",
  "remark": "其他备注信息"
}""",

    "compute_leasing": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "billing_model": "计费方式：月付填monthly，季付填quarterly，年付填yearly，无法判断填null",
  "amount": "合同总金额，仅数字，如 1500000.00，无则null",
  "start_date": "合同开始日期 YYYY-MM-DD",
  "end_date": "合同结束日期 YYYY-MM-DD"
}""",

    "satellite_data": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "contract_type": "合同子类型描述",
  "party_a_name": "甲方名称",
  "party_b_name": "乙方名称",
  "amount": "合同总金额，仅数字",
  "start_date": "合同开始日期 YYYY-MM-DD",
  "end_date": "合同结束日期 YYYY-MM-DD",
  "project_name": "所属项目名称",
  "contract_content": "合同主要内容概述",
  "delivery_requirements": "合同交付要求"
}""",

    "project": """请提取以下字段。合同中的服务清单表格通常包含多行，每行是一种容器/服务类型。

特别注意：
- 甲方（party_a_name）：合同中标注"甲方"后的公司全称
- 乙方（party_b_name）：合同中标注"乙方"后的公司全称
- 表格：识别文档中所有表格，每张表格保持原始行列结构

返回格式：
{
  "name": "合同标题",
  "contract_no": "合同编号",
  "party_a_name": "甲方全称",
  "party_b_name": "乙方全称",
  "amount": "合同总金额（纯数字）",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "project_name": "所属项目",
  "contract_content": "合同主要内容概述",
  "delivery_requirements": "交付要求",
  "remark": "其他备注",
  "raw_tables": [
    {
      "table_index": 1,
      "title": "表格标题（如有）",
      "headers": ["列1名", "列2名", "..."],
      "rows": [
        ["值1", "值2", "..."],
        ["值1", "值2", "..."]
      ]
    }
  ],
  "service_lines": [
    {
      "category": "服务大类",
      "item_name": "服务项名称",
      "specification": {"参数名": "参数值"},
      "unit": "单位",
      "quantity": "数字",
      "period_months": "数字，默认12",
      "unit_price": "数字",
      "service_description": "补充说明"
    }
  ],
  "resource_summary": {
    "stats": {"vcpu": "总vCPU核数", "memory_gb": "总内存GB", "storage_gb": "总存储GB", "gpu_count": "总GPU卡数", "gpu_tops": "总算力TOPS", "bandwidth_mbps": "总带宽Mbps", "rack_count": "总机柜数", "ip_count": "总IP数"},
    "summary_text": "总体交付内容概述，如'总计10台服务器，含40核CPU、160GB内存、500GB存储、8卡GPU'"
  }
}

注意：
- 找不到的字段填 null，数字字段无则填 0
- raw_tables 保持表格原始行列结构，表头从文档中动态识别
- resource_summary.stats 中只填能从表格中实际提取到的数值，没有的填 0 或 null
- service_lines 中 specification 用原始表格的列名做 key""",
}


def build_user_prompt(contract_type: str, contract_text: str) -> str:
    """组装完整 user prompt"""
    field_prompt = FIELD_TEMPLATES.get(contract_type, FIELD_TEMPLATES["compute_service"])
    # Qwen 27B 支持 256K tokens，这里用 64K tokens ≈ ~6万中文字符
    max_chars = 60000
    if len(contract_text) > max_chars:
        contract_text = contract_text[:max_chars] + "\n...(内容过长已截断)"

    return f"{field_prompt}\n\n合同文本：\n{contract_text}"


# ============================================================
# 多模态 Vision Prompt（PDF 图片模式）
# ============================================================

VISION_SYSTEM_PROMPT = """你是一个精确的合同信息提取助手。接下来你会看到合同文件的逐页图片。

核心任务：
1. 在合同首部仔细查找"甲方："和"乙方："标注，提取后面的公司全称
2. 如果没有"甲方："字样，查找签约方、合同当事人信息
3. 每张图都要仔细阅读，不要遗漏任何文字

返回严格的 JSON 格式，找不到填 null，不要任何额外文字。"""

VISION_FIELD_TEMPLATES = {
    "project": """请逐页阅读合同图片，提取所有关键信息。

表格处理规则：
- 只录入"服务清单""报价明细""设备清单"等交付内容表格
- 不要录入验收单、确认单、签字页、审批单等非服务内容表格
- 每张表格保持原始行列结构，表头用文档中的原文

特别注意：
- 甲方（party_a_name）：合同中标注"甲方"后的公司全称
- 乙方（party_b_name）：合同中标注"乙方"后的公司全称

返回格式：
{
  "name": "合同标题",
  "contract_no": "合同编号",
  "party_a_name": "甲方全称",
  "party_b_name": "乙方全称",
  "amount": "合同总金额（纯数字）",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "project_name": "所属项目",
  "contract_content": "合同主要内容概述",
  "delivery_requirements": "交付要求",
  "remark": "其他备注",
  "raw_tables": [
    {
      "table_index": 1,
      "title": "表格标题（服务清单/报价明细等，不是验收单）",
      "headers": ["列1", "列2"],
      "rows": [["值1", "值2"]]
    }
  ],
  "resource_summary": {
    "stats": {"vcpu": 0, "memory_gb": 0, "storage_gb": 0, "gpu_count": 0, "gpu_tops": 0, "bandwidth_mbps": 0, "rack_count": 0, "ip_count": 0},
    "summary_text": "交付内容概述"
  }
}

找不到的字段填 null，数字无则填 0。""",
}


def build_vision_user_prompt(contract_type: str, page_count: int) -> str:
    """组装多模态 user prompt（文字部分）"""
    field_prompt = VISION_FIELD_TEMPLATES.get(contract_type, VISION_FIELD_TEMPLATES["project"])
    return f"以下是一份共 {page_count} 页的合同文件，请逐页阅读后提取关键信息：\n\n{field_prompt}"


def get_vision_page_prompt(contract_type: str, page_num: int, total_pages: int, accumulated: str = None) -> str:
    """构建单页分析 prompt"""
    field_prompt = VISION_FIELD_TEMPLATES.get(contract_type, VISION_FIELD_TEMPLATES["project"])
    header = f"这是第 {page_num}/{total_pages} 页。"

    table_rule = "表格规则：只录入\"服务清单\"\"报价明细\"\"设备清单\"等交付内容表格，验收单、确认单、签字页不要录入。"

    if accumulated is None:
        ctx = f"这是第一页，请开始提取合同关键信息。{table_rule}"
    else:
        ctx = f"""前面已提取的字段如下（请在此基础上补充修正，不要重复已提取的表格）：

{accumulated}

如果本页有新的信息或需要修正前面的提取结果，请返回完整的字段内容。如果没有新信息，返回空对象 {{}}。{table_rule}"""

    return f"{header}\n{ctx}\n\n{field_prompt}"


def get_vision_final_prompt(contract_type: str, accumulated: str) -> str:
    """构建最终汇总 prompt"""
    return f"""请综合以下所有页面的提取结果，进行最终校验和汇总。注意：

1. raw_tables 去重：同一张表出现多次只保留一次
2. 删除非交付表格：去掉验收单、确认单、签字页等
3. resource_summary.stats 只填实际从表格中提取到的数值
4. 格式化：日期 YYYY-MM-DD，金额纯数字

已提取的全部内容：
{accumulated}

请返回最终的完整 JSON。"""
