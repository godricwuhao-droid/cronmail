"""
算力服务合同模块业务逻辑层
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.compute_service.models import ComputeServiceContract, ContractServiceLine
from src.compute_service.schemas import (
    ComputeServiceContractCreate,
    ComputeServiceContractUpdate,
    ContractServiceLineCreate,
    ContractServiceLineUpdate,
)


# ============================================================
# ContractServiceLine CRUD
# ============================================================

def list_service_lines(db: Session, contract_id: str) -> list[ContractServiceLine]:
    """获取合同下所有服务行"""
    return (
        db.query(ContractServiceLine)
        .filter(ContractServiceLine.contract_id == contract_id)
        .order_by(ContractServiceLine.sort_order)
        .all()
    )


def get_service_line(db: Session, line_id: str) -> Optional[ContractServiceLine]:
    """获取单个服务行"""
    return (
        db.query(ContractServiceLine)
        .filter(ContractServiceLine.id == line_id)
        .first()
    )


def _calc_line_total_price(data: ContractServiceLineCreate) -> Decimal:
    """计算服务行总价，优先使用手动覆盖值"""
    if data.manual_total_price is not None:
        return data.manual_total_price
    return data.quantity * Decimal(str(data.period_months)) * data.unit_price


def create_service_line(
    db: Session, contract_id: str, data: ContractServiceLineCreate,
) -> ContractServiceLine:
    """创建服务行"""
    total_price = _calc_line_total_price(data)
    line = ContractServiceLine(
        contract_id=contract_id,
        category=data.category,
        item_name=data.item_name,
        specification=data.specification,
        vcpu_count=data.vcpu_count,
        memory_gb=data.memory_gb,
        storage_gb=data.storage_gb,
        unit=data.unit,
        quantity=data.quantity,
        period_months=data.period_months,
        unit_price=data.unit_price,
        total_price=total_price,
        sort_order=data.sort_order,
        service_description=data.service_description,
        gpu_count=data.gpu_count,
        gpu_model=data.gpu_model,
        gpu_memory_gb=data.gpu_memory_gb,
        gpu_tops=data.gpu_tops,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_service_line(
    db: Session, line: ContractServiceLine, data: ContractServiceLineUpdate,
) -> ContractServiceLine:
    """更新服务行，支持手动覆盖 total_price"""
    update_data = data.model_dump(exclude_unset=True)

    # 提取 manual_total_price 并决定 total_price 计算方式
    mtp = update_data.pop("manual_total_price", None)
    manual_specified = "manual_total_price" in data.model_dump(exclude_unset=True)

    # 基础字段（用于自动计算 fallback）
    quantity = update_data.get("quantity", line.quantity)
    period_months = update_data.get("period_months", line.period_months)
    unit_price = update_data.get("unit_price", line.unit_price)

    for field, value in update_data.items():
        setattr(line, field, value)

    # 决定 total_price
    if manual_specified:
        if mtp is not None:
            line.total_price = mtp
        else:
            # 手动传了 None，清回自动计算
            line.total_price = quantity * Decimal(str(period_months)) * unit_price
    else:
        # 没传 manual_total_price，自动重算
        line.total_price = quantity * Decimal(str(period_months)) * unit_price

    db.commit()
    db.refresh(line)
    return line


def delete_service_line(db: Session, line: ContractServiceLine):
    """删除服务行"""
    db.delete(line)
    db.commit()


def batch_save_service_lines(
    db: Session, contract_id: str, lines: list[ContractServiceLineCreate],
) -> list[ContractServiceLine]:
    """批量保存服务行（全量替换：先删后插）"""
    # 删除现有行
    db.query(ContractServiceLine).filter(
        ContractServiceLine.contract_id == contract_id
    ).delete()
    # 批量插入新行
    new_lines = []
    for i, line_data in enumerate(lines):
        total_price = _calc_line_total_price(line_data)
        line = ContractServiceLine(
            contract_id=contract_id,
            category=line_data.category,
            item_name=line_data.item_name,
            specification=line_data.specification,
            vcpu_count=line_data.vcpu_count,
            memory_gb=line_data.memory_gb,
            storage_gb=line_data.storage_gb,
            unit=line_data.unit,
            quantity=line_data.quantity,
            period_months=line_data.period_months,
            unit_price=line_data.unit_price,
            total_price=total_price,
            sort_order=line_data.sort_order if line_data.sort_order else i,
            service_description=line_data.service_description,
            gpu_count=line_data.gpu_count,
            gpu_model=line_data.gpu_model,
            gpu_memory_gb=line_data.gpu_memory_gb,
            gpu_tops=line_data.gpu_tops,
        )
        db.add(line)
        new_lines.append(line)
    db.commit()
    for line in new_lines:
        db.refresh(line)
    return new_lines


def _calc_auto_amount(db: Session, contract_id: str) -> Optional[Decimal]:
    """计算金额自动汇总：SUM(service_lines.total_price)"""
    lines = db.query(ContractServiceLine).filter(
        ContractServiceLine.contract_id == contract_id
    ).all()
    if not lines:
        return None
    total = sum((line.total_price for line in lines), Decimal("0.00"))
    return total


def _find_related_contract(db: Session, contract: ComputeServiceContract) -> Optional[ComputeServiceContract]:
    """双向查询背靠背关联合同"""
    if contract.related_contract_id:
        return db.query(ComputeServiceContract).filter(
            ComputeServiceContract.id == contract.related_contract_id
        ).first()
    # 反向查询：查找 related_contract_id 指向当前合同的合同
    return db.query(ComputeServiceContract).filter(
        ComputeServiceContract.related_contract_id == contract.id
    ).first()


# ============================================================
# ComputeServiceContract CRUD
# ============================================================

def list_contracts(
    db: Session,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ComputeServiceContract], int]:
    """查询算力服务合同列表"""
    query = db.query(ComputeServiceContract)
    if customer_id:
        query = query.filter(ComputeServiceContract.customer_id == customer_id)
    if search:
        query = query.filter(
            or_(
                ComputeServiceContract.name.ilike(f"%{search}%"),
                ComputeServiceContract.contract_no.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    items = (
        query.order_by(ComputeServiceContract.sort_order.asc(), ComputeServiceContract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_contract(db: Session, contract_id: str) -> Optional[ComputeServiceContract]:
    return (
        db.query(ComputeServiceContract)
        .filter(ComputeServiceContract.id == contract_id)
        .first()
    )


def create_contract(db: Session, data: ComputeServiceContractCreate) -> ComputeServiceContract:
    # 分离 service_lines
    service_lines_data = data.service_lines
    create_dict = data.model_dump(exclude={"service_lines"})

    contract = ComputeServiceContract(**create_dict)
    db.add(contract)
    db.flush()  # 确保 contract.id 生成（SQLite 兼容）

    # 创建 service_lines
    if service_lines_data:
        for i, line_data in enumerate(service_lines_data):
            total_price = _calc_line_total_price(line_data)
            line = ContractServiceLine(
                contract_id=contract.id,
                category=line_data.category,
                item_name=line_data.item_name,
                specification=line_data.specification,
                vcpu_count=line_data.vcpu_count,
                memory_gb=line_data.memory_gb,
                storage_gb=line_data.storage_gb,
                unit=line_data.unit,
                quantity=line_data.quantity,
                period_months=line_data.period_months,
                unit_price=line_data.unit_price,
                total_price=total_price,
                sort_order=line_data.sort_order if line_data.sort_order else i,
                service_description=line_data.service_description,
                gpu_count=line_data.gpu_count,
                gpu_model=line_data.gpu_model,
                gpu_memory_gb=line_data.gpu_memory_gb,
                gpu_tops=line_data.gpu_tops,
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
    db: Session, contract: ComputeServiceContract, data: ComputeServiceContractUpdate,
) -> ComputeServiceContract:
    service_lines_data = data.service_lines
    update_dict = data.model_dump(exclude_unset=True, exclude={"service_lines"})

    for field, value in update_dict.items():
        setattr(contract, field, value)

    # 如果传入了 service_lines，全量替换
    if service_lines_data is not None:
        # 删除现有行
        db.query(ContractServiceLine).filter(
            ContractServiceLine.contract_id == contract.id
        ).delete()
        # 插入新行
        for i, line_data in enumerate(service_lines_data):
            total_price = _calc_line_total_price(line_data)
            line = ContractServiceLine(
                contract_id=contract.id,
                category=line_data.category,
                item_name=line_data.item_name,
                specification=line_data.specification,
                vcpu_count=line_data.vcpu_count,
                memory_gb=line_data.memory_gb,
                storage_gb=line_data.storage_gb,
                unit=line_data.unit,
                quantity=line_data.quantity,
                period_months=line_data.period_months,
                unit_price=line_data.unit_price,
                total_price=total_price,
                sort_order=line_data.sort_order if line_data.sort_order else i,
                service_description=line_data.service_description,
                gpu_count=line_data.gpu_count,
                gpu_model=line_data.gpu_model,
                gpu_memory_gb=line_data.gpu_memory_gb,
                gpu_tops=line_data.gpu_tops,
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


def delete_contract(db: Session, contract: ComputeServiceContract):
    db.delete(contract)
    db.commit()
