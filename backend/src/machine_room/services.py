"""
机房管理模块业务逻辑层（ADR-026：机房 → 排 → 机柜 → 机架 四级）

约定：
- machine_room_id / rack_row.machine_room_id / cabinet.rack_row_id /
  rack.cabinet_id 均无硬 FK，查询层保证归属
- 归属链：rack.cabinet_id → cabinet.rack_row_id → rack_row.machine_room_id；
  rack.machine_room_id 由迁移脚本保证一致，查询层以 cabinet 归属为准
- 设备 U 位结构化（ADR-022）：点位图 u_cells 由 rack_id + u_position 驱动
- 多 U 设备（ADR-028）：u_size 设备的区间 [u_position, u_position+u_size-1] 内每个 U 格
  均标记该设备（结构不变，前端按 rental_id 连续格合并渲染）
- 存量兼容：rack_location 前缀匹配仅用于机架删除保护（ADR-024 双条件）
- 未定位 U 设备（ADR-024）：point-map 响应含 unlocated（rack_id 有值、u_position 为 NULL）
"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from src.machine_room.models import MachineRoom, RackRow, Cabinet, Rack
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
    # 同步删除该机房的机架/机柜/排（无硬 FK，手动清理，自下而上）
    db.query(Rack).filter(Rack.machine_room_id == room.id).delete(synchronize_session=False)
    db.query(Cabinet).filter(Cabinet.rack_row_id.in_(
        db.query(RackRow.id).filter(RackRow.machine_room_id == room.id)
    )).delete(synchronize_session=False)
    db.query(RackRow).filter(RackRow.machine_room_id == room.id).delete(synchronize_session=False)
    db.delete(room)
    db.commit()


# ============================================================
# RackRow（排，ADR-026）
# ============================================================

def list_rack_rows(db: Session, room_id: int) -> list[RackRow]:
    return (
        db.query(RackRow)
        .filter(RackRow.machine_room_id == room_id)
        .order_by(RackRow.name.asc())
        .all()
    )


def get_rack_row(db: Session, row_id: int) -> Optional[RackRow]:
    return db.query(RackRow).filter(RackRow.id == row_id).first()


def _get_row_in_room(db: Session, room_id: int, row_id: int) -> RackRow:
    row = get_rack_row(db, row_id)
    if not row or row.machine_room_id != room_id:
        raise HTTPException(status_code=404, detail="排不存在")
    return row


def _check_row_name_unique(
    db: Session, room_id: int, name: str, exclude_row_id: Optional[int] = None
):
    query = db.query(RackRow).filter(
        RackRow.machine_room_id == room_id,
        RackRow.name == name,
    )
    if exclude_row_id is not None:
        query = query.filter(RackRow.id != exclude_row_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"排名称 '{name}' 在该机房内已存在")


def create_rack_row(db: Session, room_id: int, data: schemas.RackRowCreate) -> RackRow:
    room = get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    _check_row_name_unique(db, room_id, data.name)
    row = RackRow(machine_room_id=room_id, name=data.name, note=data.note)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_rack_row(db: Session, room_id: int, row_id: int, data: schemas.RackRowUpdate) -> RackRow:
    row = _get_row_in_room(db, room_id, row_id)
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        _check_row_name_unique(db, room_id, update_data["name"], row.id)
    for field, value in update_data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def count_row_cabinets(db: Session, row: RackRow) -> int:
    return db.query(Cabinet).filter(Cabinet.rack_row_id == row.id).count()


def delete_rack_row(db: Session, room_id: int, row_id: int) -> None:
    """删除排：排下仍有机柜则 409 拒绝"""
    row = _get_row_in_room(db, room_id, row_id)
    cabinet_count = count_row_cabinets(db, row)
    if cabinet_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"排 {row.name} 下仍有 {cabinet_count} 个机柜，请先迁移或删除机柜后再删除",
        )
    db.delete(row)
    db.commit()


# ============================================================
# Cabinet（机柜，ADR-026）
# ============================================================

def list_cabinets(db: Session, row_id: int) -> list[Cabinet]:
    return (
        db.query(Cabinet)
        .filter(Cabinet.rack_row_id == row_id)
        .order_by(Cabinet.name.asc())
        .all()
    )


def get_cabinet(db: Session, cabinet_id: int) -> Optional[Cabinet]:
    return db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()


def _get_cabinet_in_row(db: Session, row_id: int, cabinet_id: int) -> Cabinet:
    cabinet = get_cabinet(db, cabinet_id)
    if not cabinet or cabinet.rack_row_id != row_id:
        raise HTTPException(status_code=404, detail="机柜不存在")
    return cabinet


def _get_row_of_cabinet(db: Session, cabinet: Cabinet) -> RackRow:
    """机柜所属排（不存在则 404）"""
    row = get_rack_row(db, cabinet.rack_row_id) if cabinet.rack_row_id is not None else None
    if not row:
        raise HTTPException(status_code=404, detail="机柜所属排不存在")
    return row


def _check_cabinet_name_unique(
    db: Session, row_id: int, name: str, exclude_cabinet_id: Optional[int] = None
):
    query = db.query(Cabinet).filter(
        Cabinet.rack_row_id == row_id,
        Cabinet.name == name,
    )
    if exclude_cabinet_id is not None:
        query = query.filter(Cabinet.id != exclude_cabinet_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"机柜名称 '{name}' 在该排内已存在")


def create_cabinet(db: Session, row_id: int, data: schemas.CabinetCreate) -> Cabinet:
    row = get_rack_row(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="排不存在")
    _check_cabinet_name_unique(db, row_id, data.name)
    cabinet = Cabinet(
        rack_row_id=row_id,
        name=data.name,
        power_on=data.power_on,
    )
    db.add(cabinet)
    db.commit()
    db.refresh(cabinet)
    return cabinet


def update_cabinet(db: Session, cabinet_id: int, data: schemas.CabinetUpdate) -> Cabinet:
    cabinet = get_cabinet(db, cabinet_id)
    if not cabinet:
        raise HTTPException(status_code=404, detail="机柜不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        _check_cabinet_name_unique(db, cabinet.rack_row_id, update_data["name"], cabinet.id)
    for field, value in update_data.items():
        setattr(cabinet, field, value)
    db.commit()
    db.refresh(cabinet)
    return cabinet


def count_cabinet_racks(db: Session, cabinet: Cabinet) -> int:
    return db.query(Rack).filter(Rack.cabinet_id == cabinet.id).count()


def delete_cabinet(db: Session, cabinet_id: int) -> None:
    """删除机柜：机柜下仍有机架则 409 拒绝"""
    cabinet = get_cabinet(db, cabinet_id)
    if not cabinet:
        raise HTTPException(status_code=404, detail="机柜不存在")
    rack_count = count_cabinet_racks(db, cabinet)
    if rack_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"机柜 {cabinet.name} 下仍有 {rack_count} 个机架，请先迁移或删除机架后再删除",
        )
    db.delete(cabinet)
    db.commit()


# ============================================================
# Rack（机架，ADR-026）
# ============================================================

def get_rack(db: Session, rack_id: int) -> Optional[Rack]:
    return db.query(Rack).filter(Rack.id == rack_id).first()


def list_racks(db: Session, cabinet_id: int) -> list[Rack]:
    return (
        db.query(Rack)
        .filter(Rack.cabinet_id == cabinet_id)
        .order_by(Rack.name.asc())
        .all()
    )


def _check_rack_name_unique(
    db: Session, cabinet_id: int, name: str, exclude_rack_id: Optional[int] = None
):
    query = db.query(Rack).filter(
        Rack.cabinet_id == cabinet_id,
        Rack.name == name,
    )
    if exclude_rack_id is not None:
        query = query.filter(Rack.id != exclude_rack_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"机架名称 '{name}' 在该机柜内已存在")


def create_rack(db: Session, cabinet_id: int, data: schemas.RackCreate) -> Rack:
    cabinet = get_cabinet(db, cabinet_id)
    if not cabinet:
        raise HTTPException(status_code=404, detail="机柜不存在")
    row = _get_row_of_cabinet(db, cabinet)
    _check_rack_name_unique(db, cabinet_id, data.name)
    rack = Rack(
        machine_room_id=row.machine_room_id,
        cabinet_id=cabinet_id,
        name=data.name,
        capacity_u=data.capacity_u,
    )
    db.add(rack)
    db.commit()
    db.refresh(rack)
    return rack


def _check_capacity_shrink(db: Session, rack: Rack, new_capacity: Optional[int]) -> None:
    """容量收缩校验（ADR-029）：
    新容量 < 该机架已定位设备（u_position 非空）的最大占用上端 max(u_position + u_size - 1) → 400；
    扩大容量不设限，无已定位设备时不限制"""
    if new_capacity is None:
        return
    max_top = (
        db.query(func.coalesce(func.max(
            RentalRecord.u_position + func.coalesce(RentalRecord.u_size, 1) - 1
        ), 0))
        .filter(
            RentalRecord.rack_id == rack.id,
            RentalRecord.u_position.isnot(None),
        )
        .scalar()
    )
    if new_capacity < max_top:
        raise HTTPException(
            status_code=400,
            detail=f"机架容量不能小于已占用的最大 U 位（U{max_top}）",
        )


def update_rack(db: Session, rack_id: int, data: schemas.RackUpdate) -> Rack:
    """更新机架：仅 capacity_u 可改，机架名只读（沿用 ADR-023 风格）；
    容量收缩到已占用 U 位之下 → 400（ADR-029）"""
    rack = get_rack(db, rack_id)
    if not rack:
        raise HTTPException(status_code=404, detail="机架不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "capacity_u" in update_data:
        _check_capacity_shrink(db, rack, update_data["capacity_u"])
    for field, value in update_data.items():
        setattr(rack, field, value)
    db.commit()
    db.refresh(rack)
    return rack


def count_rack_devices(db: Session, rack: Rack) -> int:
    """机架下设备数（ADR-024 双条件）：
    rack_id 指向该机架（结构化，新数据），或 同机房且 rack_location 以机架名为前缀（存量兼容）"""
    return (
        db.query(RentalRecord)
        .filter(
            or_(
                RentalRecord.rack_id == rack.id,
                and_(
                    RentalRecord.machine_room_id == rack.machine_room_id,
                    RentalRecord.rack_location.like(f"{rack.name}%"),
                ),
            )
        )
        .count()
    )


def delete_rack(db: Session, rack_id: int) -> None:
    """删除机架：rack_id 指向该机架或前缀匹配到设备则 409 拒绝（ADR-024 或条件）"""
    rack = get_rack(db, rack_id)
    if not rack:
        raise HTTPException(status_code=404, detail="机架不存在")
    device_count = count_rack_devices(db, rack)
    if device_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"机架 {rack.name} 下仍有 {device_count} 台设备，请先迁移设备后再删除",
        )
    db.delete(rack)
    db.commit()


# ============================================================
# 点位图 / 级联选择源 / 未上架设备
# ============================================================

def _device_brief(rental: RentalRecord) -> schemas.RackDeviceBrief:
    return schemas.RackDeviceBrief(
        rental_id=rental.id,
        machine_model=rental.machine_model or "",
        rack_location=rental.rack_location,
        private_ip=rental.private_ip,
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


def _load_room_hierarchy(db: Session, room_id: int):
    """加载机房下 排→机柜→机架 三层（按名称升序）"""
    rows = (
        db.query(RackRow)
        .filter(RackRow.machine_room_id == room_id)
        .order_by(RackRow.name.asc())
        .all()
    )
    row_ids = [r.id for r in rows]
    cabinets = (
        db.query(Cabinet)
        .filter(Cabinet.rack_row_id.in_(row_ids))
        .order_by(Cabinet.name.asc())
        .all()
        if row_ids else []
    )
    cabinet_ids = [c.id for c in cabinets]
    racks = (
        db.query(Rack)
        .filter(Rack.cabinet_id.in_(cabinet_ids))
        .order_by(Rack.name.asc())
        .all()
        if cabinet_ids else []
    )
    cabinets_by_row: dict[Optional[int], list[Cabinet]] = {}
    for c in cabinets:
        cabinets_by_row.setdefault(c.rack_row_id, []).append(c)
    racks_by_cabinet: dict[Optional[int], list[Rack]] = {}
    for r in racks:
        racks_by_cabinet.setdefault(r.cabinet_id, []).append(r)
    return rows, cabinets_by_row, racks_by_cabinet


def _build_u_cells(rack: Rack, cells_by_u: dict[int, RentalRecord]) -> list[schemas.RackCell]:
    """U 位网格（ADR-022）：长度 = capacity_u，u 从 1 开始，空格设备字段为 null"""
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
    return u_cells


def get_point_map(db: Session, room_id: int) -> dict:
    """机房点位图数据（ADR-026）：rows→cabinets→racks→u_cells 嵌套 + 仓库未上架 + 未定位 U 设备"""
    room = get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")

    rows, cabinets_by_row, racks_by_cabinet = _load_room_hierarchy(db, room_id)
    room_devices = (
        db.query(RentalRecord)
        .filter(RentalRecord.machine_room_id == room_id)
        .order_by(RentalRecord.rack_location.asc())
        .all()
    )

    # U 位网格（ADR-022 / ADR-028）：按 rack_id + u_position 建索引；
    # 多 U 设备（u_size）区间内每个 U 格均标记该设备
    u_index: dict[int, dict[int, RentalRecord]] = {}
    for d in room_devices:
        if d.rack_id is not None and d.u_position is not None:
            size = d.u_size or 1
            for u in range(d.u_position, d.u_position + size):
                u_index.setdefault(d.rack_id, {})[u] = d

    row_items = []
    for row in rows:
        cabinet_items = []
        for cabinet in cabinets_by_row.get(row.id, []):
            rack_items = [
                schemas.PointMapRack(
                    id=rack.id,
                    name=rack.name,
                    capacity_u=rack.capacity_u,
                    u_cells=_build_u_cells(rack, u_index.get(rack.id, {})),
                )
                for rack in racks_by_cabinet.get(cabinet.id, [])
            ]
            cabinet_items.append(schemas.PointMapCabinet(
                id=cabinet.id,
                name=cabinet.name,
                power_on=cabinet.power_on,
                racks=rack_items,
            ))
        row_items.append(schemas.PointMapRow(
            id=row.id,
            name=row.name,
            note=row.note,
            cabinets=cabinet_items,
        ))

    # 未定位 U 设备（ADR-024）：在架（rack_id 有值）但未指定 U 位（u_position 为 NULL）
    unlocated = [
        d for d in room_devices
        if d.rack_id is not None and d.u_position is None
    ]

    return {
        "room": room,
        "rows": row_items,
        "warehoused": [_device_brief(d) for d in list_warehoused(db)],
        "unlocated": [_device_brief(d) for d in unlocated],
    }


def get_locations(db: Session, room_id: int) -> dict:
    """级联选择源（设备表单用，轻量版，ADR-026）：rows → cabinets → racks"""
    room = get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")

    rows, cabinets_by_row, racks_by_cabinet = _load_room_hierarchy(db, room_id)
    row_items = [
        schemas.LocationRow(
            id=row.id,
            name=row.name,
            cabinets=[
                schemas.LocationCabinet(
                    id=cabinet.id,
                    name=cabinet.name,
                    racks=[
                        schemas.LocationRack(
                            id=rack.id,
                            name=rack.name,
                            capacity_u=rack.capacity_u,
                        )
                        for rack in racks_by_cabinet.get(cabinet.id, [])
                    ],
                )
                for cabinet in cabinets_by_row.get(row.id, [])
            ],
        )
        for row in rows
    ]
    return {"rows": row_items}
