/**
 * 租赁模块共享常量与工具
 */
import type { RentalStatus } from '@/api/modules/rental'

/** 状态 → 中文标签 */
export const RENTAL_STATUS_LABEL: Record<RentalStatus, string> = {
  '空闲中': '空闲中',
  '已断电': '已断电',
  '租赁中': '租赁中',
}

/** 状态 → el-tag type 颜色 */
export const RENTAL_STATUS_TAG: Record<RentalStatus, 'success' | 'warning' | 'danger' | 'info'> = {
  '空闲中': 'success',
  '已断电': 'info',
  '租赁中': 'warning',
}

/** 旧状态值 fallback 映射（兼容后端可能返回旧值） */
export const RENTAL_STATUS_FALLBACK: Record<string, string> = {
  provisioned: '空闲中',
  reclaimed: '已断电',
  '运行中': '空闲中',
  '维护中': '空闲中',
  '已下架': '已断电',
  '故障': '已断电',
}

/**
 * 安全获取状态标签：优先用新状态值，旧值走 fallback，都不匹配则原样返回
 */
export function safeStatusLabel(status?: string | null): string {
  if (!status) return '-'
  if (status in RENTAL_STATUS_LABEL) return RENTAL_STATUS_LABEL[status as RentalStatus]
  if (status in RENTAL_STATUS_FALLBACK) return RENTAL_STATUS_FALLBACK[status]
  return status
}

/**
 * 安全获取状态 Tag 类型：优先用新状态值，旧值走 fallback 再查 TAG
 */
export function safeStatusTagType(status?: string | null): 'success' | 'warning' | 'danger' | 'info' {
  if (!status) return 'info'
  if (status in RENTAL_STATUS_TAG) return RENTAL_STATUS_TAG[status as RentalStatus]
  const mapped = RENTAL_STATUS_FALLBACK[status]
  if (mapped && mapped in RENTAL_STATUS_TAG) return RENTAL_STATUS_TAG[mapped as RentalStatus]
  return 'info'
}

/** 计费方式 → 中文（与后端枚举一致：仅 monthly / yearly） */
export const BILLING_MODEL_LABEL: Record<string, string> = {
  monthly: '按月',
  yearly: '按年',
}
