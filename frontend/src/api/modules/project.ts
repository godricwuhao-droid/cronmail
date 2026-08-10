/**
 * 项目管理合同 API 模块
 *
 * 对应后端路由：/api/project-contracts
 *
 * 与算力服务合同（compute_service）字段几乎一致，区别：
 *  - 使用 company_code 代替 customer_id
 *  - 列表查询需要 company 参数
 *  - 创建时通过 params 传 company
 */
import request from '@/api'

// ============================================================
// 合同类型定义
// ============================================================

/** 合同类型 */
export type ContractType = 'sales' | 'procurement'

/** 合同类型标签 */
export const CONTRACT_TYPE_LABEL: Record<ContractType, string> = {
  sales: '销售',
  procurement: '采购',
}

/** 合同类型 tag 颜色 */
export const CONTRACT_TYPE_TAG: Record<ContractType, 'success' | 'warning'> = {
  sales: 'success',
  procurement: 'warning',
}

/** 公司代码 → 中文名 */
export const COMPANY_MAP: Record<string, string> = {
  fengyun: '蜂云时代',
  tianshu: '安徽天枢',
  qianxing: '千星控股',
}

// ============================================================
// 服务行类型
// ============================================================

/** 规格 JSON（key-value 自由定义） */
export type ProjectSpecification = Record<string, string | number>

/** 服务行列表项 */
export interface ProjectServiceLine {
  id?: string
  category: string
  item_name: string
  specification?: ProjectSpecification
  unit: string
  quantity: number
  period_months: number
  unit_price: number
  total_price?: number
  manual_total_price?: number
  sort_order?: number
  service_description?: string
}

/** 服务行创建载荷 */
export interface ProjectServiceLineCreatePayload {
  category: string
  item_name: string
  specification?: ProjectSpecification
  unit: string
  quantity: number
  period_months: number
  unit_price: number
  manual_total_price?: number
  sort_order?: number
  service_description?: string
}

// ============================================================
// 合同类型
// ============================================================

/** 关联合同简要信息 */
export interface RelatedContractInfo {
  id: string
  name: string
  contract_no: string | null
  contract_type: ContractType
}

/** 项目管理合同列表项 */
export interface ProjectContractItem {
  id: string
  company_code: string
  name: string
  contract_no?: string | null
  contract_type: ContractType
  party_a_name: string | null
  party_b_name: string | null
  amount: string | null
  start_date: string | null
  end_date: string | null
  related_contract_id: string | null
  project_name?: string | null
  project_type?: string | null
  contract_content?: string | null
  delivery_requirements?: string | null
  process_records?: string | null
  remark?: string | null
  sort_order?: number
  service_lines_count: number
  paid_amount?: string | null
  payment_progress?: number | null
  created_at?: string | null
  updated_at?: string | null
}

/** 项目管理合同详情 */
export interface ProjectContractDetail extends ProjectContractItem {
  amount_auto_calc: string | null
  related_contract: RelatedContractInfo | null
  service_lines: ProjectServiceLine[]
  raw_tables_json?: string | null
  responsible_person?: string | null
  business_person?: string | null
  party_a_contact?: string | null
  party_b_contact?: string | null
}

/** 项目管理合同列表响应 */
export interface ProjectContractListWrap {
  items: ProjectContractItem[]
  total: number
  page: number
  page_size: number
}

/** 项目管理合同列表查询参数 */
export interface ProjectContractListParams {
  company: string
  search?: string
  page?: number
  page_size?: number
}

/** 项目管理合同创建载荷 */
export interface ProjectContractCreatePayload {
  company_code: string
  name: string
  contract_no?: string
  contract_type?: ContractType
  party_a_name?: string
  party_b_name?: string
  amount?: number | null
  start_date?: string
  end_date?: string
  related_contract_id?: string | null
  project_name?: string
  project_type?: string
  contract_content?: string
  delivery_requirements?: string
  process_records?: string
  remark?: string
  responsible_person?: string
  business_person?: string
  party_a_contact?: string
  party_b_contact?: string
  service_lines?: ProjectServiceLineCreatePayload[]
  raw_tables_json?: string | null
  sort_order?: number
}

/** 项目管理合同更新载荷 */
export interface ProjectContractUpdatePayload {
  name?: string
  contract_no?: string
  contract_type?: ContractType
  party_a_name?: string
  party_b_name?: string
  amount?: number | null
  start_date?: string
  end_date?: string
  related_contract_id?: string | null
  project_name?: string
  project_type?: string
  contract_content?: string
  delivery_requirements?: string
  process_records?: string
  remark?: string
  responsible_person?: string
  business_person?: string
  party_a_contact?: string
  party_b_contact?: string
  service_lines?: ProjectServiceLineCreatePayload[]
  raw_tables_json?: string | null
  sort_order?: number
}

// ============================================================
// 合同接口函数
// ============================================================

/** 获取项目管理合同列表 */
export function listProjectContracts(params: ProjectContractListParams): Promise<ProjectContractListWrap> {
  return request.get('/project-contracts', { params })
}

/** 创建项目管理合同 */
export function createProjectContract(data: ProjectContractCreatePayload): Promise<ProjectContractDetail> {
  return request.post('/project-contracts', data, {
    params: { company: data.company_code },
  })
}

/** 获取项目管理合同详情 */
export function getProjectContract(id: string): Promise<ProjectContractDetail> {
  return request.get(`/project-contracts/${id}`)
}

/** 更新项目管理合同 */
export function updateProjectContract(id: string, data: ProjectContractUpdatePayload): Promise<ProjectContractDetail> {
  return request.put(`/project-contracts/${id}`, data)
}

