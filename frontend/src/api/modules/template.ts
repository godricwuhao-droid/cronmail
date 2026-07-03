/**
 * 邮件模板 API
 *
 * 对应后端路由：/api/templates
 *
 * 业务说明：
 *  - trigger_type 枚举: provision | expiry_warning | reclaim
 *  - body_html 中使用 Jinja2 模板语法 {{ variable }}
 *  - preview 接口不会保存，仅用于实时预览渲染结果
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 模板触发类型 */
export type TriggerType = 'provision' | 'expiry_warning' | 'expiry_notice' | 'reclaim'

/** 模板列表项 */
export interface TemplateListItem {
  id: string
  name: string
  trigger_type: TriggerType
  subject_tpl: string
  is_active: boolean
  version: number
  updated_at: string
  created_at?: string
}

/** 模板详情 */
export interface TemplateDetail extends TemplateCreatePayload {
  id: string
  version: number
  created_at: string
  updated_at: string
}

/** 模板创建/更新请求 */
export interface TemplateCreatePayload {
  name: string
  trigger_type: TriggerType
  subject_tpl: string
  body_html: string
  /** 变量说明 {key: 中文描述} */
  variables_desc: Record<string, string>
  /** 邮件签名（HTML），渲染时自动拼接在正文末尾 */
  signature_html?: string
  is_active: boolean
}

export interface TemplateListResponse {
  items: TemplateListItem[]
  total: number
  page: number
  page_size: number
}

export interface TemplateListParams {
  trigger_type?: TriggerType
  is_active?: boolean
  search?: string
  page?: number
  page_size?: number
}

/** 模板部分更新请求（只传需要修改的字段） */
export type TemplateUpdatePayload = Partial<TemplateCreatePayload>

/** 预览请求 */
export interface TemplatePreviewPayload {
  subject_tpl: string
  body_html: string
  sample_data: Record<string, unknown>
  /** 邮件签名（HTML），预览时拼接在正文末尾 */
  signature_html?: string
}

/** 预览响应 */
export interface TemplatePreviewResponse {
  subject_rendered: string
  body_rendered: string
}

/** 模板变量定义（来自后端 /api/templates/variables） */
export interface TemplateVariableItem {
  field: string
  label: string
  type: 'string' | 'number' | 'boolean' | 'date' | 'array' | string
  note?: string
}

/** 模板变量列表响应 */
export interface TemplateVariablesResponse {
  variables: TemplateVariableItem[]
  updated_at: string
}

// ============================================================
// 接口函数
// ============================================================

/** 获取模板列表 */
export function getTemplates(
  params: TemplateListParams = {},
): Promise<TemplateListResponse> {
  return request.get('/templates', { params })
}

/** 创建模板 */
export function createTemplate(data: TemplateCreatePayload): Promise<TemplateDetail> {
  return request.post('/templates', data)
}

/** 获取模板详情 */
export function getTemplate(id: string): Promise<TemplateDetail> {
  return request.get(`/templates/${id}`)
}

/** 更新模板（version 会自动 +1） */
export function updateTemplate(
  id: string,
  data: TemplateUpdatePayload,
): Promise<TemplateDetail> {
  return request.put(`/templates/${id}`, data)
}

/** 删除模板 */
export function deleteTemplate(id: string): Promise<{ detail: string }> {
  return request.delete(`/templates/${id}`)
}

/** 预览模板（不保存，实时返回渲染结果） */
export function previewTemplate(
  data: TemplatePreviewPayload,
): Promise<TemplatePreviewResponse> {
  return request.post('/templates/preview', data)
}

/** 获取可用模板变量列表（后端维护，与 RentalRecord 模型保持一致） */
export function getTemplateVariables(): Promise<TemplateVariablesResponse> {
  return request.get('/templates/variables')
}

/** 测试发送请求 */
export interface TemplateTestSendPayload {
  to_contact_ids: string[]
  cc_contact_ids: string[]
  sample_data: Record<string, unknown>
}

/** 测试发送响应 */
export interface TemplateTestSendResponse {
  success: boolean
  message: string
  to_emails: string[]
  cc_emails: string[]
  subject_rendered: string
}

/** 测试发送：使用模板渲染后发送给指定联系人，不写 EmailLog */
export function testSendTemplate(
  id: string,
  data: TemplateTestSendPayload,
): Promise<TemplateTestSendResponse> {
  return request.post(`/templates/${id}/test-send`, data)
}
