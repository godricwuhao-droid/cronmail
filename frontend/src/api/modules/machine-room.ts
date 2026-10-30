/**
 * 机房管理 API
 *
 * 对应后端路由：/api/machine-rooms（ADR-021）+ 层级模型（ADR-026）
 *
 * 业务说明：
 *  - 机房 CRUD（name/code 全局唯一；删除有机房设备时 409）
 *  - 层级模型（ADR-026）：机房 → 排（RackRow）→ 机柜（Cabinet）→ 机架（Rack，最小上架单元）
 *    - 排 CRUD：/api/machine-rooms/{room_id}/rows（删除有机柜 → 409）
 *    - 机柜 CRUD：/api/machine-rooms/{room_id}/rows/{row_id}/cabinets + /api/cabinets/{cabinet_id}
 *      （删除有机架 → 409；power_on 电源状态归机柜）
 *    - 机架 CRUD：/api/cabinets/{cabinet_id}/racks + /api/racks/{rack_id}（删除有设备 → 409）
 *  - 点位图（ADR-026 point-map，替代旧 /points）：排 → 机柜 → 机架（U 位网格 u_cells）
 *    + 仓库未上架设备 + 在架未定位 U 设备
 *  - 级联选择源（设备表单用，轻量版）：/api/machine-rooms/{room_id}/locations
 *  - 未上架设备 = machine_room_id IS NULL（全局仓库）
 */
import type { AxiosRequestConfig } from 'axios'
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 机房 */
export interface MachineRoom {
  id: number
  name: string
  code: string
  address: string | null
  note: string | null
  created_at: string
  updated_at: string
}

/** 点位图/仓库中的设备摘要 */
export interface RoomDeviceBrief {
  rental_id: string
  machine_model: string
  rack_location: string | null
  status: string
}

/**
 * U 位格子（ADR-022 点阵图）：u 从 1 开始，空格设备字段为 null
 * ADR-028：多 U 设备区间内每个 U 格都标记同一设备 brief（含 u_size），前端据此合并渲染跨 U 色块
 */
export interface RackCell {
  u: number
  rental_id: string | null
  machine_model: string | null
  remark: string | null
  private_ip: string | null
  status: string | null
  /** 设备占用 U 数（ADR-028 契约：brief 含 u_size；后端未上线前前端按连续同 rental_id 格数推断） */
  u_size?: number | null
}

/** 机架（ADR-026：机柜下的最小上架单元；电源状态已上移机柜，本层无 power_on） */
export interface RackPoint {
  id: number
  name: string
  capacity_u: number
  /** U 位网格，长度 = capacity_u，u 从 1 连续（ADR-022） */
  u_cells: RackCell[]
}

/** 机柜（ADR-026：排下的机柜，power_on 为整柜电源状态） */
export interface Cabinet {
  id: number
  name: string
  /** 通电状态（true=通电 / false=未通电） */
  power_on: boolean
  racks: RackPoint[]
}

/** 排（ADR-026：机房下的排，如「A排」） */
export interface RackRow {
  id: number
  name: string
  note: string | null
  cabinets: Cabinet[]
}

/** 机房点位图数据（ADR-026 point-map，替代旧 MachineRoomPoints） */
export interface MachineRoomPointMap {
  room: MachineRoom
  rows: RackRow[]
  warehoused: RoomDeviceBrief[]
  /** 在架但未定位 U 的设备（ADR-024：rack_id 有值、u_position 为 NULL；后端未上线前缺省，前端按空数组兜底） */
  unlocated?: RoomDeviceBrief[]
}

/** 级联选择源 - 机架（轻量：无 u_cells） */
export interface LocationRack {
  id: number
  name: string
  capacity_u: number
}

/** 级联选择源 - 机柜 */
export interface LocationCabinet {
  id: number
  name: string
  racks: LocationRack[]
}

/** 级联选择源 - 排 */
export interface LocationRow {
  id: number
  name: string
  cabinets: LocationCabinet[]
}

/** 级联选择源响应（设备表单排/机柜/机架三级级联用） */
export interface MachineRoomLocations {
  rows: LocationRow[]
}

/** 通用列表包装（后端全模块列表接口统一返回 {items, total}） */
export interface ListWrap<T> {
  items: T[]
  total: number
}

/** 机房列表响应 */
export interface MachineRoomListResponse {
  items: MachineRoom[]
  total: number
}

/** 未上架设备列表响应 */
export interface WarehousedListResponse {
  items: RoomDeviceBrief[]
  total: number
}

/** 机房创建/更新请求（所有字段可选，创建时 name/code 必填） */
export interface MachineRoomPayload {
  name?: string
  code?: string
  address?: string | null
  note?: string | null
}

/** 排创建/更新请求 */
export interface RackRowPayload {
  name?: string
  note?: string | null
}

/** 机柜创建/更新请求 */
export interface CabinetPayload {
  name?: string
  /** 通电状态（可选，默认 true） */
  power_on?: boolean
}

/** 机架创建/更新请求 */
export interface RackPayload {
  name?: string
  capacity_u?: number
}

// ============================================================
// 接口函数
// ============================================================