/** 删除项目管理合同 */
export function deleteProjectContract(id: string): Promise<{ detail: string }> {
  return request.delete(`/project-contracts/${id}`)
}

// ============================================================
// 服务行接口函数
// ============================================================

/** 批量保存服务行（全量替换） */
export function batchSaveServiceLines(contractId: string, lines: ProjectServiceLineCreatePayload[]): Promise<{ detail: string }> {
  return request.post(`/project-contracts/${contractId}/service-lines/batch`, { lines })
}

// ============================================================
// 项目类型接口
// ============================================================

/** 项目类型响应 */
export interface ProjectTypeResponse {
  id: string
  name: string
  sort_order: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

/** 获取所有项目类型 */
export function getProjectTypes(): Promise<ProjectTypeResponse[]> {
  return request.get('/project-types')
}

/** 创建项目类型 */
export function createProjectType(data: { name: string; sort_order?: number }): Promise<ProjectTypeResponse> {
  return request.post('/project-types', data)
}

/** 更新项目类型 */
export function updateProjectType(id: string, data: { name?: string; sort_order?: number }): Promise<ProjectTypeResponse> {
  return request.put(`/project-types/${id}`, data)
}

/** 删除项目类型 */
export function deleteProjectType(id: string): Promise<void> {
  return request.delete(`/project-types/${id}`)
}

// ============================================================
// 项目概览接口（新口径：按 project_type 拆分，月度分摊）
// ============================================================

/** 月度合同摘要 */
export interface MonthlyContractSummary {
  id: string
  name: string
  monthly_amount: string
}

/** 月度资源统计 */
export interface MonthlyResourceStats {
  total_vcpu: number
  total_memory_gb: number
  total_storage_gb: number
  total_gpu_count: number
  total_gpu_tops: number
  total_bandwidth_mbps: number
  total_rack_count: number
  total_ip_count: number
}

/** 月度统计（新口径） */
export interface OverviewMonthlyStat {
  month: string
  active_contracts: number
  monthly_amount: string
  contracts: MonthlyContractSummary[]
  resources: MonthlyResourceStats
}

/** 按项目类型分组统计 */
export interface OverviewProjectTypeStat {
  project_type: string
  total_contracts: number
  total_amount: string
  monthly: OverviewMonthlyStat[]
}

/** 项目概览响应（新口径） */
export interface ProjectOverviewResponse {
  year: number
  by_project_type: OverviewProjectTypeStat[]
}

/** 获取项目概览统计数据 */
export function getProjectOverview(year?: number): Promise<ProjectOverviewResponse> {
  return request.get('/project-contracts/overview', { params: year ? { year } : undefined })
}

// ============================================================
// 回款记录 (Payment)
// ============================================================

/** 回款记录 */
export interface PaymentRecord {
  id: string
  contract_id: string
  amount: string
  payment_date: string | null
  receipt_file_id: string | null
  receipt_filename?: string | null
  receipt_mime_type?: string | null
  invoice_file_id: string | null
  invoice_filename?: string | null
  invoice_mime_type?: string | null
  remark: string | null
  created_at: string
}

/** 回款汇总 */
export interface PaymentSummary {
  total_paid: string
  contract_amount: string
  progress: number
}

/** 获取回款列表 */
export function getPayments(contractId: string): Promise<PaymentRecord[]> {
  return request.get(`/project-contracts/${contractId}/payments`)
}

/** 获取回款汇总 */
export function getPaymentSummary(contractId: string): Promise<PaymentSummary> {
  return request.get(`/project-contracts/${contractId}/payments/summary`)
}

/** 创建回款记录 */
export function createPayment(contractId: string, data: {
  amount: number
  payment_date?: string
  receipt_file_id?: string
  invoice_file_id?: string
  remark?: string
}): Promise<PaymentRecord> {
  return request.post(`/project-contracts/${contractId}/payments`, data)
}

/** 更新回款记录 */
export function updatePayment(paymentId: string, data: {
  amount?: number
  payment_date?: string
  remark?: string
}): Promise<PaymentRecord> {
  return request.put(`/project-contracts/payments/${paymentId}`, data)
}

/** 删除回款记录 */
export function deletePayment(paymentId: string): Promise<void> {
  return request.delete(`/project-contracts/payments/${paymentId}`)
}

/** AI 解析回执单（双文件）—— 新版 API */
export interface ParseResult {
  matched: boolean
  receipt_amount?: string | null
  invoice_amount?: string | null
  final_amount?: string | null
  payment_date?: string | null
  payment?: PaymentRecord | null
  detail?: string
  receipt_file_id?: string | null
  invoice_file_id?: string | null
}

/** AI 解析回执单 + 发票（双文件金额匹配） */
export function parsePaymentFiles(
  contractId: string,
  receipt: File,
  invoice?: File,
): Promise<ParseResult> {
  const fd = new FormData()
  fd.append('receipt', receipt)
  if (invoice) fd.append('invoice', invoice)
  return request.post(`/project-contracts/${contractId}/payments/parse`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

/** 确认金额后创建回款记录 */
export function confirmPaymentParse(
  contractId: string,
  data: {
    receipt_file_id: string
    invoice_file_id?: string | null
    amount: string
    payment_date?: string | null
  },
): Promise<PaymentRecord> {
  return request.post(`/project-contracts/${contractId}/payments/parse/confirm`, data)
}

/** @deprecated 使用 parsePaymentFiles 代替 */
export function parsePaymentFile(contractId: string, file: File): Promise<PaymentRecord> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/project-contracts/${contractId}/payments/parse`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}
