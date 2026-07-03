/**
 * 邮件发送日志 API
 *
 * 对应后端路由：/api/logs
 *
 * 业务说明：
 *  - trigger_type 枚举: provision | expiry_warning | reclaim
 *  - status 枚举: sent | failed
 *  - 详情接口会返回完整邮件正文 body
 *  - 只有 failed 状态的日志可以重发
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 触发类型 */
export type LogTriggerType = 'provision' | 'expiry_warning' | 'expiry_notice' | 'reclaim'

/** 收件人类型 */
export type LogRecipientType = 'to' | 'cc'

/** 日志状态 */
export type LogStatus = 'sent' | 'failed'

/** 日志列表项 */
export interface EmailLogListItem {
  id: string
  rental_id: string
  template_id: string | null
  trigger_type: LogTriggerType
  recipient: string
  recipient_type: LogRecipientType
  subject: string
  status: LogStatus
  error_msg: string | null
  sent_at: string
}

/** 日志详情（含完整 body） */
export interface EmailLogDetail extends EmailLogListItem {
  body: string
}

/** 列表响应 */
export interface EmailLogListResponse {
  items: EmailLogListItem[]
  total: number
  page: number
  page_size: number
}

export interface EmailLogListParams {
  rental_id?: string
  trigger_type?: LogTriggerType
  status?: LogStatus
  page?: number
  page_size?: number
}

export interface ResendLogResponse {
  /** 关联的日志 ID（重发时可能返回新生成的 ID 或原 ID） */
  email_log_id: string | null
  status: 'sent' | 'failed'
  success: boolean
  message: string
}

// ============================================================
// 接口函数
// ============================================================

/** 获取邮件日志列表 */
export function getLogs(params: EmailLogListParams = {}): Promise<EmailLogListResponse> {
  return request.get('/logs', { params })
}

/** 获取邮件日志详情 */
export function getLog(id: string): Promise<EmailLogDetail> {
  return request.get(`/logs/${id}`)
}

/** 重发失败的邮件 */
export function resendLog(id: string): Promise<ResendLogResponse> {
  return request.post(`/logs/${id}/resend`)
}
