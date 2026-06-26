"""
合同模块 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.contract import schemas, services
from src.contract.models import Contract, ChangeLog
from src.customer.services import get_customer

contract_router = APIRouter(prefix="/api/contracts", tags=["Contract"])


@contract_router.get("", response_model=schemas.ContractListWrap)
def list_contracts(
    customer_id: Optional[str] = Query(None, description="客户ID"),
    status: Optional[str] = Query(None, description="合同状态: active/expiring/expired/reclaimed"),
    search: Optional[str] = Query(None, description="按合同名称模糊搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取合同列表，支持按客户、状态过滤和模糊搜索"""
    items, total = services.list_contracts(
        db, customer_id=customer_id, status=status, search=search,
        page=page, page_size=page_size,
    )
    result = []
    for c in items:
        live_count = len(c.rentals) if c.rentals else 0
        history_count = len(c.history_rental_ids) if c.history_rental_ids else 0
        result.append(schemas.ContractResponse(
            id=c.id,
            customer_id=c.customer_id,
            customer_name=c.customer.name if c.customer else None,
            name=c.name,
            contract_no=c.contract_no,
            start_date=c.start_date,
            end_date=c.end_date,
            billing_model=c.billing_model,
            status=c.status,
            remark=c.remark,
            rental_count=live_count if live_count > 0 else history_count,
            contact_count=len(c.contacts) if c.contacts else 0,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return schemas.ContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


@contract_router.post("", response_model=schemas.ContractDetailResponse, status_code=201)
def create_contract(data: schemas.ContractCreate, db: Session = Depends(get_db)):
    """创建合同，可同时关联设备和联系人"""
    customer = get_customer(db, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    contract = services.create_contract(db, data)
    return _to_detail(contract, db)


# ⚠️ 固定路径路由必须放在 /{contract_id} 之前，否则会被当作 contract_id 匹配

@contract_router.get("/dashboard/stats", response_model=dict)
def dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表盘合同统计（总数、临期数、过期数、临期合同详情）"""
    from src.contract.dashboard import get_dashboard_stats, get_expiring_contracts_with_rentals
    stats = get_dashboard_stats(db)
    expiring = get_expiring_contracts_with_rentals(db)
    stats["expiring_contracts"] = expiring
    return stats


@contract_router.get("/changelog")
def list_change_logs(
    target_type: str = Query(..., description="contract / rental"),
    target_id: str = Query(..., description="目标ID"),
    db: Session = Depends(get_db),
):
    """获取变更记录列表"""
    logs = db.query(ChangeLog).filter(
        ChangeLog.target_type == target_type,
        ChangeLog.target_id == target_id,
    ).order_by(ChangeLog.created_at.desc()).all()
    return [
        {"id": l.id, "content": l.content, "created_at": l.created_at.isoformat()}
        for l in logs
    ]


@contract_router.post("/changelog", status_code=201)
def create_change_log(
    data: dict,
    db: Session = Depends(get_db),
):
    """创建变更记录"""
    log = ChangeLog(
        target_type=data["target_type"],
        target_id=data["target_id"],
        content=data["content"],
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "content": log.content, "created_at": log.created_at.isoformat()}


@contract_router.get("/{contract_id}", response_model=schemas.ContractDetailResponse)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """获取合同详情，含关联设备和联系人"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return _to_detail(contract, db)


@contract_router.put("/{contract_id}", response_model=schemas.ContractDetailResponse)
def update_contract(contract_id: str, data: schemas.ContractUpdate, db: Session = Depends(get_db)):
    """更新合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if contract.status in ('expired', 'reclaimed'):
        raise HTTPException(status_code=422, detail="已过期或已回收的合同不允许修改")
    contract = services.update_contract(db, contract, data)
    return _to_detail(contract, db)


@contract_router.delete("/{contract_id}", response_model=dict)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """删除合同（物理删除，CASCADE 删除关联）"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    services.delete_contract(db, contract)
    return {"detail": "合同已删除"}


@contract_router.post("/{contract_id}/rentals", response_model=dict)
def link_rentals(contract_id: str, data: schemas.LinkRentalRequest, db: Session = Depends(get_db)):
    """关联设备到合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if contract.status in ('expired', 'reclaimed'):
        raise HTTPException(status_code=422, detail="已过期或已回收的合同不允许关联设备")
    services.link_rentals(db, contract_id, data.rental_ids)
    return {"detail": f"已关联 {len(data.rental_ids)} 台设备"}


@contract_router.delete("/{contract_id}/rentals", response_model=dict)
def unlink_rentals(contract_id: str, data: schemas.UnlinkRentalRequest, db: Session = Depends(get_db)):
    """取消关联设备"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if contract.status in ('expired', 'reclaimed'):
        raise HTTPException(status_code=422, detail="已过期或已回收的合同不允许取消关联")
    services.unlink_rentals(db, contract_id, data.rental_ids)
    return {"detail": f"已取消关联 {len(data.rental_ids)} 台设备"}


def _to_detail(contract: Contract, db: Session) -> schemas.ContractDetailResponse:
    """将 Contract ORM 对象转为 ContractDetailResponse"""
    # 获取设备列表（已兼容回收后从历史快照反查）
    rentals = services.get_contract_rentals(db, contract.id)

    # rental_count: 优先实时关联，若已清理则用历史快照
    live_count = len(contract.rentals) if contract.rentals else 0
    history_count = len(contract.history_rental_ids) if contract.history_rental_ids else 0
    rental_count = live_count if live_count > 0 else history_count

    return schemas.ContractDetailResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        start_date=contract.start_date,
        end_date=contract.end_date,
        billing_model=contract.billing_model,
        status=contract.status,
        remark=contract.remark,
        rental_count=rental_count,
        contact_count=len(contract.contacts) if contract.contacts else 0,
        rentals=rentals,
        contacts=services.get_contract_contacts(db, contract.id),
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )
