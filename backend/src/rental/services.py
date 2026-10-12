"""
租赁记录模块业务逻辑层
"""
import json
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, String

from src.core.crypto import encrypt_password, decrypt_password
from src.core.timezone import local_today
from src.rental.models import RentalRecord, rental_contact
from src.rental.schemas import (
    RentalRecordCreate,
    RentalRecordUpdate,
)


# ============================================================
# 设备变更自动记录（ADR-021）
# ============================================================

# 字段名 → 中文 label 映射（覆盖 RentalRecordUpdate 全部字段，未映射的 key 用原名）
FIELD_LABELS = {
    "machine_model": "机器型号",
    "cpu_model": "CPU型号",
    "memory_gb": "内存(GB)",
    "gpu_info": "GPU信息",
    "system_disk": "系统盘",
    "data_disks": "数据盘",
    "os_version": "操作系统版本",
    "bandwidth_mbps": "带宽(Mbps)",
    "machine_room_id": "所属机房",
    "rack_location": "机架位置",
    "rack_id": "机架",
    "u_position": "U位",
    "private_ip": "内网IP",
    "public_ips": "公网IP",
    "ssh_port": "SSH端口",
    "root_username": "root用户名",
    "root_password": "Root密码",
    "remark": "备注",
    "status": "设备状态",
}


def _serialize_diff_value(value):
    """diff 值序列化：date/datetime 转 ISO 字符串，空值保持 None（JSON null）"""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _build_change_diff(rental: RentalRecord, update_data: dict, password_changed: bool) -> list:
    """
    更新前逐字段 diff，只记录实际变化的字段。
    返回 [{"field": "内存(GB)", "old": 64, "new": 128}, ...]
    root_password 只记录脱敏的 "***"，不记录明文/密文。
    """
    diff = []
    for field, new_value in update_data.items():
        if field == "root_password_enc":
            # 密文不直接记录，统一由 password_changed 走脱敏条目
            continue
        old_value = getattr(rental, field, None)
        if old_value == new_value:
            continue
        diff.append({
            "field": FIELD_LABELS.get(field, field),
            "old": _serialize_diff_value(old_value),
            "new": _serialize_diff_value(new_value),
        })
    if password_changed:
        diff.append({"field": "Root密码", "old": "***", "new": "***"})
    return diff


def _ensure_machine_room_exists(db: Session, machine_room_id: int):
    """校验机房存在（machine_room_id 无硬 FK，写入前应用层校验）"""
    from src.machine_room.models import MachineRoom
    room = db.query(MachineRoom).filter(MachineRoom.id == machine_room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="所属机房不存在")
    return room


def _validate_rack_placement(
    db: Session,
    rack_id: Optional[int],
    u_position: Optional[int],
    machine_room_id: Optional[int],
    exclude_rental_id: Optional[str] = None,
):
    """
    机架 U 位占位校验（ADR-022）：
    - u_position 提供但 rack_id 为空 → 400
    - rack_id 不存在 → 404
    - 机架所属机房与设备 machine_room_id 不一致 → 400
    - u_position 超出 1~capacity_u → 400
    - 同机架同 U 位已被其他设备占用 → 409
    """
    if u_position is not None and rack_id is None:
        raise HTTPException(status_code=400, detail="指定 U 位时必须同时指定机架")

    if rack_id is None:
        return

    from src.machine_room.models import Rack
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机架不存在")

    if machine_room_id is not None and rack.machine_room_id != machine_room_id:
        raise HTTPException(
            status_code=400,
            detail=f"机架 {rack.name} 不属于设备所属机房，无法占位",
        )

    if u_position is not None:
        if not (1 <= u_position <= (rack.capacity_u or 0)):
            raise HTTPException(
                status_code=400,
                detail=f"U 位超出范围（机架 {rack.name} 容量为 {rack.capacity_u} U，有效范围 1~{rack.capacity_u}）",
            )
        # 唯一占用：同机架同 U 位只能有一台设备
        occ_query = db.query(RentalRecord).filter(
            RentalRecord.rack_id == rack_id,
            RentalRecord.u_position == u_position,
        )
        if exclude_rental_id is not None:
            occ_query = occ_query.filter(RentalRecord.id != exclude_rental_id)
        occupant = occ_query.first()
        if occupant:
            raise HTTPException(
                status_code=409,
                detail=f"机架 {rack.name} 的 U{u_position} 已被设备 {occupant.machine_model} 占用",
            )


