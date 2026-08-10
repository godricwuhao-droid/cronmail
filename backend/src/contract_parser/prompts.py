"""合同解析 Prompt（硬编码版本）"""

# ============================================================
# System Prompts
# ============================================================

SYSTEM_PROMPT = (
    "你是一个合同信息提取助手。请从以下合同文本中提取关键字段。\n"
    "【严格字段约束】只允许返回 user prompt 中定义的字段，禁止自行添加任何额外字段。\n"
    "返回严格的 JSON 格式，不要任何额外文字、解释或 markdown 标记。\n"
    "找不到的字段填 null，日期统一为 YYYY-MM-DD 格式。"
)

# ============================================================
# 阶段 1：OCR System Prompt（纯文字提取）
# ============================================================

OCR_SYSTEM_PROMPT = (
    "你是一个精确的文档 OCR 助手。你会看到合同文件的连续几页图片。\n\n"
    "任务：将图片中的所有文字逐字输出为纯文本。\n\n"
    "规则：\n"
    "1. 逐字输出，不要遗漏任何文字，不要总结或改写\n"
    "2. 保留原文的层级结构（标题、段落、编号）\n"
    "3. 表格用 Markdown 表格格式输出（| 列1 | 列2 |），表头加粗\n"
    "4. 跨页的表格请合并为一张完整的表\n"
    "5. 每页之间用 \"--- 第N页 ---\" 分隔\n"
    "6. 不要添加任何解释、不要输出 JSON、不要 markdown 代码块标记\n"
    "直接输出纯文本内容。"
)

# ============================================================
# 阶段 2：汇总提取 System Prompt（从全文提取结构化 JSON）
# ============================================================

EXTRACT_SYSTEM_PROMPT = (
    "你是一个精确的合同信息提取助手。请从以下合同全文文本中提取关键信息。\n\n"
    "提取规则（按优先级执行，不要遗漏任何字段）：\n"
    "1. 【最重要】甲方全称(party_a_name)和乙方全称(party_b_name)：\n"
    "   在合同全文文本中搜索\"甲方\"\"乙方\"\"甲方（\"\"乙方（\"\"甲方：\"\"乙方：\"等关键词，提取紧跟其后的公司完整名称。\n"
    "   务必输出这两个字段，即使看起来很明显。无则填 null。\n"
    "2. 合同名称/编号：合同封面或首部的标题和编号\n"
    "3. 金额：合同总金额，仅提取数字（如 1500000.00），去除货币符号和中文单位\n"
    "4. 日期：统一为 YYYY-MM-DD 格式\n"
    "5. 项目名称：合同关联的项目名称\n"
    "6. 合同主要内容：概述合同正文的核心内容，重点关注服务项名称、规格参数（CPU/内存/GPU/存储等）\n"
    "   注意：附件中的确认单、验收单内容不要纳入此字段，只看合同正文\n"
    "7. 交付/验收要求：查找\"验收\"\"交付标准\"\"交付条件\"等关键字，提取验收要求、交付物清单、验收方式\n"
    "   注意：只提取合同正文中的交付要求，附件确认单中的验收签字内容不要纳入\n"
    "8. 合同类型：判断销售/采购性质，sales 或 procurement，无法判断填 null\n"
    "9. 执行过程记录：合同中关于执行过程、变更记录等内容，无则填 null\n"
    "10. 甲方委派人及联系方式：查找甲方委派人、甲方代表、甲方联系人及其电话/邮箱，无则填 null\n"
    "11. 乙方委派人及联系方式：查找乙方委派人、乙方代表、乙方联系人及其电话/邮箱，无则填 null\n"
    "12. 备注：其他需要记录的信息（如附件列表等），非核心信息放这里\n\n"
    "表格规则：\n"
    "- 只录入\"服务清单\"\"报价明细\"\"设备清单\"\"交付物清单\"等交付内容表格\n"
    "- 绝对不要录入确认单、验收单、签字页、审批单中的表格\n"
    "- 每张表格保持原始行列结构，表头用文档原文\n"
    "- 表格中的每一行都要录入，不要遗漏\n\n"
    "返回格式（严格 JSON，找不到填 null）：\n"
    "{\n"
    '  "name": "合同标题",\n'
    '  "contract_no": "合同编号",\n'
    '  "party_a_name": "甲方全称",\n'
    '  "party_b_name": "乙方全称",\n'
    '  "amount": "合同总金额（纯数字）",\n'
    '  "start_date": "YYYY-MM-DD",\n'
    '  "end_date": "YYYY-MM-DD",\n'
    '  "project_name": "所属项目",\n'
    '  "contract_content": "合同正文主要内容概述（不含附件确认单内容）",\n'
    '  "delivery_requirements": "验收标准/交付要求（合同正文中的）",\n'
    '  "remark": "其他备注",\n'
    '  "contract_type": "sales 或 procurement，无法判断填 null",\n'
    '  "process_records": "执行过程记录，无则填 null",\n'
    '  "party_a_contact": "甲方委派人及联系方式，无则填 null",\n'
    '  "party_b_contact": "乙方委派人及联系方式，无则填 null",\n'
    '  "raw_tables": [\n'
    '    {\n'
    '      "table_index": 1,\n'
    '      "title": "表格标题（仅交付内容表格）",\n'
    '      "headers": ["列1", "列2"],\n'
    '      "rows": [["值1", "值2"]]\n'
    '    }\n'
    '  ],\n'
    '  "resource_summary": {\n'
    '    "items": [\n'
    '      {"vcpu": 12, "memory_gb": 12, "storage_gb": 560, "gpu_count": 1, "gpu_tops": 115, "qty": 140}\n'
    '    ],\n'
    '    "summary_text": "交付内容概述"\n'
    '  }\n'
    "}\n\n"
    "resource_summary.items 填写规则（极其重要！）：\n"
    "1. 遍历 raw_tables 中每一张表格的每一行\n"
    "2. 判断该行是否包含硬件资源（CPU/内存/存储/GPU），不含硬件资源的行（如 License、软件授权、服务费等）跳过\n"
    "3. 找到该行的\"数量\"列（表格中通常是纯数字的列，如 140、108 等），填入 qty\n"
    "4. 从该行文本中解析硬件参数数值，填入对应字段：\n"
    "   - vcpu：匹配\"vCPU\"、\"CPU核心\"、\"处理器\"后的数字，\"X 核\"、\"X 核心\"\n"
    "   - memory_gb：匹配\"内存\"后的 \"X GB\"、\"X G\"、\"X GB DDR4\"\n"
    "   - storage_gb：匹配\"存储\"、\"硬盘\"、\"SSD\"、\"非易失性存储\"后的 \"X GB\"或\"X TB\"（TB×1024转GB）\n"
    "   - gpu_count：含\"GPU\"、\"显卡\"、\"算力核心\"则填 1；如明确写\"X*GPU\"则填 X\n"
    "   - gpu_tops：匹配\"TFLOPS\"、\"TOPS\"、\"FP16 算力\"、\"算力\"后的数字\n"
    "5. 没有的参数填 0\n"
    "6. 不要自行乘法累加，只需逐行填入原始参数值和数量即可\n\n"
    "【严格约束】禁止添加上述字段之外的任何字段。返回纯 JSON，不要 markdown 标记、不要解释文字。"
)

# ============================================================
# 文本模式字段模板
# ============================================================

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

    "project": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "party_a_name": "甲方全称",
  "party_b_name": "乙方全称",
  "amount": "合同总金额（纯数字）",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "project_name": "所属项目",
  "contract_content": "合同主要内容概述，重点关注表格中服务项的名称、规格参数（如CPU/内存/GPU/存储等）",
  "delivery_requirements": "验收标准，查找合同中\"验收\"\"交付标准\"\"交付条件\"等关键字，提取验收要求、交付物清单、验收方式等",
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

resource_summary 统计规则：
- 遍历 raw_tables 中所有表格的所有行
- 参数/规格通常在文本描述中（如"处理器：12 vCPU核心，内存：12GB DDR4，GPU 32GB显存，存储：560GB"），从文本中解析数值
- 每行参数值 × 该行数量 = 该行资源量，所有行累加：
  vcpu：CPU/vCPU/处理器核心数值 × 数量
  memory_gb：内存/GB/DDR数值 × 数量
  storage_gb：存储/硬盘/GB/TB数值 × 数量（TB需×1024转GB）
  gpu_count：GPU/显卡/算力核心数值 × 数量
  gpu_tops：TFLOPS/TOPS/算力数值 × 数量
- 不要遗漏任何一行
- 没有的填 0

找不到的字段填 null，数字无则填 0。""",
}

# ============================================================
# 非 project 类型的字段模板（用于阶段 2 汇总）
# ============================================================

EXTRACT_FIELD_TEMPLATES = {
    "compute_service": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "party_a_name": "甲方名称",
  "party_b_name": "乙方名称",
  "amount": "合同总金额，仅数字",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "project_name": "所属项目名称",
  "contract_content": "合同主要内容概述",
  "delivery_requirements": "交付要求",
  "remark": "其他备注信息"
}""",

    "compute_leasing": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "billing_model": "计费方式：月付monthly，季付quarterly，年付yearly",
  "amount": "合同总金额，仅数字",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD"
}""",

    "satellite_data": """请提取以下字段：
{
  "name": "合同名称",
  "contract_no": "合同编号",
  "contract_type": "合同子类型",
  "party_a_name": "甲方名称",
  "party_b_name": "乙方名称",
  "amount": "合同总金额，仅数字",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "project_name": "所属项目名称",
  "contract_content": "合同主要内容概述",
  "delivery_requirements": "合同交付要求"
}""",
}


# ============================================================
# Prompt 构建函数
# ============================================================

def build_user_prompt(contract_type: str, contract_text: str) -> str:
    """组装完整 user prompt（文本模式）"""
    field_prompt = FIELD_TEMPLATES.get(contract_type, FIELD_TEMPLATES.get("project", ""))
    max_chars = 128000
    if len(contract_text) > max_chars:
        contract_text = contract_text[:max_chars] + "\n...(内容过长已截断)"
    return f"{field_prompt}\n\n合同文本：\n{contract_text}"


def get_ocr_batch_prompt(batch_num: int, total_batches: int, start_page: int, end_page: int) -> str:
    """阶段 1 OCR：告诉 LLM 这是第几批、第几页"""
    return f"请输出第 {start_page}-{end_page} 页的文字内容（共 {total_batches} 批中的第 {batch_num} 批）。"




# ============================================================
# 回款凭证解析专用 Prompt（独立于合同解析）
# ============================================================

PAYMENT_RECEIPT_SYSTEM_PROMPT = (
    "你是一个精确的财务凭证提取助手。请从回执单/发票的 OCR 文本中提取回款信息。\n\n"
    "提取规则：\n"
    "1. 回款金额(amount)：查找\"金额\"\"合计\"\"大写\"\"小写\"\"实收\"\"收款\"等关键词后的数字，只输出纯数字（如 500000.00）\n"
    "2. 回款日期(payment_date)：查找\"日期\"\"开票日期\"\"收款日期\"等关键词后的日期，统一为 YYYY-MM-DD 格式\n"
    "3. 付款方(payer)：付款方公司全称\n"
    "4. 凭证类型(doc_type)：判断是\"回执单\"还是\"发票\"\n"
    "\n"
    "输出格式（严格 JSON，不要加代码块标记）：\n"
    '{"amount": "数字", "payment_date": "YYYY-MM-DD", "payer": "付款方", "doc_type": "回执单/发票"}'
)

PAYMENT_RECEIPT_EXTRACT_PROMPT = """请从以下凭证 OCR 文本中提取回款信息：

{full_text}

请返回 JSON（不要加 ```json 标记）。"""


def get_extract_prompt(contract_type: str, full_text: str) -> str:
    """阶段 2 汇总：从全文提取结构化 JSON"""
    if contract_type == "project":
        field_instruction = "请严格按照 system prompt 中的 JSON 格式提取所有字段。"
    else:
        field_template = EXTRACT_FIELD_TEMPLATES.get(contract_type, "")
        field_instruction = f"{field_template}\n\n请严格按上述格式返回 JSON。"

    return f"""以下是合同的完整文字内容：

{full_text}

{field_instruction}

注意：
- contract_content 和 delivery_requirements 只提取合同正文内容，不要包含附件中的确认单、验收单信息
- 确认单、验收单、签字页中的表格不要录入 raw_tables
- raw_tables 只录入服务清单、报价明细、设备清单等交付内容表格
- resource_summary.stats 从 raw_tables 精确统计"""
