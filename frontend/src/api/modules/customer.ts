/**
 * 客户管理 API
 *
 * 对应后端路由：/api/customers
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

export interface ContractStats {
  total: number
  active: number
  expired: number
}

export interface Customer {
  id: string
  name: string
  code?: string
  status: 'active' | 'inactive'
  business_types?: string[]
  contact_count?: number
  contract_stats?: ContractStats
  created_at: string
  updated_at?: string | null
}

export interface CustomerListResponse {
  items: Customer[]
  total: number
  page: number
  page_size: number
}

export interface CustomerCreatePayload {
  name: string
  code?: string
  business_types?: string[]
}

export interface CustomerUpdatePayload {
  name?: string
  code?: string
  status?: 'active' | 'inactive'
  business_types?: string[]
}

export interface CustomerListParams {
  search?: string
  /** 业务类型过滤: 算力租赁 / 卫星数据 / 算力服务 */
  business_type?: string
  page?: number
  page_size?: number
}

// ============================================================
// 接口函数
// ============================================================

/** 获取客户列表（支持分页与名称模糊搜索） */
export function getCustomers(params: CustomerListParams = {}): Promise<CustomerListResponse> {
  return request.get('/customers', { params })
}

/** 创建客户 */
export function createCustomer(data: CustomerCreatePayload): Promise<Customer> {
  return request.post('/customers', data)
}

/** 获取客户详情 */
export function getCustomer(id: string): Promise<Customer> {
  return request.get(`/customers/${id}`)
}

/** 更新客户 */
export function updateCustomer(id: string, data: CustomerUpdatePayload): Promise<Customer> {
  return request.put(`/customers/${id}`, data)
}

/** 删除客户（软删除：状态置为 inactive） */
export function deleteCustomer(id: string): Promise<{ detail: string }> {
  return request.delete(`/customers/${id}`)
}