def list_rentals(
    db: Session,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    private_ip: Optional[str] = None,
    public_ip: Optional[str] = None,
    rack_location: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    unlinked_only: bool = False,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    machine_room_id: Optional[int] = None,
    warehoused: bool = False,
    rack_id: Optional[int] = None,
) -> tuple[list[RentalRecord], int]:
    """查询租赁记录列表"""
    query = db.query(RentalRecord)

    if customer_id:
        query = query.filter(RentalRecord.customer_id == customer_id)
    if status:
        query = query.filter(RentalRecord.status == status)
    if rack_id is not None:
        query = query.filter(RentalRecord.rack_id == rack_id)
    if warehoused:
        # 未上架（未关联机房）设备，优先级高于 machine_room_id
        query = query.filter(RentalRecord.machine_room_id.is_(None))
    elif machine_room_id is not None:
        query = query.filter(RentalRecord.machine_room_id == machine_room_id)
    if search:
        query = query.filter(
            RentalRecord.machine_model.ilike(f"%{search}%")
        )
    if private_ip:
        query = query.filter(
            RentalRecord.private_ip.ilike(f"%{private_ip}%")
        )
    if public_ip:
        # public_ips 是 JSON 数组，用 cast(String) 转字符串后 LIKE 模糊匹配
        query = query.filter(
            RentalRecord.public_ips.cast(String).ilike(f"%{public_ip}%")
        )
    if rack_location:
        query = query.filter(
            RentalRecord.rack_location.ilike(f"%{rack_location}%")
        )

    if unlinked_only:
        # 过滤出未关联任何合同的设备（不在 contract_rental 表中）
        from src.contract.models import contract_rental
        from sqlalchemy import select
        subq = select(contract_rental.c.rental_id)
        query = query.filter(~RentalRecord.id.in_(subq))

    total = query.count()
    offset = (page - 1) * page_size

    SORT_WHITELIST = {
        'machine_model': RentalRecord.machine_model,
        'memory_gb': RentalRecord.memory_gb,
        'bandwidth_mbps': RentalRecord.bandwidth_mbps,
        'rack_location': RentalRecord.rack_location,
        'created_at': RentalRecord.created_at,
        'end_date': RentalRecord.end_date,
    }
    if sort_field and sort_field in SORT_WHITELIST:
        col = SORT_WHITELIST[sort_field]
        query = query.order_by(col.desc() if sort_order == 'desc' else col.asc())
    else:
        query = query.order_by(RentalRecord.created_at.desc())

    items = query.offset(offset).limit(page_size).all()
    return items, total


def get_rental(db: Session, rental_id: str) -> Optional[RentalRecord]:
    """根据 ID 获取租赁记录"""
    return db.query(RentalRecord).filter(RentalRecord.id == rental_id).first()


