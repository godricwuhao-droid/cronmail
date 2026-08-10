"""
项目管理合同模块 API 路由
"""
import urllib.parse
from decimal import Decimal
from typing import Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.export_excel import create_excel_response
from src.project import schemas, services

project_router = APIRouter(
    prefix="/api/project-contracts",
    tags=["Project Contract"],
)

project_type_router = APIRouter(
    prefix="/api/project-types",
    tags=["Project Type"],
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
        project_type=contract.project_type,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        raw_tables_json=contract.raw_tables_json,
        remark=contract.remark,
        responsible_person=contract.responsible_person,
        business_person=contract.business_person,
        party_a_contact=contract.party_a_contact,
        party_b_contact=contract.party_b_contact,
        sort_order=contract.sort_order,
        service_lines=service_line_responses,
        related_contract=related_brief,
        amount_auto_calc=amount_auto_calc,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


def _build_list_item(contract, payment_summary: dict | None = None) -> schemas.ProjectContractListResponse:
    """构建列表项"""
    slines = contract.service_lines if contract.service_lines is not None else []
    paid_amount = None
    payment_progress = None
    if payment_summary:
        paid_amount_str = payment_summary.get("total_paid")
        if paid_amount_str:
            from decimal import Decimal
            paid_amount = Decimal(paid_amount_str)
        payment_progress = payment_summary.get("progress")
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
        project_type=contract.project_type,
        contract_content=contract.contract_content,
        delivery_requirements=contract.delivery_requirements,
        process_records=contract.process_records,
        remark=contract.remark,
        responsible_person=contract.responsible_person,
        business_person=contract.business_person,
        party_a_contact=contract.party_a_contact,
        party_b_contact=contract.party_b_contact,
        sort_order=contract.sort_order,
        service_lines_count=len(slines),
        paid_amount=paid_amount,
        payment_progress=payment_progress,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


# ============================================================
# 概览统计（必须在 /{contract_id} 之前注册）
# ============================================================

@project_router.get("/overview", response_model=dict)
def get_overview(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="统计年份，默认当年"),
    db: Session = Depends(get_db),
):
    """获取项目概览统计（按项目类型、服务期内月度分摊）"""
    return services.get_project_overview(db, year=year)


# ============================================================
# 回款记录独立路由（/payments/{payment_id}，必须在 /{contract_id} 之前注册）
# ============================================================

@project_router.put("/payments/{payment_id}", response_model=schemas.PaymentResponse)
def update_payment(payment_id: str, data: schemas.PaymentUpdate, db: Session = Depends(get_db)):
    """更新回款记录"""
    return services.update_payment(db, payment_id, data)


@project_router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(payment_id: str, db: Session = Depends(get_db)):
    """删除回款记录"""
    services.delete_payment(db, payment_id)


# ============================================================
# 合同 CRUD
# ============================================================

