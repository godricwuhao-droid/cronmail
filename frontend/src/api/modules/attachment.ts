/**
 * 附件管理 API 模块
 *
 * 对应后端路由：/api/attachments、/api/system/attachment-categories、/api/attachments/status
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 合同类型 */
export type ContractType = 'compute_leasing' | 'satellite_data' | 'compute_service' | 'project'

/** 附件文件 */
export interface AttachmentFile {
  id: string
  filename: string
  file_size: number
  mime_type?: string
  uploaded_at?: string
}

/** 附件子项（含文件列表） */
export interface AttachmentItem {
  item_id: string
  item_name: string
  expected_type?: string
  files: AttachmentFile[]
  file_count: number
  confirmed: boolean
  confirmed_at?: string | null
}

/** 附件分类（含子项列表） */
export interface AttachmentCategory {
  category_id: string
  category_name: string
  items: AttachmentItem[]
}

/** GET /api/attachments 响应 */
export interface AttachmentListWrap {
  categories: AttachmentCategory[]
}

/** 上传响应 */
export interface AttachmentUploadResponse {
  attachments: Array<{
    id: string
    filename: string
    file_size: number
  }>
}

/** 附件状态汇总 */
export interface AttachmentSummary {
  total_items: number
  confirmed_items: number
  all_confirmed: boolean
  items: Record<string, {
    confirmed: boolean
    file_count: number
  }>
}

/** 附件分类项（系统配置用） */
export interface AttachmentCategoryItem {
  id: string
  name: string
  description?: string | null
  expected_type?: string | null
  sort_order: number
  is_active: boolean
}

/** 附件分类（系统配置用） */
export interface AttachmentCategoryConfig {
  id: string
  contract_type: ContractType
  name: string
  code: string
  sort_order: number
  is_active: boolean
  items: AttachmentCategoryItem[]
}

/** 附件分类列表响应 */
export interface AttachmentCategoryListWrap {
  items: AttachmentCategoryConfig[]
}

/** 创建分类载荷 */
export interface CreateCategoryPayload {
  contract_type: ContractType
  name: string
  code: string
  sort_order?: number
}

/** 更新分类载荷 */
export interface UpdateCategoryPayload {
  name?: string
  code?: string
  sort_order?: number
}

/** 创建子项载荷 */
export interface CreateCategoryItemPayload {
  name: string
  description?: string
  expected_type?: string
  sort_order?: number
}

/** 更新子项载荷 */
export interface UpdateCategoryItemPayload {
  name?: string
  description?: string
  expected_type?: string
  sort_order?: number
}

/** 确认响应 */
export interface ConfirmResponse {
  confirmed: boolean
}

// ============================================================
// 附件文件接口
// ============================================================

/** 获取合同附件列表 */
export function getAttachments(contractType: ContractType, contractId: string): Promise<AttachmentListWrap> {
  return request.get('/attachments', { params: { contract_type: contractType, contract_id: contractId } })
}

/** 上传附件 */
export function uploadAttachments(formData: FormData): Promise<AttachmentUploadResponse> {
  return request.post('/attachments/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 下载附件 */
export function downloadAttachment(id: string): Promise<Blob> {
  return request.get(`/attachments/${id}/download`, { responseType: 'blob' })
}

/** 删除附件 */
export function deleteAttachment(id: string): Promise<{ detail: string }> {
  return request.delete(`/attachments/${id}`)
}

// ============================================================
// 附件状态 / 确认接口
// ============================================================

/** 获取附件状态汇总 */
export function getAttachmentSummary(contractType: ContractType, contractId: string): Promise<AttachmentSummary> {
  return request.get('/attachments/status/summary', { params: { contract_type: contractType, contract_id: contractId } })
}

/** 确认附件子项 */
export function confirmAttachmentItem(
  contractType: ContractType,
  contractId: string,
  itemId: string,
): Promise<ConfirmResponse> {
  return request.post(`/attachments/status/${itemId}/confirm`, {
    contract_type: contractType,
    contract_id: contractId,
  })
}

/** 取消确认附件子项 */
export function unconfirmAttachmentItem(
  contractType: ContractType,
  contractId: string,
  itemId: string,
): Promise<ConfirmResponse> {
  return request.post(`/attachments/status/${itemId}/unconfirm`, {
    contract_type: contractType,
    contract_id: contractId,
  })
}

// ============================================================
// 附件分类管理接口（系统配置）
// ============================================================

/** 获取附件分类列表 */
export function listAttachmentCategories(contractType: ContractType): Promise<AttachmentCategoryListWrap> {
  return request.get('/system/attachment-categories', { params: { contract_type: contractType } })
}

/** 创建附件分类 */
export function createAttachmentCategory(data: CreateCategoryPayload): Promise<AttachmentCategoryConfig> {
  return request.post('/system/attachment-categories', data)
}

/** 更新附件分类 */
export function updateAttachmentCategory(id: string, data: UpdateCategoryPayload): Promise<AttachmentCategoryConfig> {
  return request.put(`/system/attachment-categories/${id}`, data)
}

/** 删除附件分类（软删除） */
export function deleteAttachmentCategory(id: string): Promise<{ detail: string }> {
  return request.delete(`/system/attachment-categories/${id}`)
}

/** 重排分类 */
export function reorderAttachmentCategory(id: string, sortOrder: number): Promise<{ detail: string }> {
  return request.put(`/system/attachment-categories/${id}/reorder`, { sort_order: sortOrder })
}

/** 创建分类子项 */
export function createAttachmentCategoryItem(
  categoryId: string,
  data: CreateCategoryItemPayload,
): Promise<AttachmentCategoryItem> {
  return request.post(`/system/attachment-categories/${categoryId}/items`, data)
}

/** 更新分类子项 */
export function updateAttachmentCategoryItem(
  itemId: string,
  data: UpdateCategoryItemPayload,
): Promise<AttachmentCategoryItem> {
  return request.put(`/system/attachment-categories/items/${itemId}`, data)
}

/** 删除分类子项（软删除） */
export function deleteAttachmentCategoryItem(itemId: string): Promise<{ detail: string }> {
  return request.delete(`/system/attachment-categories/items/${itemId}`)
}

/** 重排子项 */
export function reorderAttachmentCategoryItem(itemId: string, sortOrder: number): Promise<{ detail: string }> {
  return request.put(`/system/attachment-categories/items/${itemId}/reorder`, { sort_order: sortOrder })
}
