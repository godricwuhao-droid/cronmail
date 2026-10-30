"""
机房管理模块 API 路由（ADR-026：排→机柜→机架 三层）

路由结构：
- 机房：/api/machine-rooms（CRUD + warehoused）
- 排：  /api/machine-rooms/{room_id}/rows（CRUD）
- 机柜：/api/machine-rooms/{room_id}/rows/{row_id}/cabinets（GET/POST）
        /api/cabinets/{cabinet_id}（PUT/DELETE）
- 机架：/api/cabinets/{cabinet_id}/racks（GET/POST）
        /api/racks/{rack_id}（PUT/DELETE）
- 点位图：/api/machine-rooms/{room_id}/point-map
- 级联选择源：/api/machine-rooms/{room_id}/locations
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.machine_room import schemas, services

machine_room_router = APIRouter(prefix="/api/machine-rooms", tags=["MachineRoom"])
cabinet_router = APIRouter(prefix="/api/cabinets", tags=["Cabinet"])
rack_router = APIRouter(prefix="/api/racks", tags=["Rack"])


# ============================================================
# 机房 CRUD
# ============================================================

@machine_room_router.get("", response_model=schemas.MachineRoomListWrap)
def list_machine_rooms(
    search: Optional[str] = Query(None, description="按名称/编码模糊搜索"),
    db: Session = Depends(get_db),
):
    """机房列表（支持 name/code 模糊搜索）"""
    items = services.list_machine_rooms(db, search=search)
    return schemas.MachineRoomListWrap(items=items, total=len(items))


@machine_room_router.post("", response_model=schemas.MachineRoomResponse, status_code=201)
def create_machine_room(
    data: schemas.MachineRoomCreate,
    db: Session = Depends(get_db),
):
    """创建机房"""
    return services.create_machine_room(db, data)


# /warehoused 必须在 /{room_id} 之前注册，否则会被当作 room_id
@machine_room_router.get("/warehoused", response_model=schemas.WarehousedListWrap)
def list_warehoused(
    db: Session = Depends(get_db),
):
    """未上架（machine_room_id IS NULL）设备列表"""
    rentals = services.list_warehoused(db)
    items = [
        schemas.RackDeviceBrief(
            rental_id=r.id,
            machine_model=r.machine_model or "",
            rack_location=r.rack_location,
            private_ip=r.private_ip,
            status=r.status or "",
        )
        for r in rentals
    ]
    return schemas.WarehousedListWrap(items=items, total=len(items))


@machine_room_router.get("/{room_id}", response_model=schemas.MachineRoomResponse)
def get_machine_room(
    room_id: int,
    db: Session = Depends(get_db),
):
    """机房详情"""
    room = services.get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    return room


@machine_room_router.put("/{room_id}", response_model=schemas.MachineRoomResponse)
def update_machine_room(
    room_id: int,
    data: schemas.MachineRoomUpdate,
    db: Session = Depends(get_db),
):
    """更新机房（所有字段可选，只更新传入的字段）"""
    room = services.get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    return services.update_machine_room(db, room, data)


@machine_room_router.delete("/{room_id}", response_model=dict)
def delete_machine_room(
    room_id: int,
    db: Session = Depends(get_db),
):
    """删除机房（有机房设备则 409 拒绝；排/机柜/机架随机房一并删除）"""
    room = services.get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    services.delete_machine_room(db, room)
    return {"detail": "机房已删除"}


# ============================================================
# 排 CRUD
# ============================================================

@machine_room_router.get("/{room_id}/rows", response_model=schemas.RackRowListWrap)
def list_rack_rows(
    room_id: int,
    db: Session = Depends(get_db),
):
    """排列表（按排名升序）"""
    if not services.get_machine_room(db, room_id):
        raise HTTPException(status_code=404, detail="机房不存在")
    items = services.list_rack_rows(db, room_id)
    return schemas.RackRowListWrap(items=items, total=len(items))


@machine_room_router.post("/{room_id}/rows", response_model=schemas.RackRowResponse, status_code=201)
def create_rack_row(
    room_id: int,
    data: schemas.RackRowCreate,
    db: Session = Depends(get_db),
):
    """创建排（排名机房内唯一）"""
    return services.create_rack_row(db, room_id, data)


@machine_room_router.put("/{room_id}/rows/{row_id}", response_model=schemas.RackRowResponse)
def update_rack_row(
    room_id: int,
    row_id: int,
    data: schemas.RackRowUpdate,
    db: Session = Depends(get_db),
):
    """更新排（name/note 可选，只更新传入的字段）"""
    return services.update_rack_row(db, room_id, row_id, data)


@machine_room_router.delete("/{room_id}/rows/{row_id}", response_model=dict)
def delete_rack_row(
    room_id: int,
    row_id: int,
    db: Session = Depends(get_db),
):
    """删除排（排下仍有机柜则 409 拒绝）"""
    services.delete_rack_row(db, room_id, row_id)
    return {"detail": "排已删除"}


# ============================================================
# 机柜 CRUD（GET/POST 挂在排下，PUT/DELETE 独立路径，ADR-026）
# ============================================================

@machine_room_router.get("/{room_id}/rows/{row_id}/cabinets", response_model=schemas.CabinetListWrap)
def list_cabinets(
    room_id: int,
    row_id: int,
    db: Session = Depends(get_db),
):
    """排下机柜列表（按柜名升序）"""
    if not services.get_machine_room(db, room_id):
        raise HTTPException(status_code=404, detail="机房不存在")
    services._get_row_in_room(db, room_id, row_id)
    items = services.list_cabinets(db, row_id)
    return schemas.CabinetListWrap(items=items, total=len(items))


@machine_room_router.post("/{room_id}/rows/{row_id}/cabinets", response_model=schemas.CabinetResponse, status_code=201)
def create_cabinet(
    room_id: int,
    row_id: int,
    data: schemas.CabinetCreate,
    db: Session = Depends(get_db),
):
    """创建机柜（柜名排内唯一，power_on 默认 true）"""
    if not services.get_machine_room(db, room_id):
        raise HTTPException(status_code=404, detail="机房不存在")
    services._get_row_in_room(db, room_id, row_id)
    return services.create_cabinet(db, row_id, data)


@cabinet_router.put("/{cabinet_id}", response_model=schemas.CabinetResponse)
def update_cabinet(
    cabinet_id: int,
    data: schemas.CabinetUpdate,
    db: Session = Depends(get_db),
):
    """更新机柜（name/power_on 可选，只更新传入的字段）"""
    return services.update_cabinet(db, cabinet_id, data)


@cabinet_router.delete("/{cabinet_id}", response_model=dict)
def delete_cabinet(
    cabinet_id: int,
    db: Session = Depends(get_db),
):
    """删除机柜（机柜下仍有机架则 409 拒绝）"""
    services.delete_cabinet(db, cabinet_id)
    return {"detail": "机柜已删除"}


# ============================================================
# 机架 CRUD（GET/POST 挂在机柜下，PUT/DELETE 独立路径，ADR-026）
# ============================================================

@cabinet_router.get("/{cabinet_id}/racks", response_model=schemas.RackListWrap)
def list_racks(
    cabinet_id: int,
    db: Session = Depends(get_db),
):
    """机柜下机架列表（按机架名升序）"""
    cabinet = services.get_cabinet(db, cabinet_id)
    if not cabinet:
        raise HTTPException(status_code=404, detail="机柜不存在")
    items = services.list_racks(db, cabinet_id)
    return schemas.RackListWrap(items=items, total=len(items))


@cabinet_router.post("/{cabinet_id}/racks", response_model=schemas.RackResponse, status_code=201)
def create_rack(
    cabinet_id: int,
    data: schemas.RackCreate,
    db: Session = Depends(get_db),
):
    """创建机架（机架名机柜内唯一）"""
    return services.create_rack(db, cabinet_id, data)


@rack_router.put("/{rack_id}", response_model=schemas.RackResponse)
def update_rack(
    rack_id: int,
    data: schemas.RackUpdate,
    db: Session = Depends(get_db),
):
    """更新机架（仅 capacity_u 可改，只更新传入的字段；机架名只读）"""
    return services.update_rack(db, rack_id, data)


@rack_router.delete("/{rack_id}", response_model=dict)
def delete_rack(
    rack_id: int,
    db: Session = Depends(get_db),
):
    """删除机架（机架下仍有设备则 409 拒绝）"""
    services.delete_rack(db, rack_id)
    return {"detail": "机架已删除"}


# ============================================================
# 点位图 / 级联选择源
# ============================================================

@machine_room_router.get("/{room_id}/point-map", response_model=schemas.MachineRoomPointMapResponse)
def get_machine_room_point_map(
    room_id: int,
    db: Session = Depends(get_db),
):
    """机房点位图数据（ADR-026）：rows→cabinets→racks→u_cells 嵌套 + warehoused + unlocated"""
    return services.get_point_map(db, room_id)


@machine_room_router.get("/{room_id}/locations", response_model=schemas.MachineRoomLocationsResponse)
def get_machine_room_locations(
    room_id: int,
    db: Session = Depends(get_db),
):
    """级联选择源（设备表单用，轻量版，ADR-026）：rows → cabinets → racks"""
    return services.get_locations(db, room_id)
