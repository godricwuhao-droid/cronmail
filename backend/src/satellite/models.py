"""
卫星数据合同模块 ORM 模型
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Numeric, Integer, ForeignKey
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
    # ADR-013: 新增 10 个字段
    contract_type = Column(String(30), nullable=True, comment="合同子类型")
    project_name = Column(String(255), nullable=True, comment="所属项目")
    party_a_name = Column(String(255), nullable=True, comment="甲方名称")
    party_b_name = Column(String(255), nullable=True, comment="乙方名称")
    start_date = Column(Date, nullable=True, comment="服务开始日期")
    end_date = Column(Date, nullable=True, comment="服务结束日期")
    amount = Column(Numeric(12, 2), nullable=True, comment="合同金额")
    contract_content = Column(Text, nullable=True, comment="合同内容")
    delivery_requirements = Column(Text, nullable=True, comment="合同交付要求")
    process_records = Column(Text, nullable=True, comment="过程记录")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序序号")
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
