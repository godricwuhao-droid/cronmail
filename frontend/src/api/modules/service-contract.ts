/**
 * 算力服务合同 API 模块
 *
 * 对应后端路由：/api/compute-service-contracts
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 算力服务合同列表项 */
export interface ServiceContractItem {
  id: string
  customer_id: string
  customer_name?: string | null
  name: string
  contract_no?: string | null
  remark?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** 算力服务合同列表响应 */
export interface ServiceContractListWrap {
  items: ServiceContractItem[]
  total: number
  page: number
  page_size: number
}

/** 算力服务合同列表查询参数 */
export interface ServiceContractListParams {
  customer_id?: string
  search?: string
  page?: number
  page_size?: number
}

/** 算力服务合同创建载荷 */
export interface ServiceContractCreatePayload {
  customer_id: string
  name: string
  contract_no?: string
  remark?: string
}

/** 算力服务合同更新载荷 */
export interface ServiceContractUpdatePayload {
  name?: string
  contract_no?: string
  remark?: string
}

// ============================================================
// 接口函数
// ============================================================

/** 获取算力服务合同列表 */
export function listServiceContracts(params: ServiceContractListParams = {}): Promise<ServiceContractListWrap> {
  return request.get('/compute-service-contracts', { params })
}

/** 创建算力服务合同 */
export function createServiceContract(data: ServiceContractCreatePayload): Promise<ServiceContractItem> {
  return request.post('/compute-service-contracts', data)
}

/** 获取算力服务合同详情 */
export function getServiceContract(id: string): Promise<ServiceContractItem> {
  return request.get(`/compute-service-contracts/${id}`)
}

/** 更新算力服务合同 */
export function updateServiceContract(id: string, data: ServiceContractUpdatePayload): Promise<ServiceContractItem> {
  return request.put(`/compute-service-contracts/${id}`, data)
}

/** 删除算力服务合同 */
export function deleteServiceContract(id: string): Promise<{ detail: string }> {
  return request.delete(`/compute-service-contracts/${id}`)
}
