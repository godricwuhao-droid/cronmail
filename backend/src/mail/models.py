"""
邮件发送日志模块数据模型
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now
from src.customer.models import generate_uuid


class EmailLog(Base):
    """邮件发送日志表"""

    __tablename__ = "email_log"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    rental_id = Column(
        UUIDColumn(),
        ForeignKey("rental_record.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联租赁记录ID",
    )
    template_id = Column(
        UUIDColumn(),
        ForeignKey("email_template.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联模板ID",
    )
    trigger_type = Column(String(32), nullable=True, comment="触发类型")
    recipient = Column(String(256), nullable=False, comment="收件人邮箱")
    recipient_type = Column(String(4), nullable=True, comment="收件人类型: to / cc")
    subject = Column(String(512), nullable=True, comment="邮件主题")
    body = Column(Text, nullable=True, comment="邮件正文")
    status = Column(String(16), default="sent", comment="状态: sent / failed")
    error_msg = Column(Text, nullable=True, comment="错误信息")
    sent_at = Column(DateTime, nullable=True, comment="发送时间")
    created_at = Column(DateTime, default=local_now, nullable=False)
    extra_data = Column(JSON, nullable=True, comment="关联信息: rental_ids, to_emails, cc_emails")

    # 关联（使用字符串延迟引用避免循环导入）
    rental_record = relationship(
        "src.rental.models.RentalRecord",
        back_populates="email_logs",
    )
    template = relationship(
        "src.template.models.EmailTemplate",
        back_populates="email_logs",
    )

    def __repr__(self):
        return f"<EmailLog(id={self.id}, recipient={self.recipient}, status={self.status})>"