/** 机房列表（支持 name/code 模糊搜索） */
export function getMachineRooms(params: { search?: string } = {}): Promise<MachineRoomListResponse> {
  return request.get('/machine-rooms', { params })
}

/** 创建机房 */
export function createMachineRoom(data: MachineRoomPayload): Promise<MachineRoom> {
  return request.post('/machine-rooms', data)
}

/** 机房详情 */
export function getMachineRoom(id: number | string): Promise<MachineRoom> {
  return request.get(`/machine-rooms/${id}`)
}

/** 更新机房（只更新传入字段） */
export function updateMachineRoom(id: number | string, data: MachineRoomPayload): Promise<MachineRoom> {
  return request.put(`/machine-rooms/${id}`, data)
}

/** 删除机房（有机房设备时 409 拒绝） */
export function deleteMachineRoom(
  id: number | string,
  config?: AxiosRequestConfig,
): Promise<{ detail: string }> {
  return request.delete(`/machine-rooms/${id}`, config)
}

/** 机房点位图数据（ADR-026：排 → 机柜 → 机架 U 位网格 + 仓库未上架设备） */
export function getPointMap(
  id: number | string,
  config?: AxiosRequestConfig,
): Promise<MachineRoomPointMap> {
  return request.get(`/machine-rooms/${id}/point-map`, config)
}

/** 级联选择源（设备表单用，轻量 rows/cabinets/racks 结构） */
export function getLocations(id: number | string): Promise<MachineRoomLocations> {
  return request.get(`/machine-rooms/${id}/locations`)
}

/** 未上架（在库）设备列表 */
export function getWarehousedDevices(): Promise<WarehousedListResponse> {
  return request.get('/machine-rooms/warehoused')
}

// ------------------------------------------------------------
// 排 CRUD（ADR-026）
// ------------------------------------------------------------

/** 排列表（包装格式 {items, total}；items 为扁平排，不含嵌套 cabinets） */
export function getRows(roomId: number | string): Promise<ListWrap<RackRow>> {
  return request.get(`/machine-rooms/${roomId}/rows`)
}

/** 创建排 */
export function createRow(roomId: number | string, data: RackRowPayload): Promise<RackRow> {
  return request.post(`/machine-rooms/${roomId}/rows`, data)
}

/** 更新排（只更新传入字段） */
export function updateRow(
  roomId: number | string,
  rowId: number | string,
  data: RackRowPayload,
): Promise<RackRow> {
  return request.put(`/machine-rooms/${roomId}/rows/${rowId}`, data)
}

/** 删除排（排下有机柜时 409 拒绝） */
export function deleteRow(
  roomId: number | string,
  rowId: number | string,
  config?: AxiosRequestConfig,
): Promise<{ detail: string }> {
  return request.delete(`/machine-rooms/${roomId}/rows/${rowId}`, config)
}

// ------------------------------------------------------------
// 机柜 CRUD（ADR-026）
// ------------------------------------------------------------

/** 排下机柜列表（包装格式 {items, total}；items 为扁平机柜，不含嵌套 racks） */
export function getCabinets(
  roomId: number | string,
  rowId: number | string,
): Promise<ListWrap<Cabinet>> {
  return request.get(`/machine-rooms/${roomId}/rows/${rowId}/cabinets`)
}

/** 创建机柜（排内 name 唯一） */
export function createCabinet(
  roomId: number | string,
  rowId: number | string,
  data: CabinetPayload,
): Promise<Cabinet> {
  return request.post(`/machine-rooms/${roomId}/rows/${rowId}/cabinets`, data)
}

/** 更新机柜（只更新传入字段） */
export function updateCabinet(
  cabinetId: number | string,
  data: CabinetPayload,
): Promise<Cabinet> {
  return request.put(`/cabinets/${cabinetId}`, data)
}

/** 删除机柜（机柜下有机架时 409 拒绝） */
export function deleteCabinet(
  cabinetId: number | string,
  config?: AxiosRequestConfig,
): Promise<{ detail: string }> {
  return request.delete(`/cabinets/${cabinetId}`, config)
}

// ------------------------------------------------------------
// 机架 CRUD（ADR-026）
// ------------------------------------------------------------

/** 机柜下机架列表（包装格式 {items, total}；items 为扁平机架，不含 u_cells） */
export function getRacks(cabinetId: number | string): Promise<ListWrap<RackPoint>> {
  return request.get(`/cabinets/${cabinetId}/racks`)
}

/** 创建机架（机柜内 name 唯一） */
export function createRack(cabinetId: number | string, data: RackPayload): Promise<RackPoint> {
  return request.post(`/cabinets/${cabinetId}/racks`, data)
}

/** 更新机架（只更新传入字段） */
export function updateRack(rackId: number | string, data: RackPayload): Promise<RackPoint> {
  return request.put(`/racks/${rackId}`, data)
}

/** 删除机架（机架下有设备时 409 拒绝） */
export function deleteRack(
  rackId: number | string,
  config?: AxiosRequestConfig,
): Promise<{ detail: string }> {
  return request.delete(`/racks/${rackId}`, config)
}
