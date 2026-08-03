"""
项目管理合同模块 API 路由
"""
import urllib.parse
from typing import Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.export_excel import create_excel_response
from src.project import schemas, services

project_router = APIRouter(
    prefix="/api/project-contracts",
    tags=["Project Contract"],
)

COMPANY_CODE_MAP = {
    "fengyun": "风云",
    "tianshu": "天枢",
    "qianxing": "千星",
}
CONTRACT_TYPE_MAP = {"sales": "销售", "procurement": "采购"}


# ============================================================
# 辅助函数
# ============================================================

def _build_detail_response(contract, db: Session) -> schemas.ProjectContractResponse:
    """构建合同详情响应（含 service_lines + related_contract + amount_auto_calc）"""
    # service_lines
    slines = contract.service_lines if contract.service_lines is not None else []
    service_line_responses = [
        schemas.ProjectServiceLineResponse(
            id=sl.id,
            contract_id=sl.contract_id,
            category=sl.category,
            item_name=sl.item_name,
            specification=sl.specification,
            unit=sl.unit,
            quantity=sl.quantity,
            period_months=sl.period_months,
            unit_price=sl.unit_price,
            total_price=sl.total_price,
            sort_order=sl.sort_order,
            service_description=sl.service_description,
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
        related_brief = schemas.RelatedProjectContractBrief(
            id=related.id,
            name=related.name,
            contract_no=related.contract_no,
            contract_type=related.contract_type,
        )

    return schemas.ProjectContractResponse(
        id=contract.id,
        company_code=contract.company_code,
        name=contract.name,
        contract_no=contract.contract_no,
        contract_type=contract.contract_type,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        amount=contract.amount,
        start_date=contract.start_date,
        end_date=contract.end_date,
        related_contract_id=contract.related_contract_id,
        project_name=contract.project_name,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        raw_tables_json=contract.raw_tables_json,
        remark=contract.remark,
        sort_order=contract.sort_order,
        service_lines=service_line_responses,
        related_contract=related_brief,
        amount_auto_calc=amount_auto_calc,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


def _build_list_item(contract) -> schemas.ProjectContractListResponse:
    """构建列表项"""
    slines = contract.service_lines if contract.service_lines is not None else []
    return schemas.ProjectContractListResponse(
        id=contract.id,
        company_code=contract.company_code,
        name=contract.name,
        contract_no=contract.contract_no,
        contract_type=contract.contract_type,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        amount=contract.amount,
        start_date=contract.start_date,
        end_date=contract.end_date,
        related_contract_id=contract.related_contract_id,
        project_name=contract.project_name,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        remark=contract.remark,
        sort_order=contract.sort_order,
        service_lines_count=len(slines),
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


# ============================================================
# 合同 CRUD
# ============================================================

@project_router.get("", response_model=schemas.ProjectContractListWrap)
def list_contracts(
    company: Optional[str] = Query(None, alias="company", description="公司代码: fengyun/tianshu/qianxing"),
    search: Optional[str] = Query(None, description="按合同名称/编号模糊搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取项目管理合同列表"""
    items, total = services.list_contracts(
        db, company_code=company, search=search,
        page=page, page_size=page_size,
    )
    result = [_build_list_item(c) for c in items]
    return schemas.ProjectContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


@project_router.get("/export")
def export_contracts(
    company: Optional[str] = Query(None, description="公司代码: fengyun/tianshu/qianxing"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出项目管理合同列表为 Excel"""
    items, _ = services.list_contracts(
        db, company_code=company, search=search,
        page=1, page_size=999999,
    )

    headers = [
        "序号", "所属类型", "合同名称", "合同类型", "所属项目",
        "甲方", "乙方", "服务开始", "服务结束", "合同金额（元）",
        "合同编号", "合同内容", "合同交付要求", "过程记录",
    ]

    rows = []
    for idx, c in enumerate(items, 1):
        company_label = COMPANY_CODE_MAP.get(c.company_code, c.company_code or "")
        rows.append([
            idx,
            company_label,
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
        f"项目管理_合同列表_{today_str}", headers, rows,
    )

    encoded_filename = urllib.parse.quote(f"项目管理_合同列表_{today_str}.xlsx")
    return StreamingResponse(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )


@project_router.post("", response_model=schemas.ProjectContractResponse, status_code=201)
def create_contract(
    data: schemas.ProjectContractCreate,
    db: Session = Depends(get_db),
):
    """创建项目管理合同"""
    # 校验 related_contract_id
    if data.related_contract_id:
        related = services.get_contract(db, data.related_contract_id)
        if not related:
            raise HTTPException(status_code=404, detail="关联合同不存在")
    contract = services.create_contract(db, data)
    return _build_detail_response(contract, db)


@project_router.get("/{contract_id}", response_model=schemas.ProjectContractResponse)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """获取项目管理合同详情"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return _build_detail_response(contract, db)


@project_router.put("/{contract_id}", response_model=schemas.ProjectContractResponse)
def update_contract(
    contract_id: str,
    data: schemas.ProjectContractUpdate,
    db: Session = Depends(get_db),
):
    """更新项目管理合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if data.related_contract_id:
        related = services.get_contract(db, data.related_contract_id)
        if not related:
            raise HTTPException(status_code=404, detail="关联合同不存在")
    contract = services.update_contract(db, contract, data)
    return _build_detail_response(contract, db)


@project_router.delete("/{contract_id}", response_model=dict)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """删除项目管理合同"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    services.delete_contract(db, contract)
    return {"detail": "合同已删除"}


# ============================================================
# Service Lines 子路由
# ============================================================

@project_router.get(
    "/{contract_id}/service-lines",
    response_model=list[schemas.ProjectServiceLineResponse],
)
def list_service_lines(contract_id: str, db: Session = Depends(get_db)):
    """获取合同的服务行列表"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    lines = services.list_service_lines(db, contract_id)
    return [
        schemas.ProjectServiceLineResponse(
            id=sl.id,
            contract_id=sl.contract_id,
            category=sl.category,
            item_name=sl.item_name,
            specification=sl.specification,
            unit=sl.unit,
            quantity=sl.quantity,
            period_months=sl.period_months,
            unit_price=sl.unit_price,
            total_price=sl.total_price,
            sort_order=sl.sort_order,
            service_description=sl.service_description,
            created_at=sl.created_at,
        )
        for sl in lines
    ]


@project_router.post(
    "/{contract_id}/service-lines",
    response_model=schemas.ProjectServiceLineResponse,
    status_code=201,
)
def create_service_line(
    contract_id: str,
    data: schemas.ProjectServiceLineCreate,
    db: Session = Depends(get_db),
):
    """新增服务行"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    line = services.create_service_line(db, contract_id, data)
    return schemas.ProjectServiceLineResponse(
        id=line.id,
        contract_id=line.contract_id,
        category=line.category,
        item_name=line.item_name,
        specification=line.specification,
        unit=line.unit,
        quantity=line.quantity,
        period_months=line.period_months,
        unit_price=line.unit_price,
        total_price=line.total_price,
        sort_order=line.sort_order,
        service_description=line.service_description,
        created_at=line.created_at,
    )


@project_router.put(
    "/{contract_id}/service-lines/{line_id}",
    response_model=schemas.ProjectServiceLineResponse,
)
def update_service_line(
    contract_id: str,
    line_id: str,
    data: schemas.ProjectServiceLineUpdate,
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
    return schemas.ProjectServiceLineResponse(
        id=line.id,
        contract_id=line.contract_id,
        category=line.category,
        item_name=line.item_name,
        specification=line.specification,
        unit=line.unit,
        quantity=line.quantity,
        period_months=line.period_months,
        unit_price=line.unit_price,
        total_price=line.total_price,
        sort_order=line.sort_order,
        service_description=line.service_description,
        created_at=line.created_at,
    )


@project_router.delete(
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


@project_router.post(
    "/{contract_id}/service-lines/batch",
    response_model=list[schemas.ProjectServiceLineResponse],
    status_code=201,
)
def batch_save_service_lines(
    contract_id: str,
    data: schemas.ProjectServiceLineBatchSave,
    db: Session = Depends(get_db),
):
    """批量保存服务行（全量替换）"""
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    lines = services.batch_save_service_lines(db, contract_id, data.lines)
    return [
        schemas.ProjectServiceLineResponse(
            id=sl.id,
            contract_id=sl.contract_id,
            category=sl.category,
            item_name=sl.item_name,
            specification=sl.specification,
            unit=sl.unit,
            quantity=sl.quantity,
            period_months=sl.period_months,
            unit_price=sl.unit_price,
            total_price=sl.total_price,
            sort_order=sl.sort_order,
            service_description=sl.service_description,
            created_at=sl.created_at,
        )
        for sl in lines
    ]