def create_rental(db: Session, data: RentalRecordCreate) -> RentalRecord:
    """创建租赁记录（纯硬件档案，客户/日期/计费从关联合同继承）"""
    # 处理密码加密
    root_password_enc = None
    if data.root_password:
        root_password_enc = encrypt_password(data.root_password)

    # data_disks 直接是字符串数组
    data_disks_json = data.data_disks

    # 校验所属机房存在（可空）
    if data.machine_room_id is not None:
        _ensure_machine_room_exists(db, data.machine_room_id)

    # 校验机架 U 位占位（ADR-022）
    _validate_rack_placement(
        db,
        rack_id=data.rack_id,
        u_position=data.u_position,
        machine_room_id=data.machine_room_id,
    )

    rental = RentalRecord(
        customer_id=None,  # 关联合同后自动设置
        machine_model=data.machine_model,
        cpu_model=data.cpu_model,
        memory_gb=data.memory_gb,
        gpu_info=data.gpu_info,
        system_disk=data.system_disk,
        data_disks=data_disks_json,
        os_version=data.os_version,
        bandwidth_mbps=data.bandwidth_mbps,
        machine_room_id=data.machine_room_id,
        rack_location=data.rack_location,
        rack_id=data.rack_id,
        u_position=data.u_position,
        private_ip=data.private_ip,
        public_ips=data.public_ips,
        ssh_port=data.ssh_port,
        root_username=data.root_username,
        root_password_enc=root_password_enc,
        remark=data.remark,
        status="空闲中",
    )
    db.add(rental)
    db.flush()

    db.commit()
    db.refresh(rental)
    return rental


def update_rental(db: Session, rental: RentalRecord, data: RentalRecordUpdate) -> RentalRecord:
    """全量更新租赁记录（纯硬件档案），有实际变化时自动写结构化 change_log（同事务）"""
    update_data = data.model_dump(exclude_unset=True)

    # 禁止人工将状态设为"租赁中"（租赁中只能由关联合同时系统自动设置）
    if "status" in update_data and update_data["status"] == "租赁中":
        from src.contract.models import contract_rental
        linked = db.query(contract_rental).filter(contract_rental.c.rental_id == rental.id).first()
        if not linked:
            raise HTTPException(status_code=422, detail="「租赁中」状态只能由关联合同时系统自动设置，不可手动选择")

    # 校验所属机房存在（可空，传 null 表示解绑）
    if update_data.get("machine_room_id") is not None:
        _ensure_machine_room_exists(db, update_data["machine_room_id"])

    # 机架 U 位占位校验（ADR-022）
    if "rack_id" in update_data and update_data["rack_id"] is None:
        # 解绑机架：u_position 必须同步置 null
        if update_data.get("u_position") is not None:
            raise HTTPException(status_code=400, detail="解绑机架时不能同时指定 U 位")
        update_data["u_position"] = None
    new_rack_id = update_data.get("rack_id", rental.rack_id)
    new_u = update_data.get("u_position", rental.u_position)
    # 有效机房：本次传了 machine_room_id 用新值，否则用设备当前值
    eff_room = update_data["machine_room_id"] if "machine_room_id" in update_data else rental.machine_room_id
    _validate_rack_placement(
        db,
        rack_id=new_rack_id,
        u_position=new_u,
        machine_room_id=eff_room,
        exclude_rental_id=rental.id,
    )

    # 处理密码加密（root_password 明文 → root_password_enc 密文）
    password_changed = "root_password" in update_data
    if password_changed:
        plain_password = update_data.pop("root_password")
        if plain_password:
            update_data["root_password_enc"] = encrypt_password(plain_password)

    # data_disks 直接是字符串数组
    if "data_disks" in update_data:
        update_data["data_disks"] = update_data["data_disks"] or None

    # 更新前逐字段 diff（只记录实际变化的字段）
    diff = _build_change_diff(rental, update_data, password_changed)

    # 更新字段
    for field, value in update_data.items():
        setattr(rental, field, value)

    # 有变化才写日志，与主更新同一 session 同一事务（失败一起回滚）
    if diff:
        from src.contract.models import ChangeLog
        db.add(ChangeLog(
            target_type="rental",
            target_id=rental.id,
            content=json.dumps(diff, ensure_ascii=False),
        ))

    db.commit()
    db.refresh(rental)
    return rental


def delete_rental(db: Session, rental: RentalRecord) -> RentalRecord:
    """删除租赁记录"""
    # 先删除中间表关联
    db.execute(
        rental_contact.delete().where(rental_contact.c.rental_id == rental.id)
    )
    db.delete(rental)
    db.commit()
    return rental


