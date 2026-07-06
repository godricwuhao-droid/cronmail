"""
附件管理模块 Pydantic Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# AttachmentCategory
# ============================================================

class AttachmentCategoryCreate(BaseModel):
    contract_type: str = Field(..., description="合同类型: compute_leasing/satellite_data/compute_service")
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    code: str = Field(..., min_length=1, max_length=50, description="分类编码")
    sort_order: int = Field(0, description="排序")


class AttachmentCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class AttachmentCategoryReorder(BaseModel):
    sort_order: int = Field(..., description="新排序值")


class AttachmentItemBrief(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    expected_type: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class AttachmentCategoryResponse(BaseModel):
    id: str
    contract_type: str
    name: str
    code: str
    sort_order: int
    is_active: bool
    items: list[AttachmentItemBrief] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttachmentCategoryListWrap(BaseModel):
    items: list[AttachmentCategoryResponse]


# ============================================================
# AttachmentItem
# ============================================================

class AttachmentItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="子项名称")
    description: Optional[str] = Field(None, description="子项说明")
    expected_type: str = Field("any", description="期望文件类型: pdf/excel/image/any")
    sort_order: int = Field(0, description="排序")


class AttachmentItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    expected_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class AttachmentItemReorder(BaseModel):
    sort_order: int = Field(..., description="新排序值")


class AttachmentItemResponse(BaseModel):
    id: str
    category_id: str
    name: str
    description: Optional[str] = None
    expected_type: str
    sort_order: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================================
# Attachment (文件)
# ============================================================

class AttachmentFileBrief(BaseModel):
    id: str
    filename: str
    file_size: int = 0
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttachmentResponse(BaseModel):
    id: str
    contract_type: str
    contract_id: str
    item_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttachmentUploadResponse(BaseModel):
    attachments: list[AttachmentFileBrief]


# ============================================================
# 按合同组织的附件列表
# ============================================================

class CategoryItemFiles(BaseModel):
    item_id: str
    item_name: str
    expected_type: str
    files: list[AttachmentFileBrief] = []
    file_count: int = 0
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None


class CategoryWithItems(BaseModel):
    category_id: str
    category_name: str
    items: list[CategoryItemFiles] = []


class AttachmentListByContractResponse(BaseModel):
    categories: list[CategoryWithItems]


# ============================================================
# AttachmentStatus
# ============================================================

class AttachmentStatusConfirmRequest(BaseModel):
    contract_type: str = Field(..., description="合同类型")
    contract_id: str = Field(..., description="合同 ID")


class AttachmentStatusResponse(BaseModel):
    confirmed: bool


# ============================================================
# 汇总
# ============================================================

class ItemSummaryDetail(BaseModel):
    confirmed: bool = False
    file_count: int = 0


class AttachmentSummaryResponse(BaseModel):
    total_items: int = 0
    confirmed_items: int = 0
    all_confirmed: bool = False
    items: dict[str, ItemSummaryDetail] = {}
