"""
机房管理模块 ORM 模型

MachineRoom - 机房
RackRow     - 排（如 A排，ADR-026）
Cabinet     - 机柜（如 A01，电源状态归此层，ADR-026）
Rack        - 机架（点位图的最小结构化单元；ADR-022 起设备 U 位由
              RentalRecord.rack_id + u_position 结构化表达，
              rack_location 自由文本仅存量兼容保留）

层级（ADR-026）：机房 → 排 → 机柜 → 机架 → 设备
所有层级归属均无硬 FK（模块现有风格），查询层保证归属。
"""
from sqlalchemy import Boolean, Column, String, Integer, Text, DateTime

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


class RackRow(Base):
    """排（机房内唯一命名，如 A排，ADR-026）"""
    __tablename__ = "rack_row"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="排ID")
    machine_room_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="所属机房ID（无硬 FK，指向 machine_room.id，查询层保证归属）",
    )
    name = Column(String(128), nullable=False, comment="排名称（机房内唯一，如 A排）")
    note = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=local_now, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"<RackRow(id={self.id}, machine_room_id={self.machine_room_id}, name={self.name})>"


class Cabinet(Base):
    """机柜（排内唯一命名，如 A01；电源状态归机柜层，ADR-026）"""
    __tablename__ = "cabinet"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="机柜ID")
    rack_row_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="所属排ID（无硬 FK，指向 rack_row.id，查询层保证归属）",
    )
    name = Column(String(128), nullable=False, comment="机柜名称（排内唯一，如 A01）")
    power_on = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="通电状态（true=通电, false=未通电；ADR-026 自 rack.power_on 上移）",
    )
    created_at = Column(DateTime, default=local_now, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"<Cabinet(id={self.id}, rack_row_id={self.rack_row_id}, name={self.name})>"


class Rack(Base):
    """机架（机柜内唯一命名，如 A01-42U；点位图最小结构化单元）"""
    __tablename__ = "rack"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="机架ID")
    machine_room_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="所属机房ID（无硬 FK，指向 machine_room.id；迁移脚本保证与 cabinet→row→room 一致，查询层以 cabinet 归属为准，ADR-026）",
    )
    cabinet_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="所属机柜ID（无硬 FK，指向 cabinet.id，ADR-026）",
    )
    name = Column(String(128), nullable=False, comment="机架名称（机柜内唯一，如 A01-42U）")
    capacity_u = Column(Integer, default=42, comment="机架 U 位容量")
    created_at = Column(DateTime, default=local_now, nullable=False, comment="创建时间")
    # 注：power_on 已上移 cabinet（ADR-026）；DB 存量列由迁移脚本读取后 DROP，
    # 模型不再映射该列（迁移脚本用原生 SQL 读取 rack.power_on）

    def __repr__(self):
        return f"<Rack(id={self.id}, cabinet_id={self.cabinet_id}, name={self.name})>"
