/**
 * 机房管理 API
 *
 * 对应后端路由：/api/machine-rooms（ADR-021）
 *
 * 业务说明：
 *  - 机房 CRUD（name/code 全局唯一；删除有机房设备时 409）
 *  - 机架 CRUD（机房内 name 唯一；删除机架下有设备时 409）
 *  - 点位图数据（ADR-022）：机架卡片（含 U 位网格 u_cells + 存量设备摘要）+ 仓库未上架设备
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

/** 机架 */
export interface Rack {
  id: number
  machine_room_id: number
  name: string
  capacity_u: number
  created_at: string
}

/** 点位图/仓库中的设备摘要 */
export interface RoomDeviceBrief {
  rental_id: string
  machine_model: string
  rack_location: string | null
  status: string
}

/** U 位格子（ADR-022 点阵图）：u 从 1 开始，空格设备字段为 null */
export interface RackCell {
  u: number
  rental_id: string | null
  machine_model: string | null
  remark: string | null
  private_ip: string | null
  status: string | null
}

/** 点位图机架卡片（U 位网格 + 设备摘要） */
export interface RackPoint {
  id: number
  name: string
  capacity_u: number
  /** U 位网格，长度 = capacity_u，u 从 1 连续（ADR-022） */
  u_cells: RackCell[]
  /** 存量兼容：同机架 rack_location 前缀匹配的设备摘要 */
  devices: RoomDeviceBrief[]
}

/** 机房点位图数据 */
export interface MachineRoomPoints {
  room: MachineRoom
  racks: RackPoint[]
  warehoused: RoomDeviceBrief[]
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

/** 机房点位图数据（机架卡片 + 仓库未上架设备） */
export function getMachineRoomPoints(
  id: number | string,
  config?: AxiosRequestConfig,
): Promise<MachineRoomPoints> {
  return request.get(`/machine-rooms/${id}/points`, config)
}

/** 未上架（在库）设备列表 */
export function getWarehousedDevices(): Promise<WarehousedListResponse> {
  return request.get('/machine-rooms/warehoused')
}

/** 创建机架 */
export function createRack(roomId: number | string, data: RackPayload): Promise<Rack> {
  return request.post(`/machine-rooms/${roomId}/racks`, data)
}

/** 更新机架（只更新传入字段） */
export function updateRack(
  roomId: number | string,
  rackId: number | string,
  data: RackPayload,
): Promise<Rack> {
  return request.put(`/machine-rooms/${roomId}/racks/${rackId}`, data)
}

/** 删除机架（机架下有设备时 409 拒绝） */
export function deleteRack(
  roomId: number | string,
  rackId: number | string,
  config?: AxiosRequestConfig,
): Promise<{ detail: string }> {
  return request.delete(`/machine-rooms/${roomId}/racks/${rackId}`, config)
}
