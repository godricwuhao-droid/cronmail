"""
卫星数据合同模块业务逻辑层
"""
from typing import Optional
from sqlalchemy.orm import Session

from src.satellite.models import SatelliteDataContract
from src.satellite.schemas import SatelliteDataContractCreate, SatelliteDataContractUpdate


def list_contracts(
    db: Session,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SatelliteDataContract], int]:
    """查询卫星数据合同列表"""
    query = db.query(SatelliteDataContract)
    if customer_id:
        query = query.filter(SatelliteDataContract.customer_id == customer_id)
    if search:
        query = query.filter(SatelliteDataContract.name.ilike(f"%{search}%"))

    total = query.count()
    items = (
        query.order_by(SatelliteDataContract.sort_order.asc(), SatelliteDataContract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_contract(db: Session, contract_id: str) -> Optional[SatelliteDataContract]:
    return (
        db.query(SatelliteDataContract)
        .filter(SatelliteDataContract.id == contract_id)
        .first()
    )


def create_contract(db: Session, data: SatelliteDataContractCreate) -> SatelliteDataContract:
    contract = SatelliteDataContract(
        customer_id=data.customer_id,
        name=data.name,
        contract_no=data.contract_no,
        remark=data.remark,
        # ADR-013: 新增 10 个字段
        contract_type=data.contract_type,
        project_name=data.project_name,
        party_a_name=data.party_a_name,
        party_b_name=data.party_b_name,
        start_date=data.start_date,
        end_date=data.end_date,
        amount=data.amount,
        contract_content=data.contract_content,
        delivery_requirements=data.delivery_requirements,
        process_records=data.process_records,
        sort_order=data.sort_order if data.sort_order else 0,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def update_contract(
    db: Session, contract: SatelliteDataContract, data: SatelliteDataContractUpdate,
) -> SatelliteDataContract:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    db.commit()
    db.refresh(contract)
    return contract


def delete_contract(db: Session, contract: SatelliteDataContract):
    db.delete(contract)
    db.commit()
