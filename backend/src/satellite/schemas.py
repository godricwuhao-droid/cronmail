"""
卫星数据合同模块 Pydantic Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SatelliteDataContractCreate(BaseModel):
    customer_id: str = Field(..., description="客户ID")
    name: str = Field(..., min_length=1, max_length=255, description="合同名称")
    contract_no: Optional[str] = Field(None, max_length=100, description="合同编号")
    remark: Optional[str] = Field(None, description="备注")


class SatelliteDataContractUpdate(BaseModel):
    customer_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contract_no: Optional[str] = Field(None, max_length=100)
    remark: Optional[str] = None


class SatelliteDataContractResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    name: str
    contract_no: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SatelliteDataContractListWrap(BaseModel):
    items: list[SatelliteDataContractResponse]
    total: int
    page: int = 1
    page_size: int = 20
