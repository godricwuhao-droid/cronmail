/**
 * 算力服务合同 API 模块
 *
 * 对应后端路由：/api/compute-service-contracts
 */
import request from '@/api'

// ============================================================
// 合同类型定义
// ============================================================

/** 合同类型 */
export type ContractType = 'sales' | 'procurement'

/** 合同类型标签 */
export const CONTRACT_TYPE_LABEL: Record<ContractType, string> = {
  sales: '销售',
  procurement: '采购',
}

/** 合同类型 tag 颜色 */
export const CONTRACT_TYPE_TAG: Record<ContractType, 'success' | 'warning'> = {
  sales: 'success',
  procurement: 'warning',
}

// ============================================================
// 服务行类型
// ============================================================

/** 规格 JSON（key-value 自由定义） */
export type ServiceSpecification = Record<string, string | number>

/** 服务行列表项 */
export interface ServiceLineItem {
  id: string
  category: string
  item_name: string
  specification: ServiceSpecification
  vcpu_count: number
  memory_gb: number
  storage_gb: number
  unit: string
  quantity: number
  period_months: number
  unit_price: number
  total_price: number
  sort_order: number
  service_description?: string
  gpu_count?: number
  gpu_model?: string
  gpu_memory_gb?: number
  gpu_tops?: number
}

/** 服务行创建载荷 */
export interface ServiceLineCreatePayload {
  category: string
  item_name: string
  specification?: ServiceSpecification
  vcpu_count?: number
  memory_gb?: number
  storage_gb?: number
  unit: string
  quantity: number
  period_months: number
  unit_price: number
  manual_total_price?: number
  sort_order?: number
  service_description?: string
  gpu_count?: number
  gpu_model?: string
  gpu_memory_gb?: number
  gpu_tops?: number
}

/** 服务行更新载荷 */
export interface ServiceLineUpdatePayload extends Partial<ServiceLineCreatePayload> {}

/** 批量保存载荷 */
export interface ServiceLineBatchPayload {
  lines: ServiceLineCreatePayload[]
}

/** 服务行列表响应 */
export interface ServiceLineListWrap {
  items: ServiceLineItem[]
}

// ============================================================
// 合同类型
// ============================================================

/** 关联合同简要信息 */
export interface RelatedContractInfo {
  id: string
  name: string
  contract_no: string | null
  contract_type: ContractType
  amount: string | null
}

/** 算力服务合同列表项 */
export interface ServiceContractItem {
  id: string
  customer_id: string
  customer_name?: string | null
  name: string
  contract_no?: string | null
  contract_type: ContractType
  party_a_name: string | null
  party_b_name: string | null
  amount: string | null
  start_date: string | null
  end_date: string | null
  related_contract_id: string | null
  remark?: string | null
  project_name?: string | null
  contract_content?: string | null
  delivery_requirements?: string | null
  process_records?: string | null
  service_lines_count: number
  sort_order?: number
  created_at?: string | null
  updated_at?: string | null
}

/** 算力服务合同详情 */
export interface ServiceContractDetail extends ServiceContractItem {
  amount_auto_calc: string | null
  related_contract: RelatedContractInfo | null
  service_lines: ServiceLineItem[]
  project_name?: string | null
  contract_content?: string | null
  delivery_requirements?: string | null
  process_records?: string | null
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
  contract_type?: ContractType
  party_a_name?: string
  party_b_name?: string
  amount?: number | null
  start_date?: string
  end_date?: string
  related_contract_id?: string | null
  remark?: string
  project_name?: string
  contract_content?: string
  delivery_requirements?: string
  process_records?: string
  service_lines?: ServiceLineCreatePayload[]
  sort_order?: number
}

/** 算力服务合同更新载荷 */
export interface ServiceContractUpdatePayload {
  customer_id?: string
  name?: string
  contract_no?: string
  contract_type?: ContractType
  party_a_name?: string
  party_b_name?: string
  amount?: number | null
  start_date?: string
  end_date?: string
  related_contract_id?: string | null
  remark?: string
  project_name?: string
  contract_content?: string
  delivery_requirements?: string
  process_records?: string
  service_lines?: ServiceLineCreatePayload[]
  sort_order?: number
}

// ============================================================
// 合同接口函数
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
export function getServiceContract(id: string): Promise<ServiceContractDetail> {
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

// ============================================================
// 服务行接口函数
// ============================================================

/** 获取服务行列表 */
export function listServiceLines(contractId: string): Promise<ServiceLineListWrap> {
  return request.get(`/compute-service-contracts/${contractId}/service-lines`)
}

/** 创建服务行 */
export function createServiceLine(contractId: string, data: ServiceLineCreatePayload): Promise<ServiceLineItem> {
  return request.post(`/compute-service-contracts/${contractId}/service-lines`, data)
}

/** 更新服务行 */
export function updateServiceLine(contractId: string, lineId: string, data: ServiceLineUpdatePayload): Promise<ServiceLineItem> {
  return request.put(`/compute-service-contracts/${contractId}/service-lines/${lineId}`, data)
}

/** 删除服务行 */
export function deleteServiceLine(contractId: string, lineId: string): Promise<{ detail: string }> {
  return request.delete(`/compute-service-contracts/${contractId}/service-lines/${lineId}`)
}

/** 批量保存服务行（全量替换） */
export function batchSaveServiceLines(contractId: string, lines: ServiceLineCreatePayload[]): Promise<{ detail: string }> {
  return request.post(`/compute-service-contracts/${contractId}/service-lines/batch`, { lines })
}
