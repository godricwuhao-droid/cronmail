"""
租赁记录模块业务逻辑层
"""
from datetime import datetime, date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, String

from src.core.crypto import encrypt_password, decrypt_password
from src.rental.models import RentalRecord, rental_contact
from src.rental.schemas import (
    RentalRecordCreate,
    RentalRecordUpdate,
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
) -> tuple[list[RentalRecord], int]:
    """查询租赁记录列表"""
    query = db.query(RentalRecord)

    if customer_id:
        query = query.filter(RentalRecord.customer_id == customer_id)
    if status:
        query = query.filter(RentalRecord.status == status)
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
    items = query.order_by(RentalRecord.created_at.desc()).offset(offset).limit(page_size).all()
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

    # 处理 data_disks
    data_disks_json = None
    if data.data_disks:
        data_disks_json = [disk.model_dump() for disk in data.data_disks]

    rental = RentalRecord(
        customer_id=None,  # 关联合同后自动设置
        machine_model=data.machine_model,
        cpu_model=data.cpu_model,
        memory_gb=data.memory_gb,
        gpu_info=data.gpu_info,
        system_disk_gb=data.system_disk_gb,
        data_disks=data_disks_json,
        os_version=data.os_version,
        bandwidth_mbps=data.bandwidth_mbps,
        rack_location=data.rack_location,
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
    """全量更新租赁记录（纯硬件档案）"""
    update_data = data.model_dump(exclude_unset=True)

    # 禁止人工将状态设为"租赁中"（租赁中只能由关联合同时系统自动设置）
    if "status" in update_data and update_data["status"] == "租赁中":
        from src.contract.models import contract_rental
        linked = db.query(contract_rental).filter(contract_rental.c.rental_id == rental.id).first()
        if not linked:
            raise HTTPException(status_code=422, detail="「租赁中」状态只能由关联合同时系统自动设置，不可手动选择")

    # 处理密码加密
    if "root_password" in update_data:
        plain_password = update_data.pop("root_password")
        if plain_password:
            update_data["root_password_enc"] = encrypt_password(plain_password)

    # 处理 data_disks
    if "data_disks" in update_data:
        disks = update_data["data_disks"]
        if disks:
            update_data["data_disks"] = [
                disk if isinstance(disk, dict) else disk.model_dump()
                for disk in disks
            ]
        else:
            update_data["data_disks"] = None

    # 更新字段
    for field, value in update_data.items():
        setattr(rental, field, value)

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
        today = date.today()
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
        "system_disk_gb": rental.system_disk_gb or "",
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
