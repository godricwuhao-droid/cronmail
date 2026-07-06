/**
 * 卫星数据合同 API 模块
 *
 * 对应后端路由：/api/satellite-data-contracts
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 卫星数据合同列表项 */
export interface SatelliteContractItem {
  id: string
  customer_id: string
  customer_name?: string | null
  name: string
  contract_no?: string | null
  remark?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** 卫星数据合同列表响应 */
export interface SatelliteContractListWrap {
  items: SatelliteContractItem[]
  total: number
  page: number
  page_size: number
}

/** 卫星数据合同列表查询参数 */
export interface SatelliteContractListParams {
  customer_id?: string
  search?: string
  page?: number
  page_size?: number
}

/** 卫星数据合同创建载荷 */
export interface SatelliteContractCreatePayload {
  customer_id: string
  name: string
  contract_no?: string
  remark?: string
}

/** 卫星数据合同更新载荷 */
export interface SatelliteContractUpdatePayload {
  name?: string
  contract_no?: string
  remark?: string
}

// ============================================================
// 接口函数
// ============================================================

/** 获取卫星数据合同列表 */
export function listSatelliteContracts(params: SatelliteContractListParams = {}): Promise<SatelliteContractListWrap> {
  return request.get('/satellite-data-contracts', { params })
}

/** 创建卫星数据合同 */
export function createSatelliteContract(data: SatelliteContractCreatePayload): Promise<SatelliteContractItem> {
  return request.post('/satellite-data-contracts', data)
}

/** 获取卫星数据合同详情 */
export function getSatelliteContract(id: string): Promise<SatelliteContractItem> {
  return request.get(`/satellite-data-contracts/${id}`)
}

/** 更新卫星数据合同 */
export function updateSatelliteContract(id: string, data: SatelliteContractUpdatePayload): Promise<SatelliteContractItem> {
  return request.put(`/satellite-data-contracts/${id}`, data)
}

/** 删除卫星数据合同 */
export function deleteSatelliteContract(id: string): Promise<{ detail: string }> {
  return request.delete(`/satellite-data-contracts/${id}`)
}
