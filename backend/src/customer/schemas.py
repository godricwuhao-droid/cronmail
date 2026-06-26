"""
客户模块 Pydantic 请求/响应 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Customer Schemas
# ============================================================

class CustomerCreate(BaseModel):
    """创建客户请求"""
    name: str = Field(..., min_length=1, max_length=128, description="客户名称")
    code: str = Field(..., min_length=1, max_length=64, description="客户编码（唯一）")

    @field_validator("name", "code")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class CustomerUpdate(BaseModel):
    """更新客户请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")

    @field_validator("name", "code")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class CustomerResponse(BaseModel):
    """客户响应"""
    id: str
    name: str
    code: str
    status: str
    contact_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    """客户列表响应"""
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# Contact Schemas
# ============================================================

class ContactCreate(BaseModel):
    """创建联系人请求"""
    customer_id: Optional[str] = Field(None, description="客户ID，null 表示内部同事")
    name: str = Field(..., min_length=1, max_length=128, description="联系人姓名")
    email: str = Field(..., min_length=1, max_length=256, description="邮箱地址")
    phone: Optional[str] = Field(None, max_length=32)
    department: Optional[str] = Field(None, max_length=128)

    @field_validator("name", "email", "phone", "department")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class ContactUpdate(BaseModel):
    """更新联系人请求"""
    customer_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    email: Optional[str] = Field(None, min_length=1, max_length=256)
    phone: Optional[str] = Field(None, max_length=32)
    department: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None

    @field_validator("name", "email", "phone", "department")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if "@" not in v:
                raise ValueError("邮箱格式不正确")
        return v


class ContactResponse(BaseModel):
    """联系人响应"""
    id: str
    customer_id: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    """联系人列表响应"""
    items: list[ContactResponse]
    total: int
    page: int = 1
    page_size: int = 20
