"""
合同模块业务逻辑层
"""
import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from src.contract.models import Contract, contract_rental, contract_contact
from src.contract.schemas import ContractCreate, ContractUpdate
from src.core.timezone import local_today
from src.core.crypto import decrypt_password


def _safe_decrypt(value):
    """安全解密：失败时返回空字符串，不抛异常"""
    try:
        return decrypt_password(value or "") if value else ""
    except Exception:
        return ""


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
    items = query.order_by(Contract.sort_order.asc(), Contract.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_contract(db: Session, contract_id: str) -> Optional[Contract]:
    """根据 ID 获取合同"""
    return db.query(Contract).filter(Contract.id == contract_id).first()


def create_contract(db: Session, data: ContractCreate) -> Contract:
    """创建合同，可选关联设备和联系人；支持续期"""
    contract = Contract(
        customer_id=data.customer_id,
        name=data.name,
        contract_no=data.contract_no,
        start_date=data.start_date,
        end_date=data.end_date,
        billing_model=data.billing_model,
        amount=data.amount,
        remark=data.remark,
        status="active",
        renewed_from_id=data.renewed_from_id,
        sort_order=data.sort_order if data.sort_order else 0,
    )
    db.add(contract)
    db.flush()

    # 续期：先保存旧合同设备快照 + 标记回收，再迁移设备到新合同
    if data.renewed_from_id and data.rental_ids:
        old_contract = db.query(Contract).filter(Contract.id == data.renewed_from_id).first()
        if old_contract:
            # 快照旧合同当前关联的所有设备 ID（含本次迁移的 + 可能残留的）
            old_rows = db.execute(
                contract_rental.select().where(
                    contract_rental.c.contract_id == data.renewed_from_id
                )
            ).fetchall()
            old_rental_ids = [row[1] for row in old_rows]  # row[1] = rental_id
            # 合并去重
            all_old_ids = list(set(old_rental_ids + data.rental_ids))
            old_contract.history_rental_ids = all_old_ids
            old_contract.status = "reclaimed"
        # 删除旧合同的关联
        db.execute(
            contract_rental.delete().where(
                contract_rental.c.contract_id == data.renewed_from_id,
                contract_rental.c.rental_id.in_(data.rental_ids),
            )
        )

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
    """删除合同
    
    删除前：
    1. 遍历关联设备，将 status 设为 '空闲中'，customer_id 设为 None
    2. 手动清理 contract_contact 和 contract_rental 中间表行，
       避免 SQLAlchemy secondary relationship 的 CASCADE 行为因
       contract_contact 复合主键 (contract_id, contact_id, recipient_type)
       产生 StaleDataError
    """
    from src.rental.models import RentalRecord
    for rental in contract.rentals:
        rental.status = '空闲中'
        rental.customer_id = None

    # 手动清理中间表，绕过 secondary relationship 的 cascade 缺陷
    db.execute(
        contract_contact.delete().where(
            contract_contact.c.contract_id == contract.id
        )
    )
    db.execute(
        contract_rental.delete().where(
            contract_rental.c.contract_id == contract.id
        )
    )

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
    """取消关联设备，并将设备状态恢复为「空闲中」并清空客户关联"""
    from src.rental.models import RentalRecord
    for rid in rental_ids:
        rental = db.query(RentalRecord).filter(RentalRecord.id == rid).first()
        if rental:
            rental.status = '空闲中'
            rental.customer_id = None
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
        try:
            db.execute(
                contract_rental.insert().values(
                    contract_id=contract_id,
                    rental_id=rid,
                )
            )
        except IntegrityError:
            # TOCTOU 竞态：在检查和插入之间，设备已被其他合同关联
            raise HTTPException(status_code=409, detail=f"设备 {rid} 已被其他合同关联")
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

    contacts 可以是 ContractContactPayload 对象列表或 dict 列表。
    自动按 (contact_id, recipient_type) 去重，避免前端传入重复联系人导致 IntegrityError。
    """
    db.execute(
        contract_contact.delete().where(
            contract_contact.c.contract_id == contract_id
        )
    )
    seen: set[tuple[str, str]] = set()
    for c in contacts:
        if hasattr(c, 'contact_id'):
            cid = c.contact_id
            rtype = c.recipient_type
        else:
            cid = c['contact_id']
            rtype = c.get('recipient_type', 'to')
        key = (cid, rtype)
        if key in seen:
            continue
        seen.add(key)
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
            "SELECT r.id, r.machine_model, r.private_ip, r.public_ips, r.os_version, r.status, r.rack_location, "
            "r.system_disk, r.data_disks, r.bandwidth_mbps, r.cpu_model, r.memory_gb, r.gpu_info, "
            "r.ssh_port, r.root_username, r.root_password_enc, r.end_date "
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
                data_disks_val = r.data_disks
                if isinstance(public_ips, str):
                    try:
                        public_ips = json.loads(public_ips)
                    except (json.JSONDecodeError, TypeError):
                        public_ips = []
                if isinstance(data_disks_val, str):
                    try:
                        data_disks_val = json.loads(data_disks_val)
                    except (json.JSONDecodeError, TypeError):
                        data_disks_val = []
                result.append({
                    "id": r.id, "machine_model": r.machine_model,
                    "private_ip": r.private_ip, "public_ips": public_ips,
                    "os_version": r.os_version, "status": r.status,
                    "rack_location": r.rack_location or "",
                    "system_disk": r.system_disk or "", "data_disks": data_disks_val or [],
                    "bandwidth_mbps": r.bandwidth_mbps or 0, "cpu_model": r.cpu_model or "",
                    "memory_gb": r.memory_gb or 0, "gpu_info": r.gpu_info or "",
                "ssh_port": r.ssh_port or 22, "root_username": r.root_username or "",
                "root_password_enc": r.root_password_enc or "",
                "root_password": _safe_decrypt(r.root_password_enc),
                "end_date": str(r.end_date) if r.end_date else "",
            })
            return result
        return []

    result = []
    for row in rows:
        public_ips_raw = row[3]
        data_disks_raw = row[8]
        if isinstance(public_ips_raw, str):
            try:
                public_ips_raw = json.loads(public_ips_raw)
            except (json.JSONDecodeError, TypeError):
                public_ips_raw = []
        if isinstance(data_disks_raw, str):
            try:
                data_disks_raw = json.loads(data_disks_raw)
            except (json.JSONDecodeError, TypeError):
                data_disks_raw = []
        result.append({
            "id": row[0], "machine_model": row[1], "private_ip": row[2],
            "public_ips": public_ips_raw, "os_version": row[4], "status": row[5],
            "rack_location": row[6] or "",
            "system_disk": row[7] or "", "data_disks": data_disks_raw or [],
            "bandwidth_mbps": row[9] or 0, "cpu_model": row[10] or "",
            "memory_gb": row[11] or 0, "gpu_info": row[12] or "",
            "ssh_port": row[13] or 22, "root_username": row[14] or "",
            "root_password_enc": row[15] or "",
            "root_password": _safe_decrypt(row[15]),
            "end_date": str(row[16]) if row[16] else "",
        })
    return result
