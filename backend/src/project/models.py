"""
项目管理合同 ORM 模型
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Numeric, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.core.database import Base, UUIDColumn
from src.core.timezone import local_now


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ProjectType(Base):
    __tablename__ = "project_type"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True, comment="项目类型名称")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, default=local_now, comment="创建时间")
    updated_at = Column(DateTime, default=local_now, onupdate=local_now, comment="更新时间")

    def __repr__(self):
        return f"<ProjectType(id={self.id}, name={self.name})>"


class ProjectContract(Base):
    __tablename__ = "project_contract"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    company_code = Column(String(20), nullable=False, index=True, comment="公司: fengyun/tianshu/qianxing")
    name = Column(String(255), nullable=False, comment="合同名称")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    contract_type = Column(String(30), nullable=False, default="sales", comment="sales/procurement")
    party_a_name = Column(String(255), nullable=True, comment="甲方")
    party_b_name = Column(String(255), nullable=True, comment="乙方")
    amount = Column(Numeric(12, 2), nullable=True, comment="合同金额")
    start_date = Column(Date, nullable=True, comment="开始日期")
    end_date = Column(Date, nullable=True, comment="结束日期")
    related_contract_id = Column(
        UUIDColumn(),
        ForeignKey("project_contract.id"),
        nullable=True,
        comment="背靠背关联",
    )
    project_name = Column(String(255), nullable=True, comment="所属项目")
    project_type = Column(String(100), nullable=True, comment="项目类型，如算力服务合同，用户手动填写")
    contract_content = Column(Text, nullable=True, comment="合同内容")
    delivery_requirements = Column(Text, nullable=True, comment="交付要求")
    process_records = Column(Text, nullable=True, comment="过程记录")
    raw_tables_json = Column(Text, nullable=True, comment="原始表格JSON，AI解析结果")
    remark = Column(Text, nullable=True, comment="备注")
    responsible_person = Column(String(100), nullable=True, comment="负责人，手动填写")
    business_person = Column(String(100), nullable=True, comment="商务，手动填写")
    party_a_contact = Column(String(255), nullable=True, comment="甲方委派人及联系方式，Agent提取")
    party_b_contact = Column(String(255), nullable=True, comment="乙方委派人及联系方式，Agent提取")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序序号")
    created_at = Column(DateTime, default=local_now)
    updated_at = Column(DateTime, default=local_now, onupdate=local_now)

    service_lines = relationship(
        "ProjectServiceLine",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ProjectServiceLine.sort_order",
    )
    related_contract = relationship(
        "ProjectContract",
        remote_side=[id],
        foreign_keys=[related_contract_id],
    )

    def __repr__(self):
        return (
            f"<ProjectContract(id={self.id}, name={self.name}, "
            f"company_code={self.company_code})>"
        )


class ProjectServiceLine(Base):
    __tablename__ = "project_service_line"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    contract_id = Column(
        UUIDColumn(),
        ForeignKey("project_contract.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    specification = Column(JSON, nullable=True)
    unit = Column(String(20), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    period_months = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    sort_order = Column(Integer, default=0)
    service_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=local_now)

    contract = relationship("ProjectContract", back_populates="service_lines")

    def __repr__(self):
        return (
            f"<ProjectServiceLine(id={self.id}, category={self.category}, "
            f"item_name={self.item_name}, contract_id={self.contract_id})>"
        )


class ProjectContractPayment(Base):
    __tablename__ = "project_contract_payment"

    id = Column(UUIDColumn(), primary_key=True, default=generate_uuid)
    contract_id = Column(
        UUIDColumn(),
        ForeignKey("project_contract.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="关联合同ID"
    )
    amount = Column(Numeric(14, 2), nullable=False, comment="本次回款金额")
    payment_date = Column(Date, nullable=True, comment="回款日期")
    receipt_file_id = Column(String(36), nullable=True, comment="回执单附件ID（attachment表）")
    invoice_file_id = Column(String(36), nullable=True, comment="开票附件ID（attachment表）")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=local_now, comment="创建时间")
    updated_at = Column(DateTime, default=local_now, onupdate=local_now, comment="更新时间")

    contract = relationship("ProjectContract", backref="payments")

    def __repr__(self):
        return (
            f"<ProjectContractPayment(id={self.id}, contract_id={self.contract_id}, "
            f"amount={self.amount})>"
        )