@project_router.get("", response_model=schemas.ProjectContractListWrap)
def list_contracts(
    company: Optional[str] = Query(None, alias="company", description="公司代码: fengyun/tianshu/qianxing"),
    search: Optional[str] = Query(None, description="按合同名称/编号模糊搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取项目管理合同列表"""
    items, total = services.list_contracts(
        db, company_code=company, search=search,
        page=page, page_size=page_size,
    )
    # 批量获取回款汇总
    contract_ids = [str(c.id) for c in items]
    payment_summaries = services.get_payment_summary_for_contracts(db, contract_ids)
    result = [_build_list_item(c, payment_summaries.get(str(c.id))) for c in items]
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


# ============================================================
# 回款记录 CRUD（/{contract_id}/payments 系列）
# ============================================================

@project_router.get("/{contract_id}/payments/summary")
def get_payment_summary(contract_id: str, db: Session = Depends(get_db)):
    """获取合同回款汇总：已回款总额 + 进度百分比"""
    return services.get_payment_summary(db, contract_id)


@project_router.get("/{contract_id}/payments", response_model=list[schemas.PaymentResponse])
def list_payments(contract_id: str, db: Session = Depends(get_db)):
    """获取合同的所有回款记录"""
    return services.list_payments(db, contract_id)


@project_router.post("/{contract_id}/payments", response_model=schemas.PaymentResponse, status_code=201)
def create_payment(contract_id: str, data: schemas.PaymentCreate, db: Session = Depends(get_db)):
    """创建回款记录"""
    return services.create_payment(db, contract_id, data)


def _extract_amount_and_date(fields: dict) -> tuple:
    """从 parse_payment_receipt 返回的 dict 中提取 (Decimal amount, date payment_date)"""
    from datetime import datetime as dt_datetime

    extracted_amount = None
    extracted_date = None

    if isinstance(fields, dict):
        amount_str = fields.get("amount")
        if amount_str and str(amount_str).strip():
            try:
                extracted_amount = Decimal(str(amount_str).strip())
            except Exception:
                pass

        date_str = fields.get("payment_date") or fields.get("start_date") or fields.get("end_date")
        if date_str and str(date_str).strip():
            try:
                extracted_date = dt_datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
            except Exception:
                pass

    return extracted_amount, extracted_date


def _amounts_match(a: Decimal, b: Decimal) -> bool:
    """判断两个金额是否匹配：误差 ≤ 1% 或 ≤ 100 元"""
    if a == b:
        return True
    diff = abs(a - b)
    threshold_pct = a * Decimal("0.01")  # 1% of receipt amount
    threshold = max(threshold_pct, Decimal("100.00"))
    return diff <= threshold


def _ensure_payment_attachment_items(db: Session, project_type: str) -> tuple:
    """确保回款凭证附件分类和子项存在，返回 (receipt_item_id, invoice_item_id)"""
    from src.attachment.models import AttachmentItem, AttachmentCategory

    category = db.query(AttachmentCategory).filter(
        AttachmentCategory.contract_type == "project",
        AttachmentCategory.code == "payment_receipt",
        AttachmentCategory.project_type == project_type,
        AttachmentCategory.is_active == True,
    ).first()
    if not category:
        category = AttachmentCategory(
            contract_type="project",
            project_type=project_type,
            name="回款凭证",
            code="payment_receipt",
            sort_order=4,
        )
        db.add(category)
        db.flush()

    receipt_item = db.query(AttachmentItem).filter(
        AttachmentItem.category_id == category.id,
        AttachmentItem.name == "回执单",
        AttachmentItem.is_active == True,
    ).first()
    if not receipt_item:
        receipt_item = AttachmentItem(
            category_id=category.id,
            name="回执单",
            description="回款回执单扫描件",
            expected_type="any",
            sort_order=1,
        )
        db.add(receipt_item)
        db.flush()

    invoice_item = db.query(AttachmentItem).filter(
        AttachmentItem.category_id == category.id,
        AttachmentItem.name == "电子发票",
        AttachmentItem.is_active == True,
    ).first()
    if not invoice_item:
        invoice_item = AttachmentItem(
            category_id=category.id,
            name="电子发票",
            description="电子发票文件",
            expected_type="any",
            sort_order=2,
        )
        db.add(invoice_item)
        db.flush()

    return str(receipt_item.id), str(invoice_item.id)


@project_router.post("/{contract_id}/payments/parse")
async def parse_payment_receipt(
    contract_id: str,
    receipt: UploadFile = File(...),
    invoice: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    """AI 解析回执单/发票并创建回款记录（双文件金额匹配）

    上传回执单文件（必填）和电子发票文件（可选），调用 Vision 管道提取金额和日期，
    两个文件都解析后进行金额匹配：
    - 匹配成功（误差 ≤ 1% 或 ≤ 100 元）→ 自动创建回款记录，取回执单金额为准
    - 匹配失败 → 返回两个金额，由前端弹窗让用户确认
    - 仅一个文件 → 直接用该金额自动创建回款
    """
    import asyncio
    from src.contract_parser.services import parse_payment_receipt as do_parse
    from io import BytesIO
    from src.attachment.services import save_file

    # 验证合同存在
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 验证文件大小
    receipt_content = await receipt.read()
    if len(receipt_content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="回执单文件大小超过 50MB 限制")

    invoice_content = None
    invoice_filename = None
    if invoice:
        invoice_content = await invoice.read()
        invoice_filename = invoice.filename or "unknown"

    receipt_filename = receipt.filename or "unknown"

    loop = asyncio.get_event_loop()

    # ---- 解析回执单 ----
    try:
        receipt_parse_result = await loop.run_in_executor(None, do_parse, receipt_content, receipt_filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    receipt_amount, receipt_date = _extract_amount_and_date(receipt_parse_result)

    # ---- 解析发票（如果有） ----
    invoice_amount = None
    invoice_date = None
    if invoice_content and invoice_filename:
        try:
            invoice_parse_result = await loop.run_in_executor(None, do_parse, invoice_content, invoice_filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"发票解析失败: {e}")
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"发票解析失败: {e}")
        invoice_amount, invoice_date = _extract_amount_and_date(invoice_parse_result)

    # ---- 确保附件分类存在 ----
    receipt_item_id, invoice_item_id = _ensure_payment_attachment_items(db, contract.project_type)

    # ---- 保存回执单附件 ----
    receipt_upload = UploadFile(filename=receipt_filename, file=BytesIO(receipt_content))
    receipt_attachment = save_file(db, receipt_upload, "project", contract_id, receipt_item_id)

    # ---- 保存发票附件（如果有） ----
    invoice_attachment_id = None
    if invoice_content and invoice_filename:
        invoice_upload = UploadFile(filename=invoice_filename, file=BytesIO(invoice_content))
        invoice_attachment = save_file(db, invoice_upload, "project", contract_id, invoice_item_id)
        invoice_attachment_id = str(invoice_attachment.id)

    receipt_amount_str = str(receipt_amount) if receipt_amount is not None else None
    invoice_amount_str = str(invoice_amount) if invoice_amount is not None else None

    # ---- 金额匹配逻辑 ----
    # 情况 1：两个文件都有金额
    if receipt_amount is not None and invoice_amount is not None:
        if _amounts_match(receipt_amount, invoice_amount):
            # 匹配成功 → 自动创建回款，以回执单金额为准
            payment_data = schemas.PaymentCreate(
                amount=receipt_amount,
                payment_date=receipt_date or invoice_date,
                receipt_file_id=str(receipt_attachment.id),
                invoice_file_id=invoice_attachment_id,
                remark=f"AI 解析自动创建（回执单: {receipt_filename}, 发票: {invoice_filename}）",
            )
            payment = services.create_payment(db, contract_id, payment_data)
            return {
                "matched": True,
                "receipt_amount": receipt_amount_str,
                "invoice_amount": invoice_amount_str,
                "final_amount": receipt_amount_str,
                "payment_date": str(receipt_date or invoice_date) if (receipt_date or invoice_date) else None,
                "payment": schemas.PaymentResponse(
                    id=payment.id,
                    contract_id=payment.contract_id,
                    amount=payment.amount,
                    payment_date=payment.payment_date,
                    receipt_file_id=payment.receipt_file_id,
                    invoice_file_id=payment.invoice_file_id,
                    remark=payment.remark,
                    created_at=payment.created_at,
                ),
            }
        else:
            # 不匹配 → 返回两个金额让前端确认，不创建回款
            return {
                "matched": False,
                "receipt_amount": receipt_amount_str,
                "invoice_amount": invoice_amount_str,
                "final_amount": None,
                "payment_date": str(receipt_date or invoice_date) if (receipt_date or invoice_date) else None,
                "payment": None,
                "receipt_file_id": str(receipt_attachment.id),
                "invoice_file_id": invoice_attachment_id,
            }

    # 情况 2：只有回执单有金额
    if receipt_amount is not None:
        payment_data = schemas.PaymentCreate(
            amount=receipt_amount,
            payment_date=receipt_date,
            receipt_file_id=str(receipt_attachment.id),
            invoice_file_id=invoice_attachment_id,
            remark=f"AI 解析自动创建（回执单: {receipt_filename}"
                   + (f", 发票: {invoice_filename}）" if invoice_filename else "）"),
        )
        payment = services.create_payment(db, contract_id, payment_data)
        return {
            "matched": True,
            "receipt_amount": receipt_amount_str,
            "invoice_amount": invoice_amount_str,
            "final_amount": receipt_amount_str,
            "payment_date": str(receipt_date) if receipt_date else None,
            "payment": schemas.PaymentResponse(
                id=payment.id,
                contract_id=payment.contract_id,
                amount=payment.amount,
                payment_date=payment.payment_date,
                receipt_file_id=payment.receipt_file_id,
                invoice_file_id=payment.invoice_file_id,
                remark=payment.remark,
                created_at=payment.created_at,
            ),
        }

    # 情况 3：只有发票有金额（理论上回执单应该有，但做防御）
    if invoice_amount is not None:
        payment_data = schemas.PaymentCreate(
            amount=invoice_amount,
            payment_date=invoice_date,
            receipt_file_id=str(receipt_attachment.id),
            invoice_file_id=invoice_attachment_id,
            remark=f"AI 解析自动创建（回执单: {receipt_filename}, 发票: {invoice_filename}）",
        )
        payment = services.create_payment(db, contract_id, payment_data)
        return {
            "matched": True,
            "receipt_amount": receipt_amount_str,
            "invoice_amount": invoice_amount_str,
            "final_amount": invoice_amount_str,
            "payment_date": str(invoice_date) if invoice_date else None,
            "payment": schemas.PaymentResponse(
                id=payment.id,
                contract_id=payment.contract_id,
                amount=payment.amount,
                payment_date=payment.payment_date,
                receipt_file_id=payment.receipt_file_id,
                invoice_file_id=payment.invoice_file_id,
                remark=payment.remark,
                created_at=payment.created_at,
            ),
        }

    # 情况 4：两个文件都没解析出金额
    return {
        "matched": False,
        "receipt_amount": None,
        "invoice_amount": None,
        "final_amount": None,
        "payment_date": str(receipt_date or invoice_date) if (receipt_date or invoice_date) else None,
        "payment": None,
        "receipt_file_id": str(receipt_attachment.id),
        "invoice_file_id": invoice_attachment_id,
        "detail": "无法从回执单和发票中提取金额，请手动填写",
    }


@project_router.post("/{contract_id}/payments/parse/confirm", response_model=schemas.PaymentResponse, status_code=201)
def confirm_parse_payment(
    contract_id: str,
    data: schemas.PaymentParseConfirmRequest,
    db: Session = Depends(get_db),
):
    """确认金额后创建回款记录

    前端在金额不匹配时弹窗让用户确认，确认后调用此接口用已有的附件文件创建回款记录。
    """
    # 验证合同存在
    contract = services.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    payment_data = schemas.PaymentCreate(
        amount=data.amount,
        payment_date=data.payment_date,
        receipt_file_id=data.receipt_file_id,
        invoice_file_id=data.invoice_file_id,
        remark="用户确认金额后创建",
    )
    payment = services.create_payment(db, contract_id, payment_data)
    return schemas.PaymentResponse(
        id=payment.id,
        contract_id=payment.contract_id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        receipt_file_id=payment.receipt_file_id,
        invoice_file_id=payment.invoice_file_id,
        remark=payment.remark,
        created_at=payment.created_at,
    )


# ============================================================
# ProjectType CRUD
# ============================================================

@project_type_router.get("", response_model=list[schemas.ProjectTypeResponse])
def list_project_types(db: Session = Depends(get_db)):
    """获取所有项目类型"""
    return services.list_project_types(db)


@project_type_router.post("", response_model=schemas.ProjectTypeResponse, status_code=201)
def create_project_type(
    data: schemas.ProjectTypeCreate,
    db: Session = Depends(get_db),
):
    """创建项目类型"""
    return services.create_project_type(db, data)


@project_type_router.put("/{type_id}", response_model=schemas.ProjectTypeResponse)
def update_project_type(
    type_id: str,
    data: schemas.ProjectTypeUpdate,
    db: Session = Depends(get_db),
):
    """更新项目类型"""
    return services.update_project_type(db, type_id, data)


@project_type_router.delete("/{type_id}", status_code=204)
def delete_project_type(type_id: str, db: Session = Depends(get_db)):
    """软删除项目类型"""
    services.delete_project_type(db, type_id)
