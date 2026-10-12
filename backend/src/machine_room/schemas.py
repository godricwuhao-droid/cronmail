"""
机房管理模块 Pydantic Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# MachineRoom
# ============================================================

class MachineRoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="机房名称")
    code: str = Field(..., min_length=1, max_length=64, description="机房编码")
    address: Optional[str] = Field(None, max_length=256, description="机房地址")
    note: Optional[str] = Field(None, description="备注")


class MachineRoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    address: Optional[str] = Field(None, max_length=256)
    note: Optional[str] = None


class MachineRoomResponse(BaseModel):
    id: int
    name: str
    code: str
    address: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MachineRoomListWrap(BaseModel):
    items: list[MachineRoomResponse]
    total: int


# ============================================================
# Rack
# ============================================================

class RackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="机架名称（机房内唯一，如 A-01）")
    capacity_u: int = Field(42, ge=1, description="机架 U 位容量")


class RackUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    capacity_u: Optional[int] = Field(None, ge=1)


class RackResponse(BaseModel):
    id: int
    machine_room_id: Optional[int] = None
    name: str
    capacity_u: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================================
# 点位图 / 未上架设备
# ============================================================

class RackDeviceBrief(BaseModel):
    """设备摘要（点位图卡片 / 仓库列表共用）"""
    rental_id: str
    machine_model: str
    rack_location: Optional[str] = None
    status: str


class RackCell(BaseModel):
    """U 位格子（ADR-022 点阵图）：u 从 1 开始，空格设备字段为 null"""
    u: int
    rental_id: Optional[str] = None
    machine_model: Optional[str] = None
    remark: Optional[str] = None
    private_ip: Optional[str] = None
    status: Optional[str] = None


class RackWithDevices(BaseModel):
    """机架卡片：机架信息 + U 位网格（u_cells）+ 卡上设备摘要（devices，存量前缀匹配保留）"""
    id: int
    name: str
    capacity_u: int
    u_cells: list[RackCell] = []
    devices: list[RackDeviceBrief] = []


class MachineRoomPointsResponse(BaseModel):
    """机房点位图数据"""
    room: MachineRoomResponse
    racks: list[RackWithDevices] = []
    warehoused: list[RackDeviceBrief] = []


class WarehousedListWrap(BaseModel):
    """未上架（machine_room_id IS NULL）设备列表"""
    items: list[RackDeviceBrief]
    total: int
