"""
系统配置模块数据模型
"""
import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now
from src.customer.models import generate_uuid


class SmtpConfig(Base):
    """SMTP 配置表"""

    __tablename__ = "smtp_config"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    host = Column(String(256), nullable=False, comment="SMTP 服务器地址")
    port = Column(Integer, nullable=False, comment="SMTP 端口")
    username = Column(String(256), nullable=True, comment="SMTP 用户名")
    password_enc = Column(Text, nullable=True, comment="SMTP 密码(加密)")
    sender_name = Column(String(128), nullable=True, comment="发件人显示名称")
    sender_email = Column(String(256), nullable=True, comment="发件人邮箱")
    encryption = Column(String(16), default='tls', comment='tls|starttls|none')
    # 保留旧字段兼容（后续迁移后可删除）
    use_tls = Column(Boolean, default=True, comment="[DEPRECATED] 请使用 encryption 字段")
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        nullable=False,
    )

    def __repr__(self):
        return f"<SmtpConfig(id={self.id}, host={self.host}, port={self.port})>"


class DingTalkConfig(Base):
    """钉钉机器人配置表（单条记录模式）"""

    __tablename__ = "dingtalk_config"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    webhook_url = Column(String(512), nullable=False, comment="钉钉机器人 Webhook URL")
    secret = Column(String(128), nullable=True, comment="加签密钥（可选）")
    is_active = Column(Boolean, default=True, comment="是否启用钉钉通知")
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        nullable=False,
    )

    def __repr__(self):
        return f"<DingTalkConfig(id={self.id}, is_active={self.is_active})>"


class SystemConfig(Base):
    """系统配置表（键值对）"""

    __tablename__ = "system_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, comment="配置键")
    value = Column(String(500), nullable=False, comment="配置值")
    description = Column(String(255), nullable=True, comment="配置说明")
    updated_at = Column(DateTime, default=local_now, onupdate=local_now, comment="更新时间")

    def __repr__(self):
        return f"<SystemConfig(key={self.key}, value={self.value})>"
