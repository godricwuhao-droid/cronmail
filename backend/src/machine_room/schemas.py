"""
机房管理模块 Pydantic Schema（ADR-026：排→机柜→机架 三层）
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
# RackRow（排，ADR-026）
# ============================================================

class RackRowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="排名称（机房内唯一，如 A排）")
    note: Optional[str] = Field(None, description="备注")


class RackRowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    note: Optional[str] = None


class RackRowResponse(BaseModel):
    id: int
    machine_room_id: Optional[int] = None
    name: str
    note: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RackRowListWrap(BaseModel):
    items: list[RackRowResponse]
    total: int


# ============================================================
# Cabinet（机柜，ADR-026）
# ============================================================

class CabinetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="机柜名称（排内唯一，如 A01）")
    power_on: bool = Field(True, description="通电状态（true=通电, false=未通电，默认通电）")


class CabinetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    power_on: Optional[bool] = Field(None, description="通电状态（true=通电, false=未通电）")


class CabinetResponse(BaseModel):
    id: int
    rack_row_id: Optional[int] = None
    name: str
    power_on: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CabinetListWrap(BaseModel):
    items: list[CabinetResponse]
    total: int


# ============================================================
# Rack（机架，ADR-026）
# ============================================================

class RackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="机架名称（机柜内唯一，如 A01-42U）")
    capacity_u: int = Field(42, ge=1, description="机架 U 位容量")


class RackUpdate(BaseModel):
    """更新机架：仅 capacity_u 可改，机架名只读（沿用 ADR-023 风格；power_on 已上移机柜，ADR-026）"""
    capacity_u: Optional[int] = Field(None, ge=1)


class RackResponse(BaseModel):
    id: int
    machine_room_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    name: str
    capacity_u: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RackListWrap(BaseModel):
    items: list[RackResponse]
    total: int


# ============================================================
# 点位图 / 未上架设备
# ============================================================

class RackDeviceBrief(BaseModel):
    """设备摘要（点位图 / 仓库列表 / 未定位设备共用，ADR-024）"""
    rental_id: str
    machine_model: str
    rack_location: Optional[str] = None
    private_ip: Optional[str] = None
    status: str


class RackCell(BaseModel):
    """U 位格子（ADR-022 点阵图）：u 从 1 开始，空格设备字段为 null"""
    u: int
    rental_id: Optional[str] = None
    machine_model: Optional[str] = None
    remark: Optional[str] = None
    private_ip: Optional[str] = None
    status: Optional[str] = None


class PointMapRack(BaseModel):
    """点位图机架节点：机架信息 + U 位网格（u_cells）"""
    id: int
    name: str
    capacity_u: int
    u_cells: list[RackCell] = []


class PointMapCabinet(BaseModel):
    """点位图机柜节点：机柜信息 + 电源状态 + 机架列表"""
    id: int
    name: str
    power_on: bool
    racks: list[PointMapRack] = []


class PointMapRow(BaseModel):
    """点位图排节点：排信息 + 机柜列表"""
    id: int
    name: str
    note: Optional[str] = None
    cabinets: list[PointMapCabinet] = []


class MachineRoomPointMapResponse(BaseModel):
    """机房点位图数据（ADR-026：rows→cabinets→racks→u_cells 嵌套）"""
    room: MachineRoomResponse
    rows: list[PointMapRow] = []
    warehoused: list[RackDeviceBrief] = []
    unlocated: list[RackDeviceBrief] = []  # 在架但未定位 U（rack_id 有值、u_position 为 NULL，ADR-024）


class WarehousedListWrap(BaseModel):
    """未上架（machine_room_id IS NULL）设备列表"""
    items: list[RackDeviceBrief]
    total: int


# ============================================================
# 级联选择源（设备表单用，轻量版，ADR-026）
# ============================================================

class LocationRack(BaseModel):
    id: int
    name: str
    capacity_u: int


class LocationCabinet(BaseModel):
    id: int
    name: str
    racks: list[LocationRack] = []


class LocationRow(BaseModel):
    id: int
    name: str
    cabinets: list[LocationCabinet] = []


class MachineRoomLocationsResponse(BaseModel):
    """级联选择源：rows → cabinets → racks（仅 id/name/capacity_u）"""
    rows: list[LocationRow] = []
