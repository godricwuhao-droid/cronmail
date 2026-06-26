"""
系统配置模块 Pydantic 请求/响应 Schema
"""
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class SmtpConfigResponse(BaseModel):
    """SMTP 配置响应（不含密码）"""
    host: str
    port: int
    username: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    encryption: str = "tls"

    model_config = {"from_attributes": True}


class SmtpConfigUpdate(BaseModel):
    """更新 SMTP 配置请求"""
    host: str = Field(..., min_length=1, max_length=256, description="SMTP 服务器地址")
    port: int = Field(..., ge=1, le=65535, description="SMTP 端口")
    username: Optional[str] = Field(None, max_length=256)
    password: Optional[str] = Field(None, max_length=256, description="SMTP 密码（明文传入，后端加密存储）")
    sender_name: Optional[str] = Field(None, max_length=128)
    sender_email: Optional[str] = Field(None, max_length=256)
    encryption: str = Field("tls", description="加密方式: tls | starttls | none")

    @field_validator("encryption")
    @classmethod
    def validate_encryption(cls, v: str) -> str:
        if v not in ("tls", "starttls", "none"):
            raise ValueError("encryption 必须是 tls、starttls 或 none")
        return v

    @field_validator("host", "username", "sender_name", "sender_email")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class SmtpTestRequest(BaseModel):
    """SMTP 测试请求"""
    test_email: str = Field(..., min_length=1, max_length=256, description="测试邮件接收地址")

    @field_validator("test_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class SmtpTestResponse(BaseModel):
    """SMTP 测试响应"""
    success: bool
    message: str


# ============================================================
# 钉钉机器人配置 Schema
# ============================================================

class DingTalkConfigResponse(BaseModel):
    """钉钉配置响应（secret 脱敏显示 ***）"""
    id: str
    webhook_url: str
    secret: str = ""  # 脱敏后显示 "***" 或空字符串
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class DingTalkConfigUpdate(BaseModel):
    """更新钉钉配置请求"""
    webhook_url: str = Field(..., min_length=1, max_length=512, description="钉钉机器人 Webhook URL")
    secret: Optional[str] = Field(None, max_length=128, description="加签密钥（传 '***' 表示保留原值，传 '' 表示清空）")
    is_active: Optional[bool] = Field(None, description="是否启用")

    @field_validator("webhook_url")
    @classmethod
    def strip_webhook_url(cls, v: str) -> str:
        return v.strip()

    @field_validator("secret")
    @classmethod
    def strip_secret(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class DingTalkTestRequest(BaseModel):
    """钉钉测试请求"""
    webhook_url: Optional[str] = Field(None, max_length=512, description="Webhook URL（不传则用已保存配置）")
    secret: Optional[str] = Field(None, max_length=128, description="加签密钥（不传则用已保存配置）")

    @field_validator("webhook_url")
    @classmethod
    def strip_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v

    @field_validator("secret")
    @classmethod
    def strip_secret(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


class DingTalkTestResponse(BaseModel):
    """钉钉测试响应"""
    success: bool
    message: str
