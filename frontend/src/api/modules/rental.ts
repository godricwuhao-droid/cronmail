/**
 * 租赁记录 API
 *
 * 对应后端路由：/api/rentals
 *
 * 业务说明：
 *  - 列表支持按客户、状态、关键词（机器型号/IP）筛选
 *  - 创建/更新时需要提交联系人收件人关系（to/cc）
 *  - 详情会返回解密后的密码（仅供内部管理使用）
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 租赁状态枚举 */
export type RentalStatus = '空闲中' | '已断电' | '租赁中'

/** 旧状态值兼容映射（后端可能仍返回旧值） */
export const RENTAL_STATUS_FALLBACK: Record<string, string> = {
  provisioned: '空闲中',
  reclaimed: '已断电',
  '运行中': '空闲中',
  '维护中': '空闲中',
  '已下架': '已断电',
  '故障': '已断电',
}

/** 计费方式 */
export type BillingModel = 'monthly' | 'yearly'

/** 数据盘条目 */
export interface DataDisk {
  size_gb: number
  type: string
}

/** 租赁联系人收件人条目 */
export interface RentalContactLink {
  contact_id: string
  /** 收件人类型：to/cc */
  recipient_type: 'to' | 'cc'
}

/** 租赁记录列表项 */
export interface RentalListItem {
  id: string
  customer: {
    id: string
    name: string
  }
  contract_id?: string | null
  machine_model: string
  rack_location?: string | null
  private_ip: string | null
  start_date: string
  end_date: string
  status: RentalStatus
  created_at: string
}

/** 租赁记录详情（后端响应：含 customer 简要信息 + contacts 详情 + email_logs） */
export interface RentalDetail {
  id: string
  customer: {
    id: string
    name: string
  } | null
  /** 关联的合同信息（通过合同关联设备时返回） */
  contract_info?: {
    id: string
    name: string
    start_date: string
    end_date: string
    billing_model: string
  } | null
  contacts: Array<{
    contact_id: string
    name: string
    email: string
    recipient_type: 'to' | 'cc'
  }>
  machine_model: string
  cpu_model: string | null
  memory_gb: number | null
  gpu_info: string | null
  system_disk_gb: number | null
  data_disks: DataDisk[] | null
  os_version: string | null
  bandwidth_mbps: number | null
  rack_location: string | null
  private_ip: string | null
  public_ips: string[] | null
  ssh_port: number
  root_username: string | null
  root_password: string | null
  billing_model: BillingModel
  start_date: string | null
  end_date: string | null
  auto_renew: boolean
  remark: string | null
  status: RentalStatus
  email_logs?: Array<{
    id: string
    trigger_type: 'provision' | 'expiry_warning' | 'reclaim' | null
    recipient: string
    recipient_type: 'to' | 'cc' | null
    subject: string | null
    status: 'sent' | 'failed'
    error_msg: string | null
    sent_at: string | null
    created_at: string
  }>
  created_at: string
  updated_at?: string | null
}

/** 租赁记录创建请求（仅硬件信息，客户/日期/计费/联系人由合同管理） */
export interface RentalCreatePayload {
  machine_model?: string
  cpu_model?: string
  memory_gb?: number
  gpu_info?: string
  system_disk_gb?: number
  data_disks?: DataDisk[]
  os_version?: string
  bandwidth_mbps?: number
  rack_location?: string
  private_ip?: string
  public_ips?: string[]
  ssh_port?: number
  root_username?: string
  root_password?: string
  remark?: string
  status?: string
}

/** 租赁记录更新请求（仅硬件信息，所有字段可选） */
export interface RentalUpdatePayload {
  machine_model?: string
  cpu_model?: string
  memory_gb?: number
  gpu_info?: string
  system_disk_gb?: number
  data_disks?: DataDisk[]
  os_version?: string
  bandwidth_mbps?: number
  rack_location?: string
  private_ip?: string
  public_ips?: string[]
  ssh_port?: number
  root_username?: string
  root_password?: string
  remark?: string
  status?: string
}

export interface RentalListResponse {
  items: RentalListItem[]
  total: number
  page: number
  page_size: number
}

export interface RentalListParams {
  customer_id?: string
  status?: RentalStatus
  search?: string
  /** 按内网IP模糊搜索 */
  private_ip?: string
  /** 按公网IP模糊搜索（匹配 public_ips JSON 数组） */
  public_ip?: string
  /** 按机架位置模糊搜索 */
  rack_location?: string
  /** 仅返回未关联合同的设备 */
  unlinked_only?: boolean
  page?: number
  page_size?: number
}

export interface SendProvisionEmailPayload {
  template_id?: string
}

export interface SendProvisionEmailResponse {
  email_log_ids: string[]
  recipient_count: number
}

// ============================================================
// 接口函数
// ============================================================

/** 获取租赁记录列表 */
export function getRentals(params: RentalListParams = {}): Promise<RentalListResponse> {
  return request.get('/rentals', { params })
}

/** 创建租赁记录（仅保存，不发邮件） */
export function createRental(data: RentalCreatePayload): Promise<RentalDetail> {
  return request.post('/rentals', data)
}

/** 获取租赁记录详情 */
export function getRental(id: string): Promise<RentalDetail> {
  return request.get(`/rentals/${id}`)
}

/** 全量更新租赁记录 */
export function updateRental(
  id: string,
  data: RentalUpdatePayload,
): Promise<RentalDetail> {
  return request.put(`/rentals/${id}`, data)
}

/** 删除租赁记录 */
export function deleteRental(id: string): Promise<{ detail: string }> {
  return request.delete(`/rentals/${id}`)
}

/** 手动发送开通邮件 */
export function sendProvisionEmail(
  id: string,
  data: SendProvisionEmailPayload = {},
): Promise<SendProvisionEmailResponse> {
  return request.post(`/rentals/${id}/send-provision-email`, data)
}

/** 手动发送临期提醒邮件 */
export function sendExpiryReminder(
  id: string,
  data: SendProvisionEmailPayload = {},
): Promise<SendProvisionEmailResponse> {
  return request.post(`/rentals/${id}/send-expiry-reminder`, data)
}

/** 手动回收（发送回收邮件 + 状态置为 reclaimed） */
export function reclaimRental(
  id: string,
  data: SendProvisionEmailPayload = {},
): Promise<SendProvisionEmailResponse> {
  return request.post(`/rentals/${id}/reclaim`, data)
}
