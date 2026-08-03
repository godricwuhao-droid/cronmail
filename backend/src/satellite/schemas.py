"""
卫星数据合同模块 Pydantic Schema
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class SatelliteDataContractCreate(BaseModel):
    customer_id: str = Field(..., description="客户ID")
    name: str = Field(..., min_length=1, max_length=255, description="合同名称")
    contract_no: Optional[str] = Field(None, max_length=100, description="合同编号")
    remark: Optional[str] = Field(None, description="备注")
    # ADR-013: 新增 10 个 Optional 字段
    contract_type: Optional[str] = Field(None, max_length=30, description="合同子类型")
    project_name: Optional[str] = Field(None, max_length=255, description="所属项目")
    party_a_name: Optional[str] = Field(None, max_length=255, description="甲方名称")
    party_b_name: Optional[str] = Field(None, max_length=255, description="乙方名称")
    start_date: Optional[date] = Field(None, description="服务开始日期")
    end_date: Optional[date] = Field(None, description="服务结束日期")
    amount: Optional[Decimal] = Field(None, description="合同金额")
    contract_content: Optional[str] = Field(None, description="合同内容")
    delivery_requirements: Optional[str] = Field(None, description="合同交付要求")
    process_records: Optional[str] = Field(None, description="过程记录")
    sort_order: Optional[int] = Field(0, description="排序序号")


class SatelliteDataContractUpdate(BaseModel):
    customer_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contract_no: Optional[str] = Field(None, max_length=100)
    remark: Optional[str] = None
    # ADR-013: 新增 10 个 Optional 字段
    contract_type: Optional[str] = Field(None, max_length=30, description="合同子类型")
    project_name: Optional[str] = Field(None, max_length=255, description="所属项目")
    party_a_name: Optional[str] = Field(None, max_length=255, description="甲方名称")
    party_b_name: Optional[str] = Field(None, max_length=255, description="乙方名称")
    start_date: Optional[date] = Field(None, description="服务开始日期")
    end_date: Optional[date] = Field(None, description="服务结束日期")
    amount: Optional[Decimal] = Field(None, description="合同金额")
    contract_content: Optional[str] = Field(None, description="合同内容")
    delivery_requirements: Optional[str] = Field(None, description="合同交付要求")
    process_records: Optional[str] = Field(None, description="过程记录")
    sort_order: Optional[int] = None


class SatelliteDataContractResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    name: str
    contract_no: Optional[str] = None
    remark: Optional[str] = None
    # ADR-013: 新增 10 个 Optional 字段
    contract_type: Optional[str] = None
    project_name: Optional[str] = None
    party_a_name: Optional[str] = None
    party_b_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    amount: Optional[Decimal] = None
    contract_content: Optional[str] = None
    delivery_requirements: Optional[str] = None
    process_records: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SatelliteDataContractListWrap(BaseModel):
    items: list[SatelliteDataContractResponse]
    total: int
    page: int = 1
    page_size: int = 20
