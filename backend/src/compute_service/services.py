"""
算力服务合同模块业务逻辑层
"""
from typing import Optional
from sqlalchemy.orm import Session

from src.compute_service.models import ComputeServiceContract
from src.compute_service.schemas import ComputeServiceContractCreate, ComputeServiceContractUpdate


def list_contracts(
    db: Session,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ComputeServiceContract], int]:
    """查询算力服务合同列表"""
    query = db.query(ComputeServiceContract)
    if customer_id:
        query = query.filter(ComputeServiceContract.customer_id == customer_id)
    if search:
        query = query.filter(ComputeServiceContract.name.ilike(f"%{search}%"))

    total = query.count()
    items = (
        query.order_by(ComputeServiceContract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_contract(db: Session, contract_id: str) -> Optional[ComputeServiceContract]:
    return (
        db.query(ComputeServiceContract)
        .filter(ComputeServiceContract.id == contract_id)
        .first()
    )


def create_contract(db: Session, data: ComputeServiceContractCreate) -> ComputeServiceContract:
    contract = ComputeServiceContract(
        customer_id=data.customer_id,
        name=data.name,
        contract_no=data.contract_no,
        remark=data.remark,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def update_contract(
    db: Session, contract: ComputeServiceContract, data: ComputeServiceContractUpdate,
) -> ComputeServiceContract:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    db.commit()
    db.refresh(contract)
    return contract


def delete_contract(db: Session, contract: ComputeServiceContract):
    db.delete(contract)
    db.commit()
