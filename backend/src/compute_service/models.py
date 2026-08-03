"""
算力服务合同模块 ORM 模型
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Numeric, Date, JSON
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ContractServiceLine(Base):
    """算力服务合同 - 服务内容行"""
    __tablename__ = "contract_service_line"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    contract_id = Column(
        UUIDColumn(),
        ForeignKey("compute_service_contract.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="合同ID",
    )
    category = Column(String(50), nullable=False, comment="服务大类")
    item_name = Column(String(100), nullable=False, comment="服务项")
    specification = Column(JSON, nullable=True, comment="异构规格，仅展示")
    vcpu_count = Column(Numeric(10, 2), nullable=True, comment="vCPU核数，用于聚合")
    memory_gb = Column(Numeric(10, 2), nullable=True, comment="内存GB，用于聚合")
    storage_gb = Column(Numeric(10, 2), nullable=True, comment="存储GB，用于聚合")
    unit = Column(String(20), nullable=False, comment="单位")
    quantity = Column(Numeric(12, 2), nullable=False, comment="数量")
    period_months = Column(Integer, nullable=False, default=1, comment="周期月数")
    unit_price = Column(Numeric(12, 2), nullable=False, comment="单价")
    total_price = Column(Numeric(12, 2), nullable=False, comment="总价 = quantity × period_months × unit_price")
    sort_order = Column(Integer, default=0, comment="排序")
    service_description = Column(Text, nullable=True, comment="服务描述长文本")
    gpu_count = Column(Integer, nullable=True, comment="每台GPU卡数")
    gpu_model = Column(String(100), nullable=True, comment="GPU型号")
    gpu_memory_gb = Column(Numeric(10, 2), nullable=True, comment="单卡显存GB")
    gpu_tops = Column(Numeric(10, 2), nullable=True, comment="单卡算力TOPS")
    created_at = Column(DateTime, default=local_now, comment="创建时间")

    # 关联
    contract = relationship(
        "ComputeServiceContract",
        back_populates="service_lines",
    )

    def __repr__(self):
        return (
            f"<ContractServiceLine(id={self.id}, category={self.category}, "
            f"item_name={self.item_name}, contract_id={self.contract_id})>"
        )


class ComputeServiceContract(Base):
    """算力服务合同"""
    __tablename__ = "compute_service_contract"

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
    contract_type = Column(
        String(30),
        nullable=False,
        default="sales",
        comment="合同类型: sales(销售) | procurement(采购)",
    )
    party_a_name = Column(String(255), nullable=True, comment="甲方名称")
    party_b_name = Column(String(255), nullable=True, comment="乙方名称")
    amount = Column(Numeric(12, 2), nullable=True, comment="合同总金额")
    start_date = Column(Date, nullable=True, comment="合同开始日期")
    end_date = Column(Date, nullable=True, comment="合同到期日期")
    related_contract_id = Column(
        UUIDColumn(),
        ForeignKey("compute_service_contract.id"),
        nullable=True,
        comment="背靠背关联合同ID",
    )
    remark = Column(Text, nullable=True, comment="备注")
    project_name = Column(String(255), nullable=True, comment="所属项目")
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
        backref="compute_service_contracts",
    )
    service_lines = relationship(
        "ContractServiceLine",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractServiceLine.sort_order",
    )
    related_contract = relationship(
        "ComputeServiceContract",
        remote_side=[id],
        foreign_keys=[related_contract_id],
    )

    def __repr__(self):
        return (
            f"<ComputeServiceContract(id={self.id}, name={self.name}, "
            f"customer_id={self.customer_id})>"
        )
