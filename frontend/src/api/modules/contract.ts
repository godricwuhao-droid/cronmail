/**
 * 合同 API 模块
 *
 * 对应后端路由：/api/contracts
 *
 * 业务说明：
 *  - 合同是设备的归属单位（替代了直接挂在客户下的关系）
 *  - 创建合同时可一并关联设备和联系人
 *  - 设备 / 联系人可在详情页后续追加或解绑
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** 合同状态枚举 */
export type ContractStatus = 'active' | 'expiring' | 'expired' | 'reclaimed'

/** 计费方式 */
export type ContractBillingModel = 'monthly' | 'quarterly' | 'yearly'

/** 续期链路节点 */
export interface RenewalChainNode {
  id: string
  name: string
  status: string
  start_date: string | null
  end_date: string | null
  is_current: boolean
  renewal_seq: number
}

/** 合同列表项（不含 rentals/contacts 详情） */
export interface ContractItem {
  id: string
  customer_id: string
  customer_name?: string | null
  name: string
  contract_no?: string | null
  start_date: string
  end_date: string
  billing_model: string
  status: ContractStatus
  amount?: number | null
  remark?: string | null
  rental_count: number
  contact_count: number
  sort_order?: number
  created_at?: string | null
  updated_at?: string | null
  renewed_from_id?: string | null
  renewal_seq?: number
  has_renewal?: boolean
}

/** 合同关联设备条目 */
export interface ContractRentalItem {
  id: string
  machine_model: string
  rack_location?: string | null
  private_ip: string | null
  public_ips: string[] | null
  os_version: string | null
  status: string
}

/** 合同关联联系人条目 */
export interface ContractContactItem {
  contact_id: string
  name: string
  email: string
  recipient_type: 'to' | 'cc'
}

/** 合同详情（含 rentals/contacts 数组） */
export interface ContractDetail extends ContractItem {
  rentals: ContractRentalItem[]
  contacts: ContractContactItem[]
  renewal_chain?: RenewalChainNode[]
}

/** 合同列表响应 */
export interface ContractListWrap {
  items: ContractItem[]
  total: number
  page: number
  page_size: number
}

/** 合同列表查询参数 */
export interface ContractListParams {
  customer_id?: string
  status?: ContractStatus
  search?: string
  page?: number
  page_size?: number
}

/** 合同创建载荷 */
export interface ContractCreatePayload {
  customer_id: string
  name: string
  contract_no?: string
  start_date: string
  end_date: string
  billing_model?: ContractBillingModel
  amount?: number
  remark?: string
  rental_ids?: string[]
  contacts?: Array<{ contact_id: string; recipient_type: 'to' | 'cc' }>
  renewed_from_id?: string
  sort_order?: number
}

/** 合同更新载荷（所有字段可选；contacts 传入时全量替换） */
export interface ContractUpdatePayload {
  name?: string
  contract_no?: string
  start_date?: string
  end_date?: string
  billing_model?: ContractBillingModel
  status?: ContractStatus
  amount?: number
  remark?: string
  contacts?: Array<{ contact_id: string; recipient_type: 'to' | 'cc' }>
  sort_order?: number
}

// ============================================================
// 接口函数
// ============================================================

/** 获取合同列表 */
export function listContracts(params: ContractListParams = {}): Promise<ContractListWrap> {
  return request.get('/contracts', { params })
}

/** 创建合同 */
export function createContract(data: ContractCreatePayload): Promise<ContractDetail> {
  return request.post('/contracts', data)
}

/** 获取合同详情 */
export function getContract(id: string): Promise<ContractDetail> {
  return request.get(`/contracts/${id}`)
}

/** 更新合同 */
export function updateContract(id: string, data: ContractUpdatePayload): Promise<ContractDetail> {
  return request.put(`/contracts/${id}`, data)
}

/** 删除合同（物理删除） */
export function deleteContract(id: string): Promise<{ detail: string }> {
  return request.delete(`/contracts/${id}`)
}

/** 关联设备到合同 */
export function linkContractRentals(
  contractId: string,
  rentalIds: string[],
): Promise<{ detail: string }> {
  return request.post(`/contracts/${contractId}/rentals`, { rental_ids: rentalIds })
}

/** 取消关联设备 */
export function unlinkContractRentals(
  contractId: string,
  rentalIds: string[],
): Promise<{ detail: string }> {
  return request.delete(`/contracts/${contractId}/rentals`, { data: { rental_ids: rentalIds } })
}

// ============================================================
// 仪表盘统计
// ============================================================

/** 仪表盘统计数据 */
export interface DashboardStats {
  total_contracts: number
  expiring: number
  expired: number
  reclaimed: number
  email_sent?: number
  expiring_contracts: Array<{
    contract_id: string
    contract_name: string
    customer_name: string
    end_date: string
    status: string
    rental_count: number
    rentals: Array<{
      id: string
      machine_model: string
      private_ip: string
      os_version: string
      status: string
    }>
  }>
}

/** 获取仪表盘统计数据 */
export function getDashboardStats(): Promise<DashboardStats> {
  return request.get('/contracts/dashboard/stats')
}

// ============================================================
// 变更记录 (Changelog)
// ============================================================

/** 变更记录条目 */
export interface ChangeLogEntry {
  id: string
  content: string
  created_at: string
}

/** 获取变更记录列表 */
export function listChangeLogs(target_type: string, target_id: string): Promise<ChangeLogEntry[]> {
  return request.get('/contracts/changelog', { params: { target_type, target_id } })
}

/** 创建变更记录 */
export function createChangeLog(data: {
  target_type: string
  target_id: string
  content: string
}): Promise<ChangeLogEntry> {
  return request.post('/contracts/changelog', data)
}
