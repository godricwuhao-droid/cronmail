/**
 * 联系人 / 内部同事 API
 *
 * 对应后端路由：/api/contacts
 *
 * 业务说明：
 *  - type=customer + customer_id：查询指定客户下的联系人
 *  - type=colleague（不传 customer_id）：查询内部同事（customer_id IS NULL）
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

export type ContactType = 'customer' | 'colleague'

export interface Contact {
  id: string
  customer_id: string | null
  name: string
  email: string
  phone: string | null
  department: string | null
  is_active: boolean
  created_at: string
  updated_at?: string | null
}

export interface ContactListResponse {
  items: Contact[]
  total: number
  page: number
  page_size: number
}

export interface ContactListParams {
  /** 客户 ID；type=colleague 时忽略 */
  customer_id?: string
  /** 联系人类型：customer / colleague */
  type?: ContactType
  /**
   * 是否拉取全部
   * - true: 忽略分页，一次性返回所有（目前仅 type=customer 时支持）
   * - false/undefined: 按 page / page_size 分页
   */
  all?: boolean
  page?: number
  page_size?: number
}

export interface ContactCreatePayload {
  customer_id?: string | null
  name: string
  email: string
  phone?: string | null
  department?: string | null
}

export interface ContactUpdatePayload {
  customer_id?: string | null
  name?: string
  email?: string
  phone?: string | null
  department?: string | null
  is_active?: boolean
}

// ============================================================
// 接口函数
// ============================================================

/** 获取联系人列表 */
export function getContacts(params: ContactListParams = {}): Promise<ContactListResponse> {
  return request.get('/contacts', { params })
}

/** 创建联系人 */
export function createContact(data: ContactCreatePayload): Promise<Contact> {
  return request.post('/contacts', data)
}

/** 获取联系人详情 */
export function getContact(id: string): Promise<Contact> {
  return request.get(`/contacts/${id}`)
}

/** 更新联系人 */
export function updateContact(id: string, data: ContactUpdatePayload): Promise<Contact> {
  return request.put(`/contacts/${id}`, data)
}

/** 删除联系人（软删除：is_active=false） */
export function deleteContact(id: string): Promise<{ detail: string }> {
  return request.delete(`/contacts/${id}`)
}
