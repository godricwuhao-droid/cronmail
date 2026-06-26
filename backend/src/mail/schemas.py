"""
邮件日志模块 Pydantic 请求/响应 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmailLogResponse(BaseModel):
    """邮件日志响应（列表用，不含 body）"""
    id: str
    rental_id: Optional[str] = None
    template_id: Optional[str] = None
    trigger_type: Optional[str] = None
    recipient: str
    recipient_type: Optional[str] = None
    subject: Optional[str] = None
    status: str
    error_msg: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    extra_data: Optional[dict] = None

    model_config = {"from_attributes": True}


class EmailLogDetailResponse(EmailLogResponse):
    """邮件日志详情响应（含 body）"""
    body: Optional[str] = None

    model_config = {"from_attributes": True}


class EmailLogListResponse(BaseModel):
    """邮件日志列表响应"""
    items: list[EmailLogResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ResendResponse(BaseModel):
    """重发响应"""
    success: bool
    message: str
    email_log_id: Optional[str] = None
