"""
合同模块业务逻辑层
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.contract.models import Contract, contract_rental, contract_contact
from src.contract.schemas import ContractCreate, ContractUpdate


def list_contracts(
    db: Session,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Contract], int]:
    """查询合同列表，支持按客户、状态过滤和模糊搜索"""
    query = db.query(Contract)
    if customer_id:
        query = query.filter(Contract.customer_id == customer_id)
    if status:
        query = query.filter(Contract.status == status)
    if search:
        query = query.filter(Contract.name.ilike(f"%{search}%"))

    total = query.count()
    items = query.order_by(Contract.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_contract(db: Session, contract_id: str) -> Optional[Contract]:
    """根据 ID 获取合同"""
    return db.query(Contract).filter(Contract.id == contract_id).first()


def create_contract(db: Session, data: ContractCreate) -> Contract:
    """创建合同，可选关联设备和联系人"""
    contract = Contract(
        customer_id=data.customer_id,
        name=data.name,
        contract_no=data.contract_no,
        start_date=data.start_date,
        end_date=data.end_date,
        billing_model=data.billing_model,
        remark=data.remark,
        status="active",
    )
    db.add(contract)
    db.flush()

    # 关联设备
    if data.rental_ids:
        _link_rentals(db, contract.id, data.rental_ids)

    # 关联联系人
    if data.contacts:
        _replace_contract_contacts(db, contract.id, data.contacts)

    db.commit()
    db.refresh(contract)
    return contract


def update_contract(db: Session, contract: Contract, data: ContractUpdate) -> Contract:
    """更新合同"""
    update_data = data.model_dump(exclude_unset=True)
    contacts_data = update_data.pop("contacts", None)

    for field, value in update_data.items():
        setattr(contract, field, value)

    # 合同关键字段变更时，同步给所有关联设备
    if "end_date" in update_data or "customer_id" in update_data or "start_date" in update_data or "billing_model" in update_data:
        from src.rental.models import RentalRecord
        for rental in contract.rentals:
            if "customer_id" in update_data:
                rental.customer_id = contract.customer_id
            if "end_date" in update_data:
                rental.end_date = contract.end_date
            if "start_date" in update_data:
                rental.start_date = contract.start_date
            if "billing_model" in update_data:
                rental.billing_model = contract.billing_model

    if contacts_data is not None:
        _replace_contract_contacts(db, contract.id, contacts_data)

    db.commit()
    db.refresh(contract)
    return contract


def delete_contract(db: Session, contract: Contract):
    """删除合同（CASCADE 会删除中间表关联）"""
    db.delete(contract)
    db.commit()


# ============================================================
# 设备关联
# ============================================================

def link_rentals(db: Session, contract_id: str, rental_ids: list[str]):
    """关联设备到合同"""
    _link_rentals(db, contract_id, rental_ids)
    db.commit()


def unlink_rentals(db: Session, contract_id: str, rental_ids: list[str]):
    """取消关联设备，并将设备状态恢复为「空闲中」"""
    from src.rental.models import RentalRecord
    for rid in rental_ids:
        rental = db.query(RentalRecord).filter(RentalRecord.id == rid).first()
        if rental:
            rental.status = '空闲中'
    db.execute(
        contract_rental.delete().where(
            and_(
                contract_rental.c.contract_id == contract_id,
                contract_rental.c.rental_id.in_(rental_ids),
            )
        )
    )
    db.commit()


def _link_rentals(db: Session, contract_id: str, rental_ids: list[str]):
    """关联设备（跳过已存在的关系避免 duplicate key；检测 rental_id 已被其他合同占用）

    contract_rental 中间表列顺序: contract_id(0), rental_id(1), created_at(2)
    """
    import logging
    _logger = logging.getLogger(__name__)

    # 获取合同（用于同步 end_date）
    contract = db.query(Contract).filter(Contract.id == contract_id).first()

    # 查询已关联的 rental_id
    existing_rows = db.execute(
        contract_rental.select().where(
            contract_rental.c.contract_id == contract_id
        )
    ).fetchall()
    existing_ids = {row[1] for row in existing_rows}  # row[1] = rental_id

    # 查询所有已被占用的 rental_id（全局，用于冲突检测）
    all_rows = db.execute(contract_rental.select()).fetchall()
    occupied = {row[1]: row[0] for row in all_rows}  # rental_id -> contract_id

    from src.rental.models import RentalRecord

    for rid in rental_ids:
        if rid in existing_ids:
            continue
        if rid in occupied and occupied[rid] != contract_id:
            _logger.warning(
                f"设备 {rid} 已关联到合同 {occupied[rid]}，跳过关联到合同 {contract_id}"
            )
            continue
        db.execute(
            contract_rental.insert().values(
                contract_id=contract_id,
                rental_id=rid,
            )
        )
        # 同步设备字段：从合同继承
        if contract:
            rental = db.query(RentalRecord).filter(RentalRecord.id == rid).first()
            if rental:
                rental.customer_id = contract.customer_id
                rental.end_date = contract.end_date
                rental.start_date = contract.start_date
                rental.billing_model = contract.billing_model
                rental.status = '租赁中'


# ============================================================
# 合同联系人
# ============================================================

def get_contract_contacts(db: Session, contract_id: str) -> list[dict]:
    """获取合同关联的联系人详情

    返回: [{"contact_id": "...", "name": "...", "email": "...", "recipient_type": "to"}, ...]
    """
    from sqlalchemy import text

    rows = db.execute(
        text(
            "SELECT c.id, c.name, c.email, cc.recipient_type "
            "FROM contract_contact cc "
            "JOIN contact c ON cc.contact_id = c.id "
            "WHERE cc.contract_id = :contract_id"
        ),
        {"contract_id": contract_id},
    ).fetchall()

    return [
        {"contact_id": row[0], "name": row[1], "email": row[2], "recipient_type": row[3]}
        for row in rows
    ]


def _replace_contract_contacts(db: Session, contract_id: str, contacts: list):
    """全量替换合同联系人

    contacts 可以是 ContractContactPayload 对象列表或 dict 列表
    """
    db.execute(
        contract_contact.delete().where(
            contract_contact.c.contract_id == contract_id
        )
    )
    for c in contacts:
        if hasattr(c, 'contact_id'):
            cid = c.contact_id
            rtype = c.recipient_type
        else:
            cid = c['contact_id']
            rtype = c.get('recipient_type', 'to')
        db.execute(
            contract_contact.insert().values(
                contract_id=contract_id,
                contact_id=cid,
                recipient_type=rtype,
            )
        )


def get_contract_rentals(db: Session, contract_id: str) -> list[dict]:
    """获取合同关联的设备简要列表

    优先从 contract_rental 中间表查实时数据；
    如果中间表已清理（合同已回收），则从 history_rental_ids 反查。
    """
    from sqlalchemy import text

    rows = db.execute(
        text(
            "SELECT r.id, r.machine_model, r.private_ip, r.public_ips, r.os_version, r.status, r.rack_location "
            "FROM rental_record r "
            "JOIN contract_rental cr ON r.id = cr.rental_id "
            "WHERE cr.contract_id = :contract_id"
        ),
        {"contract_id": contract_id},
    ).fetchall()

    if not rows:
        # 中间表已清理，从 history_rental_ids 反查
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if contract and contract.history_rental_ids:
            from src.rental.models import RentalRecord
            history_rentals = (
                db.query(RentalRecord)
                .filter(RentalRecord.id.in_(contract.history_rental_ids))
                .all()
            )
            result = []
            for r in history_rentals:
                public_ips = r.public_ips
                if isinstance(public_ips, str):
                    try:
                        public_ips = json.loads(public_ips)
                    except (json.JSONDecodeError, TypeError):
                        public_ips = []
                result.append({
                    "id": r.id, "machine_model": r.machine_model,
                    "private_ip": r.private_ip, "public_ips": public_ips,
                    "os_version": r.os_version, "status": r.status,
                    "rack_location": r.rack_location or "",
                })
            return result
        return []

    result = []
    for row in rows:
        public_ips_raw = row[3]
        if isinstance(public_ips_raw, str):
            try:
                public_ips_raw = json.loads(public_ips_raw)
            except (json.JSONDecodeError, TypeError):
                public_ips_raw = []
        result.append({
            "id": row[0], "machine_model": row[1], "private_ip": row[2],
            "public_ips": public_ips_raw, "os_version": row[4], "status": row[5],
            "rack_location": row[6] or "",
        })
    return result
