"""
机房管理模块业务逻辑层

约定（ADR-021 / ADR-022）：
- machine_room_id / rack.machine_room_id 均无硬 FK，查询层保证归属
- 设备 U 位结构化（ADR-022）：点位图 u_cells 由 rack_id + u_position 驱动
- 存量兼容：rack_location 前缀匹配（如机架 "A-01" 匹配 "A-01-05-U12"）保留，
  仅用于 devices 摘要与机架删除保护等存量展示
"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.machine_room.models import MachineRoom, Rack
from src.machine_room import schemas
from src.rental.models import RentalRecord


# ============================================================
# MachineRoom
# ============================================================

def list_machine_rooms(db: Session, search: Optional[str] = None) -> list[MachineRoom]:
    """机房列表，支持 name/code 模糊搜索"""
    query = db.query(MachineRoom)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (MachineRoom.name.ilike(like)) | (MachineRoom.code.ilike(like))
        )
    return query.order_by(MachineRoom.id.asc()).all()


def get_machine_room(db: Session, room_id: int) -> Optional[MachineRoom]:
    return db.query(MachineRoom).filter(MachineRoom.id == room_id).first()


def _check_name_unique(db: Session, name: str, exclude_id: Optional[int] = None):
    query = db.query(MachineRoom).filter(MachineRoom.name == name)
    if exclude_id is not None:
        query = query.filter(MachineRoom.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"机房名称 '{name}' 已存在")


def _check_code_unique(db: Session, code: str, exclude_id: Optional[int] = None):
    query = db.query(MachineRoom).filter(MachineRoom.code == code)
    if exclude_id is not None:
        query = query.filter(MachineRoom.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"机房编码 '{code}' 已存在")


def create_machine_room(db: Session, data: schemas.MachineRoomCreate) -> MachineRoom:
    _check_name_unique(db, data.name)
    _check_code_unique(db, data.code)
    room = MachineRoom(
        name=data.name,
        code=data.code,
        address=data.address,
        note=data.note,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def update_machine_room(db: Session, room: MachineRoom, data: schemas.MachineRoomUpdate) -> MachineRoom:
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        _check_name_unique(db, update_data["name"], room.id)
    if "code" in update_data:
        _check_code_unique(db, update_data["code"], room.id)
    for field, value in update_data.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room


def delete_machine_room(db: Session, room: MachineRoom) -> None:
    """删除机房：有关联设备则 409 拒绝（软保护，不做级联）"""
    device_count = (
        db.query(RentalRecord)
        .filter(RentalRecord.machine_room_id == room.id)
        .count()
    )
    if device_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"机房下仍有 {device_count} 台关联设备，请先迁移或解绑设备后再删除",
        )
    # 同步删除该机房的机架（无硬 FK，手动清理）
    db.query(Rack).filter(Rack.machine_room_id == room.id).delete(synchronize_session=False)
    db.delete(room)
    db.commit()


# ============================================================
# Rack
# ============================================================

def get_rack(db: Session, rack_id: int) -> Optional[Rack]:
    return db.query(Rack).filter(Rack.id == rack_id).first()


def _get_rack_in_room(db: Session, room_id: int, rack_id: int) -> Rack:
    rack = get_rack(db, rack_id)
    if not rack or rack.machine_room_id != room_id:
        raise HTTPException(status_code=404, detail="机架不存在")
    return rack


def _check_rack_name_unique(
    db: Session, room_id: int, name: str, exclude_rack_id: Optional[int] = None
):
    query = db.query(Rack).filter(
        Rack.machine_room_id == room_id,
        Rack.name == name,
    )
    if exclude_rack_id is not None:
        query = query.filter(Rack.id != exclude_rack_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"机架名称 '{name}' 在该机房内已存在")


def create_rack(db: Session, room_id: int, data: schemas.RackCreate) -> Rack:
    room = get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    _check_rack_name_unique(db, room_id, data.name)
    rack = Rack(
        machine_room_id=room_id,
        name=data.name,
        capacity_u=data.capacity_u,
    )
    db.add(rack)
    db.commit()
    db.refresh(rack)
    return rack


def update_rack(db: Session, room_id: int, rack_id: int, data: schemas.RackUpdate) -> Rack:
    rack = _get_rack_in_room(db, room_id, rack_id)
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        _check_rack_name_unique(db, room_id, update_data["name"], rack.id)
    for field, value in update_data.items():
        setattr(rack, field, value)
    db.commit()
    db.refresh(rack)
    return rack


def count_rack_devices(db: Session, rack: Rack) -> int:
    """机架下设备数：同机房且 rack_location 以机架名为前缀"""
    return (
        db.query(RentalRecord)
        .filter(
            RentalRecord.machine_room_id == rack.machine_room_id,
            RentalRecord.rack_location.like(f"{rack.name}%"),
        )
        .count()
    )


def delete_rack(db: Session, room_id: int, rack_id: int) -> None:
    """删除机架：机架下仍有设备则 409 拒绝"""
    rack = _get_rack_in_room(db, room_id, rack_id)
    device_count = count_rack_devices(db, rack)
    if device_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"机架 {rack.name} 下仍有 {device_count} 台设备，请先迁移设备后再删除",
        )
    db.delete(rack)
    db.commit()


# ============================================================
# 点位图 / 未上架设备
# ============================================================

def _device_brief(rental: RentalRecord) -> schemas.RackDeviceBrief:
    return schemas.RackDeviceBrief(
        rental_id=rental.id,
        machine_model=rental.machine_model or "",
        rack_location=rental.rack_location,
        status=rental.status or "",
    )


def list_warehoused(db: Session) -> list[RentalRecord]:
    """未上架（machine_room_id IS NULL）设备列表"""
    return (
        db.query(RentalRecord)
        .filter(RentalRecord.machine_room_id.is_(None))
        .order_by(RentalRecord.created_at.desc())
        .all()
    )


def get_points(db: Session, room_id: int) -> dict:
    """机房点位图数据：机架卡片 + 每机架设备摘要 + 仓库未上架设备"""
    room = get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")

    racks = (
        db.query(Rack)
        .filter(Rack.machine_room_id == room_id)
        .order_by(Rack.name.asc())
        .all()
    )
    room_devices = (
        db.query(RentalRecord)
        .filter(RentalRecord.machine_room_id == room_id)
        .order_by(RentalRecord.rack_location.asc())
        .all()
    )

    # U 位网格（ADR-022）：按 rack_id + u_position 建索引，空格设备字段为 null
    u_index: dict[int, dict[int, RentalRecord]] = {}
    for d in room_devices:
        if d.rack_id is not None and d.u_position is not None:
            u_index.setdefault(d.rack_id, {})[d.u_position] = d

    rack_items = []
    for rack in racks:
        devices = [
            d for d in room_devices
            if d.rack_location and d.rack_location.startswith(rack.name)
        ]
        cells_by_u = u_index.get(rack.id, {})
        u_cells = []
        for u in range(1, (rack.capacity_u or 0) + 1):
            d = cells_by_u.get(u)
            if d is None:
                u_cells.append(schemas.RackCell(u=u))
            else:
                u_cells.append(schemas.RackCell(
                    u=u,
                    rental_id=d.id,
                    machine_model=d.machine_model,
                    remark=d.remark,
                    private_ip=d.private_ip,
                    status=d.status,
                ))
        rack_items.append(schemas.RackWithDevices(
            id=rack.id,
            name=rack.name,
            capacity_u=rack.capacity_u,
            u_cells=u_cells,
            devices=[_device_brief(d) for d in devices],
        ))

    return {
        "room": room,
        "racks": rack_items,
        "warehoused": [_device_brief(d) for d in list_warehoused(db)],
    }
