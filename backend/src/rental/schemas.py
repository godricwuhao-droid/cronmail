"""
租赁记录模块 Pydantic 请求/响应 Schema
"""
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# 辅助 Schema
# ============================================================


class RentalContactCreate(BaseModel):
    """创建租赁记录时的联系人关联"""
    contact_id: str = Field(..., description="联系人ID")
    recipient_type: str = Field(default="to", pattern="^(to|cc)$", description="收件人类型: to / cc")


class RentalContactResponse(BaseModel):
    """租赁记录关联的联系人响应"""
    contact_id: str
    name: str
    email: str
    recipient_type: str


# ============================================================
# 客户简要信息（嵌套在租赁记录中）
# ============================================================

class CustomerBrief(BaseModel):
    """客户简要信息"""
    id: str
    name: str

    model_config = {"from_attributes": True}


# ============================================================
# EmailLog 简要信息（嵌套在租赁记录详情中）
# ============================================================

class EmailLogBrief(BaseModel):
    """邮件日志简要信息"""
    id: str
    trigger_type: Optional[str] = None
    recipient: str
    recipient_type: Optional[str] = None
    subject: Optional[str] = None
    status: str
    error_msg: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# RentalRecord Schemas
# ============================================================

class RentalRecordCreate(BaseModel):
    """创建租赁记录请求（纯硬件档案，客户/日期/计费从关联合同继承）"""
    machine_model: Optional[str] = Field(None, min_length=1, max_length=128, description="机器型号")
    cpu_model: Optional[str] = Field(None, max_length=256)
    memory_gb: Optional[int] = Field(None, ge=0)
    gpu_info: Optional[str] = None
    system_disk: Optional[str] = Field(None, max_length=256)
    data_disks: Optional[list[str]] = None
    os_version: Optional[str] = Field(None, max_length=128)
    bandwidth_mbps: Optional[int] = Field(None, ge=0)
    rack_location: Optional[str] = Field(None, max_length=256)
    private_ip: Optional[str] = Field(None, max_length=64)
    public_ips: Optional[list[str]] = None
    ssh_port: int = 22
    root_username: Optional[str] = Field(None, max_length=64)
    root_password: Optional[str] = Field(None, description="root 密码（明文传入，后端加密存储）")
    remark: Optional[str] = None

    @field_validator("machine_model", "cpu_model", "gpu_info", "os_version", "rack_location", "private_ip", "root_username", "remark")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class RentalRecordUpdate(BaseModel):
    """更新租赁记录请求（纯硬件档案，客户/日期/计费从关联合同继承；设备状态人工可修改）"""
    machine_model: Optional[str] = Field(None, min_length=1, max_length=128)
    cpu_model: Optional[str] = Field(None, max_length=256)
    memory_gb: Optional[int] = Field(None, ge=0)
    gpu_info: Optional[str] = None
    system_disk: Optional[str] = Field(None, max_length=256)
    data_disks: Optional[list[str]] = None
    os_version: Optional[str] = Field(None, max_length=128)
    bandwidth_mbps: Optional[int] = Field(None, ge=0)
    rack_location: Optional[str] = Field(None, max_length=256)
    private_ip: Optional[str] = Field(None, max_length=64)
    public_ips: Optional[list[str]] = None
    ssh_port: Optional[int] = None
    root_username: Optional[str] = Field(None, max_length=64)
    root_password: Optional[str] = Field(None, description="root 密码（明文传入，后端加密存储）")
    remark: Optional[str] = None
    status: Optional[str] = Field(None, description="设备物理状态（人工可修改）: 空闲中 / 已断电 / 租赁中")

    @field_validator("machine_model", "cpu_model", "gpu_info", "os_version", "rack_location", "private_ip", "root_username", "remark")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class RentalRecordListResponse(BaseModel):
    """租赁记录列表响应（含所有业务字段，不含密码、联系人列表、邮件日志）"""
    id: str
    contract_id: Optional[str] = None  # 已关联的合同ID（如有）
    customer: Optional[CustomerBrief] = None
    machine_model: str
    cpu_model: Optional[str] = None
    memory_gb: Optional[int] = None
    gpu_info: Optional[str] = None
    system_disk: Optional[str] = None
    data_disks: Optional[list[str]] = None
    os_version: Optional[str] = None
    bandwidth_mbps: Optional[int] = None
    rack_location: Optional[str] = None
    private_ip: Optional[str] = None
    public_ips: Optional[list[str]] = None
    ssh_port: int = 22
    root_username: Optional[str] = None
    billing_model: str = "monthly"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auto_renew: bool = False
    remark: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RentalRecordDetailResponse(BaseModel):
    """租赁记录详情响应（含解密密码、客户、联系人、邮件日志、合同信息）"""
    id: str
    customer: Optional[CustomerBrief] = None
    contacts: list[RentalContactResponse] = []
    contract_info: Optional[dict] = None
    machine_model: str
    cpu_model: Optional[str] = None
    memory_gb: Optional[int] = None
    gpu_info: Optional[str] = None
    system_disk: Optional[str] = None
    data_disks: Optional[list[str]] = None
    os_version: Optional[str] = None
    bandwidth_mbps: Optional[int] = None
    rack_location: Optional[str] = None
    private_ip: Optional[str] = None
    public_ips: Optional[list[str]] = None
    ssh_port: int = 22
    root_username: Optional[str] = None
    root_password: Optional[str] = Field(None, description="解密后的明文密码")
    billing_model: str = "monthly"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auto_renew: bool = False
    remark: Optional[str] = None
    status: str = "空闲中"
    email_logs: list[EmailLogBrief] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RentalRecordListWrap(BaseModel):
    """租赁记录列表包装响应"""
    items: list[RentalRecordListResponse]
    total: int
    page: int = 1
    page_size: int = 20


class SendEmailRequest(BaseModel):
    """发送邮件请求"""
    template_id: Optional[str] = Field(None, description="指定模板ID（不传则用默认模板）")


class SendEmailResponse(BaseModel):
    """发送邮件响应"""
    email_log_ids: list[str] = []
    recipient_count: int = 0
    message: Optional[str] = None


class ReclaimResponse(BaseModel):
    """回收响应"""
    success: bool
    message: str
    email_log_ids: list[str] = []
    recipient_count: int = 0
