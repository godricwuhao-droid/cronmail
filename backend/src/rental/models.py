"""
租赁模块数据模型
"""
from datetime import date
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Date,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Table,
    JSON,
)
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now
from src.customer.models import generate_uuid


# rental_contact 中间表
rental_contact = Table(
    "rental_contact",
    Base.metadata,
    Column(
        "rental_id",
        UUIDColumn(),
        ForeignKey("rental_record.id", ondelete="CASCADE"),
        primary_key=True,
        comment="租赁记录ID",
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
        String(4),
        nullable=False,
        default="to",
        comment="收件人类型: to / cc",
    ),
    UniqueConstraint("rental_id", "contact_id", name="uq_rental_contact"),
    comment="租赁记录-联系人关联中间表",
)


class RentalRecord(Base):
    """租赁记录表"""

    __tablename__ = "rental_record"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    customer_id = Column(
        UUIDColumn(),
        ForeignKey("customer.id", ondelete="RESTRICT"),
        nullable=True,
        comment="客户ID（关联合同后自动设置）",
    )

    # 硬件信息
    machine_model = Column(String(128), nullable=False, comment="机器型号")
    cpu_model = Column(String(256), nullable=True, comment="CPU 型号")
    memory_gb = Column(Integer, nullable=True, comment="内存(GB)")
    gpu_info = Column(Text, nullable=True, comment="GPU 信息")
    system_disk = Column(String(256), nullable=True, comment="系统盘，如 480GB SATA SSD")
    data_disks = Column(JSON, nullable=True, comment="数据盘列表，每项为字符串如 '1000GB NVMe SSD'")

    # 系统信息
    os_version = Column(String(128), nullable=True, comment="操作系统版本")
    bandwidth_mbps = Column(Integer, nullable=True, comment="带宽(Mbps)")

    # 网络/位置
    rack_location = Column(String(256), nullable=True, comment="机架位置")
    private_ip = Column(String(64), nullable=True, comment="内网IP")
    public_ips = Column(JSON, nullable=True, comment="公网IP列表(JSON)")
    ssh_port = Column(Integer, default=22, comment="SSH 端口")

    # 凭证
    root_username = Column(String(64), nullable=True, comment="root 用户名")
    root_password_enc = Column(Text, nullable=True, comment="root 密码(加密)")

    # 计费/期限
    billing_model = Column(
        String(32),
        default="monthly",
        comment="计费模式: monthly / yearly — DEPRECATED: 请从关联 Contract 获取",
    )
    start_date = Column(Date, nullable=True, comment="租赁开始日期")
    end_date = Column(
        Date,
        nullable=True,
        comment="租赁结束日期 — DEPRECATED: 请从关联 Contract 获取",
    )
    auto_renew = Column(Boolean, default=False, comment="是否自动续期")

    # 状态
    status = Column(
        String(32),
        default="空闲中",
        comment="状态: 空闲中 / 已断电 / 租赁中",
    )

    # 备注
    remark = Column(Text, nullable=True, comment="备注")

    # 时间戳
    created_at = Column(DateTime, default=local_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        nullable=False,
    )

    # 关联（使用字符串延迟引用避免循环导入）
    customer = relationship(
        "src.customer.models.Customer",
        back_populates="rental_records",
    )
    contacts = relationship(
        "src.customer.models.Contact",
        secondary=rental_contact,
        back_populates="rental_records",
        lazy="dynamic",
    )
    email_logs = relationship(
        "src.mail.models.EmailLog",
        back_populates="rental_record",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<RentalRecord(id={self.id}, model={self.machine_model}, status={self.status})>"


class RentalContact:
    """
    RentalContact 辅助类
    用于访问 rental_contact 中间表的额外字段 (recipient_type)
    通过 association proxy 或直接操作 rental_contact 表使用
    """
    pass
