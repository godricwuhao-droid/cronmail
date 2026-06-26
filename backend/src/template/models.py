"""
邮件模板模块数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now
from src.customer.models import generate_uuid


class EmailTemplate(Base):
    """邮件模板表"""

    __tablename__ = "email_template"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False, comment="模板名称")
    trigger_type = Column(
        String(32),
        nullable=False,
        comment="触发类型: provision / expiry_warning / reclaim",
    )
    subject_tpl = Column(Text, nullable=False, comment="邮件主题模板(Jinja2)")
    body_html = Column(Text, nullable=False, comment="邮件正文模板(Jinja2, HTML)")
    variables_desc = Column(JSON, nullable=True, comment="模板变量说明")
    signature_html = Column(Text, nullable=True, comment="邮件签名（HTML，含内嵌图片）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    version = Column(Integer, default=1, comment="版本号")
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        nullable=False,
    )

    # 关联（使用字符串延迟引用避免循环导入）
    email_logs = relationship(
        "src.mail.models.EmailLog",
        back_populates="template",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name={self.name}, trigger={self.trigger_type})>"
