"""
算力服务合同模块 API 路由
"""
import urllib.parse
from typing import Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.export_excel import create_excel_response
from src.compute_service import schemas, services
from src.customer.services import get_customer

compute_service_router = APIRouter(
    prefix="/api/compute-service-contracts",
    tags=["Compute Service Contract"],
)


# ============================================================
# 辅助函数
# ============================================================

def _build_detail_response(contract, db: Session) -> schemas.ComputeServiceContractResponse:
    """构建合同详情响应（含 service_lines + related_contract + amount_auto_calc）"""
    # service_lines
    slines = contract.service_lines if contract.service_lines is not None else []
    service_line_responses = [
        schemas.ContractServiceLineResponse(
            id=sl.id,
            contract_id=sl.contract_id,
            category=sl.category,
            item_name=sl.item_name,
            specification=sl.specification,
            vcpu_count=sl.vcpu_count,
            memory_gb=sl.memory_gb,
            storage_gb=sl.storage_gb,
            unit=sl.unit,
            quantity=sl.quantity,
            period_months=sl.period_months,
            unit_price=sl.unit_price,
            total_price=sl.total_price,
            manual_total_price=None,
            sort_order=sl.sort_order,
            created_at=sl.created_at,
        )
        for sl in slines
    ]

    # amount_auto_calc
    amount_auto_calc = services._calc_auto_amount(db, contract.id)

    # related_contract 双向查询
    related = services._find_related_contract(db, contract)
    related_brief = None
    if related:
        related_brief = schemas.RelatedContractBrief(
            id=related.id,
            name=related.name,
            contract_no=related.contract_no,
            contract_type=related.contract_type,
        )

    return schemas.ComputeServiceContractResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        contract_type=contract.contract_type,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        amount=contract.amount,
        start_date=contract.start_date,
        end_date=contract.end_date,
        related_contract_id=contract.related_contract_id,
        remark=contract.remark,
        project_name=contract.project_name,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        sort_order=contract.sort_order,
        service_lines=service_line_responses,
        related_contract=related_brief,
        amount_auto_calc=amount_auto_calc,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


