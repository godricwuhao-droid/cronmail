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
  created_at?: string | null
  updated_at?: string | null
}

/** 项目管理合同详情 */
export interface ProjectContractDetail extends ProjectContractItem {
  amount_auto_calc: string | null
  related_contract: RelatedContractInfo | null
  service_lines: ProjectServiceLine[]
  raw_tables_json?: string | null
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
