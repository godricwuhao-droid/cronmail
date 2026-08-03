"""
合同模块 API 路由
"""
import urllib.parse
from typing import Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.export_excel import create_excel_response
from src.contract import schemas, services
from src.contract.models import Contract, ChangeLog
from src.customer.services import get_customer

contract_router = APIRouter(prefix="/api/contracts", tags=["Contract"])


def _build_renewal_chain(db: Session, contract: Contract) -> list[dict]:
    """构建续期链路：从原始合同到最新续期"""
    chain = []
    # 1. 反向追溯：找到原始合同
    current = contract
    visited = {current.id}
    while current.renewed_from_id:
        if current.renewed_from_id in visited:
            break
        prev = db.query(Contract).filter(Contract.id == current.renewed_from_id).first()
        if not prev:
            break
        visited.add(prev.id)
        current = prev
    # current 现在是原始合同
    # 2. 正向遍历：从原始合同到所有续期
    seq = 0
    node = current
    visited_forward = set()
    while node:
        if node.id in visited_forward:
            break
        visited_forward.add(node.id)
        chain.append({
            "id": node.id,
            "name": node.name,
            "status": node.status,
            "start_date": str(node.start_date) if node.start_date else None,
            "end_date": str(node.end_date) if node.end_date else None,
            "is_current": node.id == contract.id,
            "renewal_seq": seq,
        })
        seq += 1
        # 查找下一个续期
        next_contract = db.query(Contract).filter(
            Contract.renewed_from_id == node.id
        ).first()
        node = next_contract
    return chain


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
    # 批量查询 has_renewal
    renewed_ids = [c.id for c in items]
    from sqlalchemy import func
    has_renewal_map = {}
    if renewed_ids:
        rows = db.query(
            Contract.renewed_from_id,
            func.count(Contract.id)
        ).filter(
            Contract.renewed_from_id.in_(renewed_ids)
        ).group_by(Contract.renewed_from_id).all()
        has_renewal_map = {row[0]: row[1] > 0 for row in rows}

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
            amount=c.amount,
            rental_count=live_count if live_count > 0 else history_count,
            contact_count=len(c.contacts) if c.contacts else 0,
            renewed_from_id=c.renewed_from_id,
            renewal_seq=0,  # 列表不查全链，性能考虑
            has_renewal=has_renewal_map.get(c.id, False),
            sort_order=c.sort_order,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return schemas.ContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


@contract_router.post("", response_model=schemas.ContractDetailResponse, status_code=201)
def create_contract(data: schemas.ContractCreate, db: Session = Depends(get_db)):
    """创建合同，可同时关联设备和联系人；支持续期"""
    customer = get_customer(db, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if data.renewed_from_id:
        original = services.get_contract(db, data.renewed_from_id)
        if not original:
            raise HTTPException(status_code=404, detail="续期来源合同不存在")
        existing_renewal = db.query(Contract).filter(
            Contract.renewed_from_id == data.renewed_from_id
        ).first()
        if existing_renewal:
            raise HTTPException(status_code=409, detail="该合同已被续期")
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


@contract_router.get("/dashboard/overview-stats", response_model=dict)
def overview_stats(db: Session = Depends(get_db)):
    """获取运营概览图表的统计数据"""
    from src.contract.dashboard import get_overview_stats
    return get_overview_stats(db)


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


BILLING_MODEL_MAP = {"monthly": "月付", "quarterly": "季付", "yearly": "年付"}


@contract_router.get("/export")
def export_contracts(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出算力租赁合同列表为 Excel"""
    items, _ = services.list_contracts(
        db, customer_id=customer_id, status=status, search=search,
        page=1, page_size=999999,  # 全量
    )

    headers = [
        "序号", "所属类型", "合同名称", "合同类型", "所属项目",
        "甲方", "乙方", "服务开始", "服务结束", "合同金额（元）",
        "合同编号", "合同内容", "合同交付要求", "过程记录",
    ]

    rows = []
    for idx, c in enumerate(items, 1):
        rows.append([
            idx,
            "算力租赁",
            c.name or "",
            BILLING_MODEL_MAP.get(c.billing_model, c.billing_model or ""),
            "",  # 所属项目 - 暂无
            "",  # 甲方 - 暂无
            "",  # 乙方 - 暂无
            str(c.start_date) if c.start_date else "",
            str(c.end_date) if c.end_date else "",
            str(c.amount) if c.amount else "",
            c.contract_no or "",
            "",  # 合同内容 - 暂无
            "",  # 合同交付要求 - 暂无
            "",  # 过程记录 - 暂无
        ])

    today_str = date_type.today().strftime("%Y-%m-%d")
    excel_bytes = create_excel_response(
        f"算力租赁_合同列表_{today_str}", headers, rows,
    )

    encoded_filename = urllib.parse.quote(f"算力租赁_合同列表_{today_str}.xlsx")
    return StreamingResponse(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )


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
    if contract.status == 'reclaimed':
        raise HTTPException(status_code=422, detail="已回收的合同不允许修改")
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
    try:
        # 获取设备列表（已兼容回收后从历史快照反查）
        rentals = services.get_contract_rentals(db, contract.id)

        # rental_count: 优先实时关联，若已清理则用历史快照
        live_count = len(rentals) if rentals else 0
        history_count = len(contract.history_rental_ids) if contract.history_rental_ids else 0
        rental_count = max(live_count, history_count)

        customer_name = contract.customer.name if contract.customer else None
        contact_count = len(contract.contacts) if contract.contacts else 0
        contacts = services.get_contract_contacts(db, contract.id)

        # 续期链路
        renewal_chain = _build_renewal_chain(db, contract)
        current_in_chain = next((c for c in renewal_chain if c["is_current"]), {})
        has_renewal = db.query(Contract).filter(
            Contract.renewed_from_id == contract.id
        ).count() > 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取合同详情失败: {e}")

    return schemas.ContractDetailResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=customer_name,
        name=contract.name,
        contract_no=contract.contract_no,
        start_date=contract.start_date,
        end_date=contract.end_date,
        billing_model=contract.billing_model,
        status=contract.status,
        remark=contract.remark,
        amount=contract.amount,
        rental_count=rental_count,
        contact_count=contact_count,
        renewed_from_id=contract.renewed_from_id,
        renewal_seq=current_in_chain.get("renewal_seq", 0),
        has_renewal=has_renewal,
        sort_order=contract.sort_order,
        renewal_chain=renewal_chain,
        rentals=rentals,
        contacts=contacts,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )
