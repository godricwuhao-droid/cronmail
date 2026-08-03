"""
项目管理合同模块 Pydantic Schema
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# ProjectServiceLine Schemas
# ============================================================

class ProjectServiceLineCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="服务大类")
    item_name: str = Field(..., min_length=1, max_length=100, description="服务项")
    specification: Optional[dict] = Field(None, description="异构规格，仅展示")
    unit: str = Field(..., min_length=1, max_length=20, description="单位")
    quantity: Decimal = Field(..., description="数量")
    period_months: int = Field(1, ge=1, description="周期月数")
    unit_price: Decimal = Field(..., description="单价")
    sort_order: int = Field(0, description="排序")
    service_description: Optional[str] = Field(None, description="服务描述长文本")


class ProjectServiceLineUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    item_name: Optional[str] = Field(None, min_length=1, max_length=100)
    specification: Optional[dict] = None
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    quantity: Optional[Decimal] = None
    period_months: Optional[int] = Field(None, ge=1)
    unit_price: Optional[Decimal] = None
    sort_order: Optional[int] = None
    service_description: Optional[str] = None


class ProjectServiceLineResponse(BaseModel):
    id: str
    contract_id: str
    category: str
    item_name: str
    specification: Optional[dict] = None
    unit: str
    quantity: Decimal
    period_months: int
    unit_price: Decimal
    total_price: Decimal
    sort_order: int
    service_description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectServiceLineBatchSave(BaseModel):
    lines: list[ProjectServiceLineCreate] = Field(..., description="服务行列表（全量替换）")


# ============================================================
# ProjectContract Schemas
# ============================================================

class RelatedProjectContractBrief(BaseModel):
    """背靠背关联合同简要信息"""
    id: str
    name: str
    contract_no: Optional[str] = None
    contract_type: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectContractCreate(BaseModel):
    company_code: str = Field(..., min_length=1, max_length=20, description="公司: fengyun/tianshu/qianxing")
    name: str = Field(..., min_length=1, max_length=255, description="合同名称")
    contract_no: Optional[str] = Field(None, max_length=100, description="合同编号")
    contract_type: str = Field("sales", pattern=r"^(sales|procurement)$", description="合同类型")
    party_a_name: Optional[str] = Field(None, max_length=255, description="甲方名称")
    party_b_name: Optional[str] = Field(None, max_length=255, description="乙方名称")
    amount: Optional[Decimal] = Field(None, description="合同总金额")
    start_date: Optional[date] = Field(None, description="合同开始日期")
    end_date: Optional[date] = Field(None, description="合同结束日期")
    related_contract_id: Optional[str] = Field(None, description="背靠背关联合同ID")
    project_name: Optional[str] = Field(None, max_length=255, description="所属项目")
    project_type: Optional[str] = Field(None, max_length=100, description="项目类型，如算力服务合同")
    contract_content: Optional[str] = Field(None, description="合同内容")
    delivery_requirements: Optional[str] = Field(None, description="合同交付要求")
    process_records: Optional[str] = Field(None, description="过程记录")
    raw_tables_json: Optional[str] = Field(None, description="原始表格JSON，AI解析结果")
    remark: Optional[str] = Field(None, description="备注")
    sort_order: Optional[int] = Field(0, description="排序序号")
    service_lines: Optional[list[ProjectServiceLineCreate]] = Field(None, description="服务行列表")


class ProjectContractUpdate(BaseModel):
    company_code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contract_no: Optional[str] = Field(None, max_length=100)
    contract_type: Optional[str] = Field(None, pattern=r"^(sales|procurement)$")
    party_a_name: Optional[str] = Field(None, max_length=255)
    party_b_name: Optional[str] = Field(None, max_length=255)
    amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    related_contract_id: Optional[str] = None
    project_name: Optional[str] = Field(None, max_length=255)
    project_type: Optional[str] = Field(None, max_length=100, description="项目类型，如算力服务合同")
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    raw_tables_json: Optional[str] = None
    remark: Optional[str] = None
    sort_order: Optional[int] = None
    service_lines: Optional[list[ProjectServiceLineCreate]] = None


class ProjectContractListResponse(BaseModel):
    """列表项（不含完整 service_lines，含 service_lines_count）"""
    id: str
    company_code: str
    name: str
    contract_no: Optional[str] = None
    contract_type: Optional[str] = None
    party_a_name: Optional[str] = None
    party_b_name: Optional[str] = None
    amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    related_contract_id: Optional[str] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    remark: Optional[str] = None
    sort_order: int = 0
    service_lines_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectContractResponse(BaseModel):
    """详情（含完整 service_lines 和 related_contract）"""
    id: str
    company_code: str
    name: str
    contract_no: Optional[str] = None
    contract_type: Optional[str] = None
    party_a_name: Optional[str] = None
    party_b_name: Optional[str] = None
    amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    related_contract_id: Optional[str] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    raw_tables_json: Optional[str] = None
    remark: Optional[str] = None
    sort_order: int = 0
    service_lines: list[ProjectServiceLineResponse] = []
    related_contract: Optional[RelatedProjectContractBrief] = None
    amount_auto_calc: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectContractListWrap(BaseModel):
    items: list[ProjectContractListResponse]
    total: int
    page: int = 1
    page_size: int = 20
