/**
 * 邮件日志模块共享常量与工具
 */
import type { LogStatus, LogTriggerType, LogRecipientType } from '@/api/modules/log'

/** 触发类型 → 中文 */
export const LOG_TRIGGER_LABEL: Record<LogTriggerType, string> = {
  provision: '开通通知',
  expiry_warning: '临期提醒',
  expiry_notice: '到期提醒',
  reclaim: '回收通知',
}

/** 收件人类型 → 中文 */
export const LOG_RECIPIENT_TYPE_LABEL: Record<LogRecipientType, string> = {
  to: '收件人',
  cc: '抄送',
}

/** 状态 → el-tag 颜色 */
export const LOG_STATUS_TAG: Record<LogStatus, 'success' | 'danger'> = {
  sent: 'success',
  failed: 'danger',
}

/** 状态 → 中文 */
export const LOG_STATUS_LABEL: Record<LogStatus, string> = {
  sent: '已发送',
  failed: '发送失败',
}
