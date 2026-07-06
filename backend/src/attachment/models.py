"""
附件管理模块 ORM 模型

AttachmentCategory  - 附件分类（按合同类型 + 分类 code）
AttachmentItem     - 分类下的子项清单
Attachment         - 实际文件（多态关联三张合同表）
AttachmentStatus   - 子项完成确认状态
"""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AttachmentCategory(Base):
    """附件分类"""
    __tablename__ = "attachment_category"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    contract_type = Column(
        String(30), nullable=False,
        comment="合同类型: compute_leasing / satellite_data / compute_service",
    )
    name = Column(String(100), nullable=False, comment="分类名称")
    code = Column(String(50), nullable=False, comment="分类编码")
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=local_now, comment="创建时间")

    # 关联子项
    items = relationship(
        "AttachmentItem",
        back_populates="category",
        lazy="selectin",
        order_by="AttachmentItem.sort_order",
    )

    def __repr__(self):
        return (
            f"<AttachmentCategory(id={self.id}, name={self.name}, "
            f"code={self.code}, contract_type={self.contract_type})>"
        )


class AttachmentItem(Base):
    """分类下的子项清单"""
    __tablename__ = "attachment_item"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    category_id = Column(
        UUIDColumn(),
        ForeignKey("attachment_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属分类ID",
    )
    name = Column(String(100), nullable=False, comment="子项名称")
    description = Column(Text, nullable=True, comment="子项说明")
    expected_type = Column(
        String(20), default="any",
        comment="期望文件类型: pdf / excel / image / any",
    )
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=local_now, comment="创建时间")

    # 关联
    category = relationship("AttachmentCategory", back_populates="items")
    attachments = relationship(
        "Attachment",
        back_populates="item",
        lazy="selectin",
    )

    def __repr__(self):
        return (
            f"<AttachmentItem(id={self.id}, name={self.name}, "
            f"category_id={self.category_id})>"
        )


class Attachment(Base):
    """实际文件（多态关联三张合同表）"""
    __tablename__ = "attachment"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    contract_type = Column(
        String(30), nullable=False,
        comment="关联哪种合同表: compute_leasing / satellite_data / compute_service",
    )
    contract_id = Column(
        String(36), nullable=False, index=True,
        comment="关联合同的 ID",
    )
    item_id = Column(
        UUIDColumn(),
        ForeignKey("attachment_item.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属子项ID",
    )
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(
        String(500), nullable=False,
        comment="相对路径: {contract_type}/{contract_id}/{item_id}/{uuid}.ext",
    )
    file_size = Column(Integer, default=0, comment="文件大小(字节)")
    mime_type = Column(String(100), nullable=True, comment="MIME 类型")
    uploaded_at = Column(DateTime, default=local_now, comment="上传时间")

    # 关联
    item = relationship("AttachmentItem", back_populates="attachments")

    def __repr__(self):
        return (
            f"<Attachment(id={self.id}, filename={self.filename}, "
            f"contract_type={self.contract_type}, contract_id={self.contract_id})>"
        )


class AttachmentStatus(Base):
    """子项完成确认状态"""
    __tablename__ = "attachment_status"
    __table_args__ = (
        UniqueConstraint(
            "contract_type", "contract_id", "item_id",
            name="uq_attachment_status",
        ),
    )

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    contract_type = Column(
        String(30), nullable=False,
        comment="合同类型",
    )
    contract_id = Column(
        String(36), nullable=False,
        comment="合同 ID",
    )
    item_id = Column(
        UUIDColumn(),
        ForeignKey("attachment_item.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="子项ID",
    )
    file_count = Column(Integer, default=0, comment="文件数量")
    confirmed = Column(Boolean, default=False, comment="是否已确认完成")
    confirmed_at = Column(DateTime, nullable=True, comment="确认时间")
    created_at = Column(DateTime, default=local_now, comment="创建时间")

    def __repr__(self):
        return (
            f"<AttachmentStatus(contract_type={self.contract_type}, "
            f"contract_id={self.contract_id}, item_id={self.item_id}, "
            f"confirmed={self.confirmed})>"
        )
