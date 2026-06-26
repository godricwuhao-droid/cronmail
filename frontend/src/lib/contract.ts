/**
 * 合同模块共享常量与工具
 */
import type { ContractStatus } from '@/api/modules/contract'

/** 合同状态 → 中文标签 */
export const CONTRACT_STATUS_LABEL: Record<ContractStatus, string> = {
  active: '生效中',
  expiring: '临期',
  expired: '已到期',
  reclaimed: '已回收',
}

/** 合同状态 → el-tag type 颜色 */
export const CONTRACT_STATUS_TAG: Record<
  ContractStatus,
  'success' | 'warning' | 'danger' | 'info'
> = {
  active: 'success',
  expiring: 'warning',
  expired: 'danger',
  reclaimed: 'info',
}

/** 合同状态选项（用于下拉筛选） */
export const CONTRACT_STATUS_OPTIONS: Array<{ label: string; value: ContractStatus }> = [
  { label: '生效中', value: 'active' },
  { label: '临期', value: 'expiring' },
  { label: '已到期', value: 'expired' },
  { label: '已回收', value: 'reclaimed' },
]

/** 计费方式 → 中文（与后端枚举一致：monthly / quarterly / yearly） */
export const CONTRACT_BILLING_MODEL_LABEL: Record<string, string> = {
  monthly: '按月',
  quarterly: '按季',
  yearly: '按年',
}

/** 计费方式选项（用于下拉选择） */
export const CONTRACT_BILLING_MODEL_OPTIONS: Array<{ label: string; value: string }> = [
  { label: '按月', value: 'monthly' },
  { label: '按季', value: 'quarterly' },
  { label: '按年', value: 'yearly' },
]
