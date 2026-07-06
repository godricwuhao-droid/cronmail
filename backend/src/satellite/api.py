"""
卫星数据合同模块 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.satellite import schemas, services
from src.customer.services import get_customer

satellite_router = APIRouter(
    prefix="/api/satellite-data-contracts",
    tags=["Satellite Data Contract"],
)


@satellite_router.get("", response_model=schemas.SatelliteDataContractListWrap)
def list_contracts(
    customer_id: Optional[str] = Query(None, description="客户ID"),
    search: Optional[str] = Query(None, description="按合同名称模糊搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取卫星数据合同列表"""
    items, total = services.list_contracts(
        db, customer_id=customer_id, search=search,
        page=page, page_size=page_size,
    )
    result = []
    for c in items:
        result.append(schemas.SatelliteDataContractResponse(
            id=c.id,
            customer_id=c.customer_id,
            customer_name=c.customer.name if c.customer else None,
            name=c.name,
            contract_no=c.contract_no,
            remark=c.remark,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return schemas.SatelliteDataContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


@satellite_router.post("", response_model=schemas.SatelliteDataContractResponse, status_code=201)
def create_contract(
    data: schemas.SatelliteDataContractCreate,
    db: Session = Depends(get_db),
):
    """创建卫星数据合同"""
    customer = get_customer(db, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    contract = services.create_contract(db, data)
    return schemas.SatelliteDataContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=customer.name,
        name=contract.name,
        contract_no=contract.contract_no,
        remark=contract.remark,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@satellite_router.get("/{contract_id}", response_model=schemas.SatelliteDataContractResponse)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """获取卫星数据合同详情"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return schemas.SatelliteDataContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        remark=contract.remark,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@satellite_router.put("/{contract_id}", response_model=schemas.SatelliteDataContractResponse)
def update_contract(
    contract_id: str,
    data: schemas.SatelliteDataContractUpdate,
    db: Session = Depends(get_db),
):
    """更新卫星数据合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if data.customer_id:
        customer = get_customer(db, data.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
    contract = services.update_contract(db, contract, data)
    return schemas.SatelliteDataContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        remark=contract.remark,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@satellite_router.delete("/{contract_id}", response_model=dict)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """删除卫星数据合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    services.delete_contract(db, contract)
    return {"detail": "合同已删除"}
