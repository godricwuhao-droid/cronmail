"""
合同模块 Pydantic Schema
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class ContractContactPayload(BaseModel):
    contact_id: str
    recipient_type: str = "to"  # to / cc


class ContractCreate(BaseModel):
    customer_id: str = Field(..., description="客户ID")
    name: str = Field(..., min_length=1, max_length=255, description="合同名称")
    contract_no: Optional[str] = Field(None, max_length=100, description="合同编号")
    start_date: date = Field(..., description="合同开始日期")
    end_date: date = Field(..., description="合同到期日期")
    billing_model: str = Field("monthly", description="计费方式: monthly/quarterly/yearly")
    remark: Optional[str] = Field(None, description="备注")
    # 创建时可选的设备 ID 列表和联系人列表
    rental_ids: Optional[list[str]] = Field(None, description="关联设备ID列表")
    contacts: Optional[list[ContractContactPayload]] = Field(None, description="关联联系人列表")


class ContractUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contract_no: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    billing_model: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    contacts: Optional[list[ContractContactPayload]] = None


class ContractResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    name: str
    contract_no: Optional[str] = None
    start_date: date
    end_date: date
    billing_model: str
    status: str
    remark: Optional[str] = None
    rental_count: int = 0
    contact_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContractDetailResponse(ContractResponse):
    rentals: list[dict] = []    # 关联设备简要列表
    contacts: list[dict] = []   # 关联联系人列表


class ContractListWrap(BaseModel):
    items: list[ContractResponse]
    total: int
    page: int = 1
    page_size: int = 20


class LinkRentalRequest(BaseModel):
    rental_ids: list[str] = Field(..., min_length=1, description="要关联的设备ID列表")


class UnlinkRentalRequest(BaseModel):
    rental_ids: list[str] = Field(..., min_length=1, description="要取消关联的设备ID列表")
