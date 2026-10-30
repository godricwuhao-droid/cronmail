/**
 * 租赁模块共享常量与工具
 */
import type { RentalStatus } from '@/api/modules/rental'
import { RENTAL_STATUS_FALLBACK } from '@/api/modules/rental'

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

// RENTAL_STATUS_FALLBACK 从 @/api/modules/rental 导入，不在此重复定义
export { RENTAL_STATUS_FALLBACK }

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

/**
 * 仅机架名展示（列表「机架」列，ADR-028 由「机柜/机架位置」列改名；ADR-024 表头去重修订）：
 *  - 有 rack_name → 原样返回（ADR-028 起为纯机架名，如 `A01-45U`），**不带 U 位**
 *  - 无 rack_name 但有 rack_location 存量文本 → 原样显示
 *  - 都无 → '—'
 *
 * U 数单独由「U数」列（u_size）展示，避免与机架列信息重复。
 */
export function formatRackPath(record: {
  rack_name?: string | null
  rack_location?: string | null
}): string {
  if (record.rack_name) return record.rack_name
  if (record.rack_location) return record.rack_location
  return '—'
}

/**
 * 统一位置展示（ADR-024）：
 *  - 有 rack_name → `{rack_name}-U{u_position}`（如 A01-U12；u_position 为空时只返回 rack_name）
 *  - 无 rack_name 但有 rack_location 存量文本 → 原样显示
 *  - 都无 → '—'
 *
 * 注意：含 U 位，适合详情页/合同明细等单行展示场景；列表列请用 formatRackPath。
 */
export function formatRackLocation(record: {
  rack_name?: string | null
  u_position?: number | null
  rack_location?: string | null
}): string {
  if (record.rack_name) {
    return record.u_position != null ? `${record.rack_name}-U${record.u_position}` : record.rack_name
  }
  if (record.rack_location) return record.rack_location
  return '—'
}