def _replace_rental_contacts(
    db: Session,
    rental_id: str,
    contacts: list,
):
    """
    全量替换租赁记录的联系人关联
    先删除旧关联，再插入新关联
    contacts 可以是 RentalContactCreate 对象列表或 dict 列表
    """
    # 删除旧关联
    db.execute(
        rental_contact.delete().where(rental_contact.c.rental_id == rental_id)
    )

    # 插入新关联
    for c in contacts:
        if hasattr(c, 'contact_id'):
            cid = c.contact_id
            rtype = c.recipient_type
        else:
            cid = c['contact_id']
            rtype = c.get('recipient_type', 'to')

        db.execute(
            rental_contact.insert().values(
                rental_id=rental_id,
                contact_id=cid,
                recipient_type=rtype,
            )
        )


def get_rental_contacts(db: Session, rental_id: str) -> list[dict]:
    """
    获取租赁记录关联的联系人详情
    返回: [{"contact_id": "...", "name": "...", "email": "...", "recipient_type": "to"}, ...]
    """
    from sqlalchemy import text

    rows = db.execute(
        text(
            "SELECT c.id, c.name, c.email, rc.recipient_type "
            "FROM rental_contact rc "
            "JOIN contact c ON rc.contact_id = c.id "
            "WHERE rc.rental_id = :rental_id"
        ),
        {"rental_id": rental_id},
    ).fetchall()

    contacts = []
    for row in rows:
        contacts.append({
            "contact_id": row[0],
            "name": row[1],
            "email": row[2],
            "recipient_type": row[3],
        })
    return contacts


def get_rental_email_logs(db: Session, rental_id: str, limit: int = 20):
    """获取租赁记录关联的邮件日志"""
    from src.mail.models import EmailLog
    return (
        db.query(EmailLog)
        .filter(EmailLog.rental_id == rental_id)
        .order_by(EmailLog.created_at.desc())
        .limit(limit)
        .all()
    )


def build_rental_context(db: Session, rental: RentalRecord) -> dict:
    """
    构建邮件模板渲染上下文（统一 rentals 数组结构）

    单条租赁记录包装为单元素 rentals 数组，与定时合并发送（N条）结构一致。
    模板变量: customer_name, rental_count, rentals (数组，元素字段如下)
    """
    # 距到期天数
    days_until_expiry = 0
    if rental.end_date:
        today = local_today()
        delta = rental.end_date - today
        days_until_expiry = delta.days

    # 联系人信息
    contacts_info = get_rental_contacts(db, rental.id)

    # 单条设备上下文
    rental_ctx = {
        "machine_model": rental.machine_model or "",
        "cpu_model": rental.cpu_model or "",
        "memory_gb": rental.memory_gb or "",
        "gpu_info": rental.gpu_info or "",
        "system_disk": rental.system_disk or "",
        "data_disks": rental.data_disks or [],
        "os_version": rental.os_version or "",
        "bandwidth_mbps": rental.bandwidth_mbps or "",
        "rack_location": rental.rack_location or "",
        "private_ip": rental.private_ip or "",
        "public_ips": rental.public_ips or [],
        "ssh_port": rental.ssh_port or 22,
        "root_username": rental.root_username or "root",
        "root_password": decrypt_password(rental.root_password_enc or ""),
        "billing_model": rental.billing_model or "monthly",
        "start_date": rental.start_date.isoformat() if rental.start_date else "",
        "end_date": rental.end_date.isoformat() if rental.end_date else "",
        "auto_renew": rental.auto_renew,
        "remark": rental.remark or "",
        "status": rental.status or "",
        "days_until_expiry": days_until_expiry,
        "contacts": contacts_info,
    }

    # 客户名称
    customer = rental.customer
    customer_name = customer.name if customer else ""

    # 统一结构：rentals 数组 + rental_count + customer_name
    return {
        "customer_name": customer_name,
        "rental_count": 1,
        "rentals": [rental_ctx],
    }
