"""
卫星数据合同模块 API 路由
"""
import urllib.parse
from typing import Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.export_excel import create_excel_response
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
            contract_type=c.contract_type,
            project_name=c.project_name,
            party_a_name=c.party_a_name,
            party_b_name=c.party_b_name,
            start_date=c.start_date,
            end_date=c.end_date,
            amount=c.amount,
            contract_content=c.contract_content,
            delivery_requirements=c.delivery_requirements,
            process_records=c.process_records,
            sort_order=c.sort_order,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return schemas.SatelliteDataContractListWrap(
        items=result, total=total, page=page, page_size=page_size,
    )


@satellite_router.get("/export")
def export_contracts(
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出卫星数据合同列表为 Excel"""
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
            "卫星数据",
            c.name or "",
            c.contract_type or "",
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
        f"卫星数据_合同列表_{today_str}", headers, rows,
    )

    encoded_filename = urllib.parse.quote(f"卫星数据_合同列表_{today_str}.xlsx")
    return StreamingResponse(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
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
        contract_type=contract.contract_type,
        project_name=contract.project_name,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        start_date=contract.start_date,
        end_date=contract.end_date,
        amount=contract.amount,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        sort_order=contract.sort_order,
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
        contract_type=contract.contract_type,
        project_name=contract.project_name,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        start_date=contract.start_date,
        end_date=contract.end_date,
        amount=contract.amount,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        sort_order=contract.sort_order,
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
        contract_type=contract.contract_type,
        project_name=contract.project_name,
        party_a_name=contract.party_a_name,
        party_b_name=contract.party_b_name,
        start_date=contract.start_date,
        end_date=contract.end_date,
        amount=contract.amount,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        sort_order=contract.sort_order,
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
