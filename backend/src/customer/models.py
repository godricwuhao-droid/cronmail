"""
客户模块数据模型
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class Customer(Base):
    """客户表"""

    __tablename__ = "customer"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False, comment="客户名称")
    code = Column(String(64), unique=True, nullable=False, default=generate_uuid, comment="客户编码（自动生成）")
    status = Column(String(16), default="active", comment="状态: active / inactive")
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(DateTime, default=local_now, onupdate=local_now, nullable=False)

    # 关联（使用字符串延迟引用避免循环导入）
    contacts = relationship("Contact", back_populates="customer", lazy="dynamic")
    rental_records = relationship(
        "src.rental.models.RentalRecord",
        back_populates="customer",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Customer(id={self.id}, name={self.name}, code={self.code})>"


class Contact(Base):
    """联系人表"""

    __tablename__ = "contact"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    customer_id = Column(
        UUIDColumn(),
        ForeignKey("customer.id", ondelete="SET NULL"),
        nullable=True,
        comment="客户ID，NULL 表示内部同事",
    )
    name = Column(String(128), nullable=False, comment="联系人姓名")
    email = Column(String(256), nullable=False, comment="邮箱地址")
    phone = Column(String(32), nullable=True, comment="电话")
    department = Column(String(128), nullable=True, comment="部门")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(DateTime, default=local_now, onupdate=local_now, nullable=False)

    # 关联（使用字符串延迟引用避免循环导入）
    customer = relationship("Customer", back_populates="contacts")
    rental_records = relationship(
        "src.rental.models.RentalRecord",
        secondary="rental_contact",
        back_populates="contacts",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Contact(id={self.id}, name={self.name}, email={self.email})>"
