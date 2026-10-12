"""
机房管理模块 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.machine_room import schemas, services

machine_room_router = APIRouter(prefix="/api/machine-rooms", tags=["MachineRoom"])


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
    """删除机房（有机房设备则 409 拒绝）"""
    room = services.get_machine_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    services.delete_machine_room(db, room)
    return {"detail": "机房已删除"}


# ============================================================
# 点位图
# ============================================================

@machine_room_router.get("/{room_id}/points", response_model=schemas.MachineRoomPointsResponse)
def get_machine_room_points(
    room_id: int,
    db: Session = Depends(get_db),
):
    """机房点位图数据：机架卡片（含每机架设备摘要）+ 仓库未上架设备"""
    return services.get_points(db, room_id)


# ============================================================
# 机架 CRUD
# ============================================================

@machine_room_router.post("/{room_id}/racks", response_model=schemas.RackResponse, status_code=201)
def create_rack(
    room_id: int,
    data: schemas.RackCreate,
    db: Session = Depends(get_db),
):
    """创建机架"""
    return services.create_rack(db, room_id, data)


@machine_room_router.put("/{room_id}/racks/{rack_id}", response_model=schemas.RackResponse)
def update_rack(
    room_id: int,
    rack_id: int,
    data: schemas.RackUpdate,
    db: Session = Depends(get_db),
):
    """更新机架（所有字段可选，只更新传入的字段）"""
    return services.update_rack(db, room_id, rack_id, data)


@machine_room_router.delete("/{room_id}/racks/{rack_id}", response_model=dict)
def delete_rack(
    room_id: int,
    rack_id: int,
    db: Session = Depends(get_db),
):
    """删除机架（机架下仍有设备则 409 拒绝）"""
    services.delete_rack(db, room_id, rack_id)
    return {"detail": "机架已删除"}
