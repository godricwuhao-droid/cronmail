"""
卫星数据合同模块 ORM 模型
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now


def generate_uuid() -> str:
    return str(uuid.uuid4())


class SatelliteDataContract(Base):
    """卫星数据合同"""
    __tablename__ = "satellite_data_contract"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    customer_id = Column(
        UUIDColumn(),
        ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="客户ID",
    )
    name = Column(String(255), nullable=False, comment="合同名称")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=local_now, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        comment="更新时间",
    )

    # 关联
    customer = relationship(
        "src.customer.models.Customer",
        backref="satellite_data_contracts",
    )

    def __repr__(self):
        return (
            f"<SatelliteDataContract(id={self.id}, name={self.name}, "
            f"customer_id={self.customer_id})>"
        )
