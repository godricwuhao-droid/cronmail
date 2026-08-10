"""
项目管理合同模块业务逻辑层
"""
import json
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from src.project.models import ProjectContract, ProjectServiceLine, ProjectType, ProjectContractPayment
from src.project import schemas


# ============================================================
# ProjectServiceLine CRUD
# ============================================================

def list_service_lines(db: Session, contract_id: str) -> list[ProjectServiceLine]:
    """获取合同下所有服务行"""
    return (
        db.query(ProjectServiceLine)
        .filter(ProjectServiceLine.contract_id == contract_id)
        .order_by(ProjectServiceLine.sort_order)
        .all()
    )


def get_service_line(db: Session, line_id: str) -> Optional[ProjectServiceLine]:
    """获取单个服务行"""
    return (
        db.query(ProjectServiceLine)
        .filter(ProjectServiceLine.id == line_id)
        .first()
    )


def _calc_line_total_price(data: schemas.ProjectServiceLineCreate) -> Decimal:
    """计算服务行总价 = quantity × period_months × unit_price"""
    return data.quantity * Decimal(str(data.period_months)) * data.unit_price


def create_service_line(
    db: Session, contract_id: str, data: schemas.ProjectServiceLineCreate,
) -> ProjectServiceLine:
    """创建服务行"""
    total_price = _calc_line_total_price(data)
    line = ProjectServiceLine(
        contract_id=contract_id,
        category=data.category,
        item_name=data.item_name,
        specification=data.specification,
        unit=data.unit,
        quantity=data.quantity,
        period_months=data.period_months,
        unit_price=data.unit_price,
        total_price=total_price,
        sort_order=data.sort_order,
        service_description=data.service_description,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_service_line(
    db: Session, line: ProjectServiceLine, data: schemas.ProjectServiceLineUpdate,
) -> ProjectServiceLine:
    """更新服务行"""
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(line, field, value)

    # 自动重算 total_price
    line.total_price = line.quantity * Decimal(str(line.period_months)) * line.unit_price

    db.commit()
    db.refresh(line)
    return line


def delete_service_line(db: Session, line: ProjectServiceLine):
    """删除服务行"""
    db.delete(line)
    db.commit()


def batch_save_service_lines(
    db: Session, contract_id: str, lines: list[schemas.ProjectServiceLineCreate],
) -> list[ProjectServiceLine]:
    """批量保存服务行（全量替换：先删后插）"""
    # 删除现有行
    db.query(ProjectServiceLine).filter(
        ProjectServiceLine.contract_id == contract_id
    ).delete()
    # 批量插入新行
    new_lines = []
    for i, line_data in enumerate(lines):
        total_price = _calc_line_total_price(line_data)
        line = ProjectServiceLine(
            contract_id=contract_id,
            category=line_data.category,
            item_name=line_data.item_name,
            specification=line_data.specification,
            unit=line_data.unit,
            quantity=line_data.quantity,
            period_months=line_data.period_months,
            unit_price=line_data.unit_price,
            total_price=total_price,
            sort_order=line_data.sort_order if line_data.sort_order else i,
            service_description=line_data.service_description,
        )
        db.add(line)
        new_lines.append(line)
    db.commit()
    for line in new_lines:
        db.refresh(line)
    return new_lines


def _calc_auto_amount(db: Session, contract_id: str) -> Optional[Decimal]:
    """计算金额自动汇总：SUM(service_lines.total_price)"""
    lines = db.query(ProjectServiceLine).filter(
        ProjectServiceLine.contract_id == contract_id
    ).all()
    if not lines:
        return None
    total = sum((line.total_price for line in lines), Decimal("0.00"))
    return total


def _find_related_contract(db: Session, contract: ProjectContract) -> Optional[ProjectContract]:
    """双向查询背靠背关联合同"""
    if contract.related_contract_id:
        return db.query(ProjectContract).filter(
            ProjectContract.id == contract.related_contract_id
        ).first()
    # 反向查询：查找 related_contract_id 指向当前合同的合同
    return db.query(ProjectContract).filter(
        ProjectContract.related_contract_id == contract.id
    ).first()


# ============================================================
# ProjectContract CRUD
# ============================================================

def list_contracts(
    db: Session,
    company_code: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ProjectContract], int]:
    """查询项目管理合同列表"""
    query = db.query(ProjectContract)
    if company_code:
        query = query.filter(ProjectContract.company_code == company_code)
    if search:
        query = query.filter(
            or_(
                ProjectContract.name.ilike(f"%{search}%"),
                ProjectContract.contract_no.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    items = (
        query.order_by(ProjectContract.sort_order.asc(), ProjectContract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_contract(db: Session, contract_id: str) -> Optional[ProjectContract]:
    return (
        db.query(ProjectContract)
        .filter(ProjectContract.id == contract_id)
        .first()
    )


def create_contract(db: Session, data: schemas.ProjectContractCreate) -> ProjectContract:
    # 分离 service_lines
    service_lines_data = data.service_lines
    create_dict = data.model_dump(exclude={"service_lines"})

    contract = ProjectContract(**create_dict)
    db.add(contract)
    db.flush()  # 确保 contract.id 生成（SQLite 兼容）

    # 创建 service_lines
    if service_lines_data:
        for i, line_data in enumerate(service_lines_data):
            total_price = _calc_line_total_price(line_data)
            line = ProjectServiceLine(
                contract_id=contract.id,
                category=line_data.category,
                item_name=line_data.item_name,
                specification=line_data.specification,
                unit=line_data.unit,
                quantity=line_data.quantity,
                period_months=line_data.period_months,
                unit_price=line_data.unit_price,
                total_price=total_price,
                sort_order=line_data.sort_order if line_data.sort_order else i,
                service_description=line_data.service_description,
            )
            db.add(line)

        # 如果用户未手动填 amount，自动计算
        if data.amount is None:
            auto_amount = sum(
                (_calc_line_total_price(l) for l in service_lines_data), Decimal("0.00")
            )
            contract.amount = auto_amount

    db.commit()
    db.refresh(contract)
    return contract


def update_contract(
    db: Session, contract: ProjectContract, data: schemas.ProjectContractUpdate,
) -> ProjectContract:
    service_lines_data = data.service_lines
    update_dict = data.model_dump(exclude_unset=True, exclude={"service_lines"})

    for field, value in update_dict.items():
        setattr(contract, field, value)

    # 如果传入了 service_lines，全量替换
    if service_lines_data is not None:
        # 删除现有行
        db.query(ProjectServiceLine).filter(
            ProjectServiceLine.contract_id == contract.id
        ).delete()
        # 插入新行
        for i, line_data in enumerate(service_lines_data):
            total_price = _calc_line_total_price(line_data)
            line = ProjectServiceLine(
                contract_id=contract.id,
                category=line_data.category,
                item_name=line_data.item_name,
                specification=line_data.specification,
                unit=line_data.unit,
                quantity=line_data.quantity,
                period_months=line_data.period_months,
                unit_price=line_data.unit_price,
                total_price=total_price,
                sort_order=line_data.sort_order if line_data.sort_order else i,
                service_description=line_data.service_description,
            )
            db.add(line)

        # 如果用户未手动更新 amount，重新自动计算
        if "amount" not in update_dict:
            auto_amount = sum(
                (_calc_line_total_price(l) for l in service_lines_data), Decimal("0.00")
            )
            contract.amount = auto_amount

    db.commit()
    db.refresh(contract)
    return contract


def delete_contract(db: Session, contract: ProjectContract):
    """删除合同，同时清理关联的附件、附件状态、回款记录"""
    import os
    from src.attachment.models import Attachment, AttachmentStatus
    from src.attachment.services import UPLOAD_BASE_DIR

    contract_id = str(contract.id)

    # 0. 删除回款记录（CASCADE 会处理，但显式清理确保一致）
    db.query(ProjectContractPayment).filter(
        ProjectContractPayment.contract_id == contract_id
    ).delete(synchronize_session="fetch")

    # 1. 查询该合同的所有附件记录
    attachments = db.query(Attachment).filter(
        Attachment.contract_type == "project",
        Attachment.contract_id == contract_id,
    ).all()

    # 2. 删除磁盘文件
    for att in attachments:
        file_full_path = os.path.join(UPLOAD_BASE_DIR, att.file_path)
        try:
            if os.path.exists(file_full_path):
                os.remove(file_full_path)
        except OSError:
            pass  # 文件已不存在或无法删除，继续

    # 3. 删除附件状态记录
    db.query(AttachmentStatus).filter(
        AttachmentStatus.contract_type == "project",
        AttachmentStatus.contract_id == contract_id,
    ).delete(synchronize_session="fetch")

    # 4. 删除附件记录
    db.query(Attachment).filter(
        Attachment.contract_type == "project",
        Attachment.contract_id == contract_id,
    ).delete(synchronize_session="fetch")

    # 5. 尝试删除 NFS 目录（如果为空）
    contract_dir = os.path.join(UPLOAD_BASE_DIR, "project", contract_id)
    try:
        os.rmdir(contract_dir)  # rmdir 只在目录为空时成功
    except OSError:
        pass

    # 6. 删除合同本身
    db.delete(contract)
    db.commit()


# ============================================================
# ProjectType CRUD
# ============================================================

def list_project_types(db: Session) -> list[ProjectType]:
    """获取所有活跃的项目类型，按 sort_order 排序"""
    return (
        db.query(ProjectType)
        .filter(ProjectType.is_active == True)
        .order_by(ProjectType.sort_order)
        .all()
    )


def get_project_type(db: Session, type_id: str) -> Optional[ProjectType]:
    """获取单个活跃项目类型"""
    return (
        db.query(ProjectType)
        .filter(ProjectType.id == type_id, ProjectType.is_active == True)
        .first()
    )


def create_project_type(db: Session, data: schemas.ProjectTypeCreate) -> ProjectType:
    """创建项目类型"""
    pt = ProjectType(name=data.name, sort_order=data.sort_order or 0)
    db.add(pt)
    db.commit()
    db.refresh(pt)
    return pt


def update_project_type(db: Session, type_id: str, data: schemas.ProjectTypeUpdate) -> ProjectType:
    """更新项目类型"""
    pt = get_project_type(db, type_id)
    if not pt:
        raise HTTPException(status_code=404, detail="项目类型不存在")
    if data.name is not None:
        pt.name = data.name
    if data.sort_order is not None:
        pt.sort_order = data.sort_order
    db.commit()
    db.refresh(pt)
    return pt


def delete_project_type(db: Session, type_id: str):
    """软删除项目类型"""
    pt = get_project_type(db, type_id)
    if not pt:
        raise HTTPException(status_code=404, detail="项目类型不存在")
    pt.is_active = False
    db.commit()


# ============================================================
# Overview 统计
# ============================================================

def _parse_raw_tables_json(raw_tables_json) -> dict:
    """兼容字符串和已解析对象格式，返回 resource_summary.stats 字典"""
    if raw_tables_json is None:
        return {}
    if isinstance(raw_tables_json, str):
        try:
            raw_tables_json = json.loads(raw_tables_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    if isinstance(raw_tables_json, dict):
        rs = raw_tables_json.get("resource_summary", {})
        if isinstance(rs, dict):
            return rs.get("stats", {}) or {}
    return {}


def get_project_overview(db: Session, year: Optional[int] = None) -> dict:
    """获取项目概览统计：按 project_type 维度、服务期内月度分摊

    新口径：
    1. 按 project_type 拆分维度统计
    2. 合同从 start_date 到 end_date 之间的月份才算「服务期内」
    3. 金额分摊：总金额 / 服务月数 = 月度分摊金额
    4. 资源消耗：raw_tables_json 中 resource_summary.stats 按服务月数分摊
    """

    from datetime import date as dt_date, timedelta

    if year is None:
        year = dt_date.today().year

    contracts = db.query(ProjectContract).all()

    # 资源字段列表
    RESOURCE_KEYS = [
        "total_vcpu", "total_memory_gb", "total_storage_gb",
        "total_gpu_count", "total_gpu_tops", "total_bandwidth_mbps",
        "total_rack_count", "total_ip_count",
    ]

    def _zero_resources() -> dict:
        return {k: 0 for k in RESOURCE_KEYS}

    def _safe_float(v) -> float:
        if v is None:
            return 0.0
        return float(v)

    def _generate_months(start: dt_date, end: dt_date) -> list[str]:
        """生成从 start 到 end（含）之间所有 YYYY-MM 字符串"""
        months = []
        current = dt_date(start.year, start.month, 1)
        end_first = dt_date(end.year, end.month, 1)
        while current <= end_first:
            months.append(current.strftime("%Y-%m"))
            # 推进到下个月
            if current.month == 12:
                current = dt_date(current.year + 1, 1, 1)
            else:
                current = dt_date(current.year, current.month + 1, 1)
        return months

    # 中间结构：
    # type_month_map[project_type][month] = {
    #     active_contracts, monthly_amount (Decimal), contracts (list), resources (dict)
    # }
    type_month_map: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(lambda: {
            "active_contracts": 0,
            "monthly_amount": Decimal("0.00"),
            "contracts": [],
            "resources": _zero_resources(),
        })
    )

    # 按 project_type 统计合同数、总金额
    type_total_contracts: dict[str, int] = defaultdict(int)
    type_total_amount: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for c in contracts:
        amount = c.amount or Decimal("0.00")
        pt = c.project_type or "未分类"

        type_total_contracts[pt] += 1
        type_total_amount[pt] += amount

        # 确定服务期范围
        today = dt_date.today()
        if c.start_date and c.end_date:
            start = c.start_date
            end = c.end_date
        elif c.start_date and not c.end_date:
            start = c.start_date
            end = c.start_date  # 只有开始日期，只算当月
        elif c.end_date and not c.start_date:
            start = c.end_date
            end = c.end_date  # 只有结束日期，只算当月
        else:
            # start_date 和 end_date 都为 NULL，跳过该合同的月度分摊
            continue

        # 计算服务月数：max(1, (end - start).days // 30)
        service_days = (end - start).days
        service_months = max(1, service_days // 30)

        # 月度分摊金额
        monthly_amount = amount / Decimal(str(service_months))

        # 解析资源 stats 并分摊
        stats = _parse_raw_tables_json(c.raw_tables_json)
        monthly_vcpu = _safe_float(stats.get("vcpu")) / service_months
        monthly_memory_gb = _safe_float(stats.get("memory_gb")) / service_months
        monthly_storage_gb = _safe_float(stats.get("storage_gb")) / service_months
        monthly_gpu_count = _safe_float(stats.get("gpu_count")) / service_months
        monthly_gpu_tops = _safe_float(stats.get("gpu_tops")) / service_months
        monthly_bandwidth_mbps = _safe_float(stats.get("bandwidth_mbps")) / service_months
        monthly_rack_count = _safe_float(stats.get("rack_count")) / service_months
        monthly_ip_count = _safe_float(stats.get("ip_count")) / service_months

        # 生成服务期内各月份
        service_months_list = _generate_months(start, end)

        for month in service_months_list:
            # 只保留目标年份的月份
            if not month.startswith(str(year) + "-"):
                continue

            entry = type_month_map[pt][month]
            entry["active_contracts"] += 1
            entry["monthly_amount"] += monthly_amount
            entry["contracts"].append({
                "id": str(c.id),
                "name": c.name or "",
                "monthly_amount": str(monthly_amount.quantize(Decimal("0.01"))),
            })
            entry["resources"]["total_vcpu"] += round(monthly_vcpu)
            entry["resources"]["total_memory_gb"] += round(monthly_memory_gb)
            entry["resources"]["total_storage_gb"] += round(monthly_storage_gb)
            entry["resources"]["total_gpu_count"] += round(monthly_gpu_count)
            entry["resources"]["total_gpu_tops"] += round(monthly_gpu_tops)
            entry["resources"]["total_bandwidth_mbps"] += round(monthly_bandwidth_mbps)
            entry["resources"]["total_rack_count"] += round(monthly_rack_count)
            entry["resources"]["total_ip_count"] += round(monthly_ip_count)

    # 构建最终返回结构
    by_project_type = []
    for pt in sorted(type_month_map.keys()):
        monthly_list = []
        for month in sorted(type_month_map[pt].keys()):
            e = type_month_map[pt][month]
            monthly_list.append({
                "month": month,
                "active_contracts": e["active_contracts"],
                "monthly_amount": str(e["monthly_amount"].quantize(Decimal("0.01"))),
                "contracts": e["contracts"],
                "resources": e["resources"],
            })
        by_project_type.append({
            "project_type": pt,
            "total_contracts": type_total_contracts.get(pt, 0),
            "total_amount": str(type_total_amount.get(pt, Decimal("0.00")).quantize(Decimal("0.01"))),
            "monthly": monthly_list,
        })

    return {
        "year": year,
        "by_project_type": by_project_type,
    }


# ============================================================
# ProjectContractPayment CRUD
# ============================================================

def list_payments(db: Session, contract_id: str) -> list[dict]:
    """获取合同的所有回款记录，附带文件 filename 和 mime_type"""
    from src.attachment.models import Attachment

    payments = db.query(ProjectContractPayment).filter(
        ProjectContractPayment.contract_id == contract_id
    ).order_by(ProjectContractPayment.payment_date.desc()).all()

    # 批量查询关联的附件文件
    file_ids = set()
    for p in payments:
        if p.receipt_file_id:
            file_ids.add(p.receipt_file_id)
        if p.invoice_file_id:
            file_ids.add(p.invoice_file_id)

    files_map: dict[str, Attachment] = {}
    if file_ids:
        files = db.query(Attachment).filter(Attachment.id.in_(file_ids)).all()
        files_map = {str(f.id): f for f in files}

    # 构造带文件信息的字典
    result = []
    for p in payments:
        item = {
            "id": str(p.id),
            "contract_id": p.contract_id,
            "amount": p.amount,
            "payment_date": p.payment_date,
            "receipt_file_id": p.receipt_file_id,
            "receipt_filename": None,
            "receipt_mime_type": None,
            "invoice_file_id": p.invoice_file_id,
            "invoice_filename": None,
            "invoice_mime_type": None,
            "remark": p.remark,
            "created_at": p.created_at,
        }
        if p.receipt_file_id:
            receipt_file = files_map.get(str(p.receipt_file_id))
            if receipt_file:
                item["receipt_filename"] = receipt_file.filename
                item["receipt_mime_type"] = receipt_file.mime_type
        if p.invoice_file_id:
            invoice_file = files_map.get(str(p.invoice_file_id))
            if invoice_file:
                item["invoice_filename"] = invoice_file.filename
                item["invoice_mime_type"] = invoice_file.mime_type
        result.append(item)

    return result


def create_payment(db: Session, contract_id: str, data: schemas.PaymentCreate) -> ProjectContractPayment:
    contract = db.query(ProjectContract).filter(ProjectContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    payment = ProjectContractPayment(
        contract_id=contract_id,
        amount=data.amount,
        payment_date=data.payment_date,
        receipt_file_id=data.receipt_file_id,
        invoice_file_id=data.invoice_file_id,
        remark=data.remark,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment(db: Session, payment_id: str, data: schemas.PaymentUpdate) -> ProjectContractPayment:
    payment = db.query(ProjectContractPayment).filter(ProjectContractPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="回款记录不存在")
    if data.amount is not None:
        payment.amount = data.amount
    if data.payment_date is not None:
        payment.payment_date = data.payment_date
    if data.remark is not None:
        payment.remark = data.remark
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, payment_id: str):
    payment = db.query(ProjectContractPayment).filter(ProjectContractPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="回款记录不存在")
    db.delete(payment)
    db.commit()


def get_payment_summary(db: Session, contract_id: str) -> dict:
    """获取合同回款汇总：已回款总额 + 进度百分比"""
    payments = list_payments(db, contract_id)
    contract = db.query(ProjectContract).filter(ProjectContract.id == contract_id).first()
    total_paid = sum(p["amount"] for p in payments) if payments else Decimal("0.00")
    contract_amount = contract.amount if contract and contract.amount else Decimal("0.00")
    progress = round(float(total_paid / contract_amount * 100), 1) if contract_amount > 0 else 0.0
    return {
        "total_paid": str(total_paid),
        "contract_amount": str(contract_amount),
        "progress": progress,
    }


def get_payment_summary_for_contracts(db: Session, contract_ids: list[str]) -> dict[str, dict]:
    """批量获取多个合同的回款汇总，返回 {contract_id: {total_paid, progress}}"""
    if not contract_ids:
        return {}

    from sqlalchemy import func as sa_func
    rows = (
        db.query(
            ProjectContractPayment.contract_id,
            sa_func.sum(ProjectContractPayment.amount).label("total_paid"),
        )
        .filter(ProjectContractPayment.contract_id.in_(contract_ids))
        .group_by(ProjectContractPayment.contract_id)
        .all()
    )

    paid_map = {row.contract_id: row.total_paid for row in rows}

    contracts = db.query(ProjectContract).filter(ProjectContract.id.in_(contract_ids)).all()
    amount_map = {str(c.id): (c.amount or Decimal("0.00")) for c in contracts}

    result = {}
    for cid in contract_ids:
        total_paid = paid_map.get(cid, Decimal("0.00"))
        contract_amount = amount_map.get(cid, Decimal("0.00"))
        progress = round(float(total_paid / contract_amount * 100), 1) if contract_amount > 0 else 0.0
        result[cid] = {
            "total_paid": str(total_paid),
            "progress": progress,
        }
    return result
