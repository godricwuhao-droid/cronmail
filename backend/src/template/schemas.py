"""
邮件模板模块 Pydantic 请求/响应 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# EmailTemplate Schemas
# ============================================================

class EmailTemplateCreate(BaseModel):
    """创建邮件模板请求"""
    name: str = Field(..., min_length=1, max_length=128, description="模板名称")
    trigger_type: str = Field(
        ...,
        min_length=1,
        max_length=32,
        pattern="^(provision|expiry_warning|expiry_notice|reclaim)$",
        description="触发类型: provision / expiry_warning / expiry_notice / reclaim",
    )
    subject_tpl: str = Field(..., min_length=1, description="邮件主题模板(Jinja2)")
    body_html: str = Field(..., min_length=1, description="邮件正文模板(Jinja2, HTML)")
    variables_desc: Optional[dict] = Field(None, description="模板变量说明")
    signature_html: Optional[str] = Field(None, description="邮件签名（HTML）")
    is_active: bool = True

    @field_validator("name", "subject_tpl", "body_html")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if v is not None:
            return v.strip()
        return v


class EmailTemplateUpdate(BaseModel):
    """更新邮件模板请求（更新时 version 自动 +1）"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    trigger_type: Optional[str] = Field(
        None,
        min_length=1,
        max_length=32,
        pattern="^(provision|expiry_warning|expiry_notice|reclaim)$",
    )
    subject_tpl: Optional[str] = Field(None, min_length=1)
    body_html: Optional[str] = Field(None, min_length=1)
    variables_desc: Optional[dict] = None
    signature_html: Optional[str] = Field(None, description="邮件签名（HTML）")
    is_active: Optional[bool] = None

    @field_validator("name", "subject_tpl", "body_html")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class EmailTemplateResponse(BaseModel):
    """邮件模板响应"""
    id: str
    name: str
    trigger_type: str
    subject_tpl: str
    body_html: str
    variables_desc: Optional[dict] = None
    signature_html: Optional[str] = None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmailTemplateListResponse(BaseModel):
    """邮件模板列表响应"""
    items: list[EmailTemplateResponse]
    total: int
    page: int = 1
    page_size: int = 20


class TemplatePreviewRequest(BaseModel):
    """模板预览请求"""
    subject_tpl: str = Field(..., min_length=1, description="邮件主题模板")
    body_html: str = Field(..., min_length=1, description="邮件正文模板")
    sample_data: dict = Field(..., description="示例数据，用于渲染模板变量")
    signature_html: Optional[str] = Field(None, description="邮件签名（HTML），预览时拼接在正文末尾")


class TemplatePreviewResponse(BaseModel):
    """模板预览响应"""
    subject_rendered: str
    body_rendered: str


class TemplateTestSendRequest(BaseModel):
    """测试发送请求"""
    to_contact_ids: list[str] = Field(..., min_length=1, description="收件人 contact id 列表")
    cc_contact_ids: list[str] = Field(default_factory=list, description="抄送 contact id 列表")
    sample_data: Optional[dict] = Field(None, description="不传则用模板默认示例数据")


class TemplateTestSendResponse(BaseModel):
    """测试发送响应"""
    success: bool
    message: str
    to_emails: list[str] = []
    cc_emails: list[str] = []
    subject_rendered: str = ""