def _build_list_item(contract) -> schemas.ComputeServiceContractListResponse:
    """构建列表项"""
    slines = contract.service_lines if contract.service_lines is not None else []
    return schemas.ComputeServiceContractListResponse(
        id=contract.id,
        customer_id=contract.customer_id,
        customer_name=contract.customer.name if contract.customer else None,
        name=contract.name,
        contract_no=contract.contract_no,
        contract_type=contract.contract_type,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        amount=contract.amount,
        start_date=contract.start_date,
        end_date=contract.end_date,
        related_contract_id=contract.related_contract_id,
        remark=contract.remark,
        project_name=contract.project_name,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        sort_order=contract.sort_order,
        service_lines_count=len(slines),
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


# ============================================================
# 合同 CRUD
# ============================================================

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
    result = [_build_list_item(c) for c in items]
    return schemas.ComputeServiceContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


CONTRACT_TYPE_MAP = {"sales": "销售", "procurement": "采购"}


@compute_service_router.get("/export")
def export_contracts(
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出算力服务合同列表为 Excel"""
    items, _ = services.list_contracts(
        db, customer_id=customer_id, search=search,
        page=1, page_size=999999,
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
            "算力服务",
            c.name or "",
            CONTRACT_TYPE_MAP.get(c.contract_type, c.contract_type or ""),
            c.project_name or "",
            c.party_a_name or "",
            c.party_b_name or "",
            str(c.start_date) if c.start_date else "",
            str(c.end_date) if c.end_date else "",
            str(c.amount) if c.amount else "",
            c.contract_no or "",
            c.contract_content or "",
            c.delivery_requirements or "",
            c.process_records or "",
        ])

    today_str = date_type.today().strftime("%Y-%m-%d")
    excel_bytes = create_excel_response(
        f"算力服务_合同列表_{today_str}", headers, rows,
    )

    encoded_filename = urllib.parse.quote(f"算力服务_合同列表_{today_str}.xlsx")
    return StreamingResponse(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
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
    # 校验 related_contract_id
    if data.related_contract_id:
        related = services.get_contract(db, data.related_contract_id)
        if not related:
            raise HTTPException(status_code=404, detail="关联合同不存在")
    contract = services.create_contract(db, data)
    return _build_detail_response(contract, db)


@compute_service_router.get("/{contract_id}", response_model=schemas.ComputeServiceContractResponse)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """获取算力服务合同详情"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return _build_detail_response(contract, db)


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
    if data.related_contract_id:
        related = services.get_contract(db, data.related_contract_id)
        if not related:
            raise HTTPException(status_code=404, detail="关联合同不存在")
    contract = services.update_contract(db, contract, data)
    return _build_detail_response(contract, db)


@compute_service_router.delete("/{contract_id}", response_model=dict)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """删除算力服务合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    services.delete_contract(db, contract)
    return {"detail": "合同已删除"}


# ============================================================
# Service Lines 子路由
# ============================================================

@compute_service_router.get(
    "/{contract_id}/service-lines",
    response_model=list[schemas.ContractServiceLineResponse],
)
def list_service_lines(contract_id: str, db: Session = Depends(get_db)):
    """获取合同的服务行列表"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    lines = services.list_service_lines(db, contract_id)
    return [
        schemas.ContractServiceLineResponse(
            id=sl.id,
            contract_id=sl.contract_id,
            category=sl.category,
            item_name=sl.item_name,
            specification=sl.specification,
            vcpu_count=sl.vcpu_count,
            memory_gb=sl.memory_gb,
            storage_gb=sl.storage_gb,
            unit=sl.unit,
            quantity=sl.quantity,
            period_months=sl.period_months,
            unit_price=sl.unit_price,
            total_price=sl.total_price,
            manual_total_price=None,
            sort_order=sl.sort_order,
            created_at=sl.created_at,
        )
        for sl in lines
    ]


@compute_service_router.post(
    "/{contract_id}/service-lines",
    response_model=schemas.ContractServiceLineResponse,
    status_code=201,
)
def create_service_line(
    contract_id: str,
    data: schemas.ContractServiceLineCreate,
    db: Session = Depends(get_db),
):
    """新增服务行"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    line = services.create_service_line(db, contract_id, data)
    return schemas.ContractServiceLineResponse(
        id=line.id,
        contract_id=line.contract_id,
        category=line.category,
        item_name=line.item_name,
        specification=line.specification,
        vcpu_count=line.vcpu_count,
        memory_gb=line.memory_gb,
        storage_gb=line.storage_gb,
        unit=line.unit,
        quantity=line.quantity,
        period_months=line.period_months,
        unit_price=line.unit_price,
        total_price=line.total_price,
        manual_total_price=None,
        sort_order=line.sort_order,
        created_at=line.created_at,
    )


@compute_service_router.put(
    "/{contract_id}/service-lines/{line_id}",
    response_model=schemas.ContractServiceLineResponse,
)
def update_service_line(
    contract_id: str,
    line_id: str,
    data: schemas.ContractServiceLineUpdate,
    db: Session = Depends(get_db),
):
    """更新服务行"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    line = services.get_service_line(db, line_id)
    if not line or line.contract_id != contract_id:
        raise HTTPException(status_code=404, detail="服务行不存在")
    line = services.update_service_line(db, line, data)
    return schemas.ContractServiceLineResponse(
        id=line.id,
        contract_id=line.contract_id,
        category=line.category,
        item_name=line.item_name,
        specification=line.specification,
        vcpu_count=line.vcpu_count,
        memory_gb=line.memory_gb,
        storage_gb=line.storage_gb,
        unit=line.unit,
        quantity=line.quantity,
        period_months=line.period_months,
        unit_price=line.unit_price,
        total_price=line.total_price,
        manual_total_price=None,
        sort_order=line.sort_order,
        created_at=line.created_at,
    )


@compute_service_router.delete(
    "/{contract_id}/service-lines/{line_id}",
    response_model=dict,
)
def delete_service_line(
    contract_id: str,
    line_id: str,
    db: Session = Depends(get_db),
):
    """删除服务行"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    line = services.get_service_line(db, line_id)
    if not line or line.contract_id != contract_id:
        raise HTTPException(status_code=404, detail="服务行不存在")
    services.delete_service_line(db, line)
    return {"detail": "服务行已删除"}


@compute_service_router.post(
    "/{contract_id}/service-lines/batch",
    response_model=list[schemas.ContractServiceLineResponse],
    status_code=201,
)
def batch_save_service_lines(
    contract_id: str,
    data: schemas.ContractServiceLineBatchSave,
    db: Session = Depends(get_db),
):
    """批量保存服务行（全量替换）"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    lines = services.batch_save_service_lines(db, contract_id, data.lines)
    return [
        schemas.ContractServiceLineResponse(
            id=sl.id,
            contract_id=sl.contract_id,
            category=sl.category,
            item_name=sl.item_name,
            specification=sl.specification,
            vcpu_count=sl.vcpu_count,
            memory_gb=sl.memory_gb,
            storage_gb=sl.storage_gb,
            unit=sl.unit,
            quantity=sl.quantity,
            period_months=sl.period_months,
            unit_price=sl.unit_price,
            total_price=sl.total_price,
            manual_total_price=None,
            sort_order=sl.sort_order,
            created_at=sl.created_at,
        )
        for sl in lines
    ]
