"""
算力服务合同模块 Pydantic Schema
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# ContractServiceLine Schemas
# ============================================================

class ContractServiceLineCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="服务大类")
    item_name: str = Field(..., min_length=1, max_length=100, description="服务项")
    specification: Optional[dict] = Field(None, description="异构规格，仅展示")
    vcpu_count: Optional[Decimal] = Field(None, description="vCPU核数")
    memory_gb: Optional[Decimal] = Field(None, description="内存GB")
    storage_gb: Optional[Decimal] = Field(None, description="存储GB")
    unit: str = Field(..., min_length=1, max_length=20, description="单位")
    quantity: Decimal = Field(..., description="数量")
    period_months: int = Field(1, ge=1, description="周期月数")
    unit_price: Decimal = Field(..., description="单价")
    manual_total_price: Optional[Decimal] = Field(None, description="手动覆盖总价，留空则自动计算")
    sort_order: int = Field(0, description="排序")
    service_description: Optional[str] = Field(None, description="服务描述长文本")
    gpu_count: Optional[int] = Field(None, ge=0, description="每台GPU卡数")
    gpu_model: Optional[str] = Field(None, max_length=100, description="GPU型号")
    gpu_memory_gb: Optional[Decimal] = Field(None, description="单卡显存GB")
    gpu_tops: Optional[Decimal] = Field(None, description="单卡算力TOPS")


class ContractServiceLineUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    item_name: Optional[str] = Field(None, min_length=1, max_length=100)
    specification: Optional[dict] = None
    vcpu_count: Optional[Decimal] = None
    memory_gb: Optional[Decimal] = None
    storage_gb: Optional[Decimal] = None
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    quantity: Optional[Decimal] = None
    period_months: Optional[int] = Field(None, ge=1)
    unit_price: Optional[Decimal] = None
    manual_total_price: Optional[Decimal] = None
    sort_order: Optional[int] = None
    service_description: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_model: Optional[str] = None
    gpu_memory_gb: Optional[Decimal] = None
    gpu_tops: Optional[Decimal] = None


class ContractServiceLineResponse(BaseModel):
    id: str
    contract_id: str
    category: str
    item_name: str
    specification: Optional[dict] = None
    vcpu_count: Optional[Decimal] = None
    memory_gb: Optional[Decimal] = None
    storage_gb: Optional[Decimal] = None
    unit: str
    quantity: Decimal
    period_months: int
    unit_price: Decimal
    total_price: Decimal
    manual_total_price: Optional[Decimal] = None
    sort_order: int
    service_description: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_model: Optional[str] = None
    gpu_memory_gb: Optional[Decimal] = None
    gpu_tops: Optional[Decimal] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContractServiceLineBatchSave(BaseModel):
    lines: list[ContractServiceLineCreate] = Field(..., description="服务行列表（全量替换）")


# ============================================================
# ComputeServiceContract Schemas
# ============================================================

class RelatedContractBrief(BaseModel):
    """背靠背关联合同简要信息"""
    id: str
    name: str
    contract_no: Optional[str] = None
    contract_type: Optional[str] = None

    model_config = {"from_attributes": True}


class ComputeServiceContractCreate(BaseModel):
    customer_id: str = Field(..., description="客户ID")
    name: str = Field(..., min_length=1, max_length=255, description="合同名称")
    contract_no: Optional[str] = Field(None, max_length=100, description="合同编号")
    contract_type: str = Field("sales", pattern=r"^(sales|procurement)$", description="合同类型")
    party_a_name: Optional[str] = Field(None, max_length=255, description="甲方名称")
    party_b_name: Optional[str] = Field(None, max_length=255, description="乙方名称")
    amount: Optional[Decimal] = Field(None, description="合同总金额")
    start_date: Optional[date] = Field(None, description="合同开始日期")
    end_date: Optional[date] = Field(None, description="合同到期日期")
    related_contract_id: Optional[str] = Field(None, description="背靠背关联合同ID")
    remark: Optional[str] = Field(None, description="备注")
    project_name: Optional[str] = Field(None, max_length=255, description="所属项目")
    contract_content: Optional[str] = Field(None, description="合同内容")
    delivery_requirements: Optional[str] = Field(None, description="合同交付要求")
    process_records: Optional[str] = Field(None, description="过程记录")
    sort_order: Optional[int] = Field(0, description="排序序号")
    service_lines: Optional[list[ContractServiceLineCreate]] = Field(None, description="服务行列表")


class ComputeServiceContractUpdate(BaseModel):
    customer_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contract_no: Optional[str] = Field(None, max_length=100)
    contract_type: Optional[str] = Field(None, pattern=r"^(sales|procurement)$")
    party_a_name: Optional[str] = Field(None, max_length=255)
    party_b_name: Optional[str] = Field(None, max_length=255)
    amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    related_contract_id: Optional[str] = None
    remark: Optional[str] = None
    project_name: Optional[str] = None
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    sort_order: Optional[int] = None
    service_lines: Optional[list[ContractServiceLineCreate]] = None


class ComputeServiceContractListResponse(BaseModel):
    """列表项（不含完整 service_lines，含 service_lines_count）"""
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    name: str
    contract_no: Optional[str] = None
    contract_type: Optional[str] = None
    party_a_name: Optional[str] = None
    party_b_name: Optional[str] = None
    amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    related_contract_id: Optional[str] = None
    remark: Optional[str] = None
    project_name: Optional[str] = None
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    sort_order: int = 0
    service_lines_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ComputeServiceContractResponse(BaseModel):
    """详情（含完整 service_lines 和 related_contract）"""
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    name: str
    contract_no: Optional[str] = None
    contract_type: Optional[str] = None
    party_a_name: Optional[str] = None
    party_b_name: Optional[str] = None
    amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    related_contract_id: Optional[str] = None
    remark: Optional[str] = None
    project_name: Optional[str] = None
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    sort_order: int = 0
    service_lines: list[ContractServiceLineResponse] = []
    related_contract: Optional[RelatedContractBrief] = None
    amount_auto_calc: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ComputeServiceContractListWrap(BaseModel):
    items: list[ComputeServiceContractListResponse]
    total: int
    page: int = 1
    page_size: int = 20
