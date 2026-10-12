"""
机房管理模块 ORM 模型

MachineRoom - 机房
Rack        - 机架（点位图的最小结构化单元；ADR-022 起设备 U 位由
              RentalRecord.rack_id + u_position 结构化表达，
              rack_location 自由文本仅存量兼容保留）
"""
from sqlalchemy import Column, String, Integer, Text, DateTime

from src.core.database import Base
from src.core.timezone import local_now


class MachineRoom(Base):
    """机房"""
    __tablename__ = "machine_room"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="机房ID")
    name = Column(String(128), nullable=False, unique=True, comment="机房名称")
    code = Column(String(64), nullable=False, unique=True, comment="机房编码")
    address = Column(String(256), nullable=True, comment="机房地址")
    note = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=local_now, nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=local_now,
        onupdate=local_now,
        nullable=False,
        comment="更新时间",
    )

    def __repr__(self):
        return f"<MachineRoom(id={self.id}, name={self.name}, code={self.code})>"


class Rack(Base):
    """机架（机房内唯一命名，如 A-01）"""
    __tablename__ = "rack"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="机架ID")
    machine_room_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="所属机房ID（无硬 FK，指向 machine_room.id，查询层保证归属）",
    )
    name = Column(String(128), nullable=False, comment="机架名称（机房内唯一，如 A-01）")
    capacity_u = Column(Integer, default=42, comment="机架 U 位容量")
    created_at = Column(DateTime, default=local_now, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"<Rack(id={self.id}, machine_room_id={self.machine_room_id}, name={self.name})>"
