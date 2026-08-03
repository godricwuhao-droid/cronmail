"""
项目管理合同模块业务逻辑层
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.project.models import ProjectContract, ProjectServiceLine
from src.project.schemas import (
    ProjectContractCreate,
    ProjectContractUpdate,
    ProjectServiceLineCreate,
    ProjectServiceLineUpdate,
)


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


def _calc_line_total_price(data: ProjectServiceLineCreate) -> Decimal:
    """计算服务行总价 = quantity × period_months × unit_price"""
    return data.quantity * Decimal(str(data.period_months)) * data.unit_price


def create_service_line(
    db: Session, contract_id: str, data: ProjectServiceLineCreate,
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
    db: Session, line: ProjectServiceLine, data: ProjectServiceLineUpdate,
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
    db: Session, contract_id: str, lines: list[ProjectServiceLineCreate],
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


def create_contract(db: Session, data: ProjectContractCreate) -> ProjectContract:
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
    db: Session, contract: ProjectContract, data: ProjectContractUpdate,
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
    db.delete(contract)
    db.commit()
