"""
合同模块 ORM 模型
"""
import uuid
from sqlalchemy import Column, String, Date, Text, DateTime, ForeignKey, Numeric, UniqueConstraint, Table, JSON, Integer
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now


CONTRACT_STATUS_ENUM = ('active', 'expiring', 'expired', 'reclaimed')
BILLING_MODEL_ENUM = ('monthly', 'quarterly', 'yearly')


# contract_rental 中间表
contract_rental = Table(
    "contract_rental",
    Base.metadata,
    Column(
        "contract_id",
        UUIDColumn(),
        ForeignKey("contract.id", ondelete="CASCADE"),
        primary_key=True,
        comment="合同ID",
    ),
    Column(
        "rental_id",
        UUIDColumn(),
        ForeignKey("rental_record.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True,
        comment="租赁记录ID（唯一，一个设备只能关联一个合同）",
    ),
    Column(
        "created_at",
        DateTime,
        default=local_now,
        comment="创建时间",
    ),
    UniqueConstraint("contract_id", "rental_id", name="uq_contract_rental"),
    comment="合同-租赁记录关联中间表",
)


# contract_contact 中间表
contract_contact = Table(
    "contract_contact",
    Base.metadata,
    Column(
        "contract_id",
        UUIDColumn(),
        ForeignKey("contract.id", ondelete="CASCADE"),
        primary_key=True,
        comment="合同ID",
    ),
    Column(
        "contact_id",
        UUIDColumn(),
        ForeignKey("contact.id", ondelete="CASCADE"),
        primary_key=True,
        comment="联系人ID",
    ),
    Column(
        "recipient_type",
        String(10),
        nullable=False,
        primary_key=True,
        default="to",
        comment="收件人类型: to / cc",
    ),
    UniqueConstraint("contract_id", "contact_id", "recipient_type", name="uq_contract_contact"),
    comment="合同-联系人关联中间表",
)


class ChangeLog(Base):
    __tablename__ = 'change_log'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_type = Column(String(20), nullable=False, comment='contract / rental')
    target_id = Column(String(36), nullable=False, index=True)
    content = Column(Text, nullable=False, comment='变更内容（人工输入）')
    created_at = Column(DateTime, default=local_now)


class Contract(Base):
    __tablename__ = "contract"

    id = Column(UUIDColumn(), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(
        UUIDColumn(),
        ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="客户ID",
    )
    name = Column(String(255), nullable=False, comment="合同名称")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    start_date = Column(Date, nullable=False, comment="合同开始日期")
    end_date = Column(Date, nullable=False, comment="合同到期日期")
    billing_model = Column(
        String(20),
        nullable=False,
        default="monthly",
        comment="计费方式: monthly / quarterly / yearly",
    )
    status = Column(
        String(20),
        nullable=False,
        default="active",
        comment="状态: active / expiring / expired / reclaimed",
    )
    remark = Column(Text, nullable=True, comment="备注")
    amount = Column(Numeric(12, 2), nullable=True, comment="合同金额")
    history_rental_ids = Column(JSON, nullable=True, comment="回收时快照的设备ID列表，方便复盘")
    renewed_from_id = Column(
        UUIDColumn(),
        ForeignKey("contract.id"),
        nullable=True,
        index=True,
        comment="续期来源合同ID，NULL 表示非续期合同",
    )
    sort_order = Column(Integer, default=0, nullable=False, comment="排序序号")
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        nullable=False,
    )

    # 关联
    customer = relationship(
        "src.customer.models.Customer",
        backref="contracts",
    )
    rentals = relationship(
        "src.rental.models.RentalRecord",
        secondary=contract_rental,
        backref="contracts",
    )
    contacts = relationship(
        "src.customer.models.Contact",
        secondary=contract_contact,
        backref="contracts",
    )
    renewed_from = relationship(
        "Contract",
        remote_side="Contract.id",
        foreign_keys=[renewed_from_id],
        backref="renewals",
    )

    def __repr__(self):
        return (
            f"<Contract(id={self.id}, name={self.name}, "
            f"customer_id={self.customer_id}, status={self.status})>"
        )
