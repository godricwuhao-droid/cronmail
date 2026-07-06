"""
算力服务合同模块 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.compute_service import schemas, services
from src.customer.services import get_customer

compute_service_router = APIRouter(
    prefix="/api/compute-service-contracts",
    tags=["Compute Service Contract"],
)


@compute_service_router.get("", response_model=schemas.ComputeServiceContractListWrap)
def list_contracts(
    customer_id: Optional[str] = Query(None, description="客户ID"),
    search: Optional[str] = Query(None, description="按合同名称模糊搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取算力服务合同列表"""
    items, total = services.list_contracts(
        db, customer_id=customer_id, search=search,
        page=page, page_size=page_size,
    )
    result = []
    for c in items:
        result.append(schemas.ComputeServiceContractResponse(
            id=c.id,
            customer_id=c.customer_id,
            customer_name=c.customer.name if c.customer else None,
            name=c.name,
            contract_no=c.contract_no,
            remark=c.remark,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return schemas.ComputeServiceContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


@compute_service_router.post("", response_model=schemas.ComputeServiceContractResponse, status_code=201)
def create_contract(
    data: schemas.ComputeServiceContractCreate,
    db: Session = Depends(get_db),
):
    """创建算力服务合同"""
    customer = get_customer(db, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    contract = services.create_contract(db, data)
    return schemas.ComputeServiceContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=customer.name,
        name=contract.name,
        contract_no=contract.contract_no,
        remark=contract.remark,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@compute_service_router.get("/{contract_id}", response_model=schemas.ComputeServiceContractResponse)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """获取算力服务合同详情"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return schemas.ComputeServiceContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        remark=contract.remark,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@compute_service_router.put("/{contract_id}", response_model=schemas.ComputeServiceContractResponse)
def update_contract(
    contract_id: str,
    data: schemas.ComputeServiceContractUpdate,
    db: Session = Depends(get_db),
):
    """更新算力服务合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if data.customer_id:
        customer = get_customer(db, data.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
    contract = services.update_contract(db, contract, data)
    return schemas.ComputeServiceContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        remark=contract.remark,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@compute_service_router.delete("/{contract_id}", response_model=dict)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """删除算力服务合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    services.delete_contract(db, contract)
    return {"detail": "合同已删除"}
