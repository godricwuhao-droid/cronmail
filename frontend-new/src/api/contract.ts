import http from './request'

export interface Contract {
  id: string
  customer_id: string
  customer_name: string | null
  name: string
  contract_no: string | null
  start_date: string
  end_date: string
  billing_model: string
  status: 'active' | 'expiring' | 'expired' | 'reclaimed'
  amount: number | string | null
  remark: string | null
  rental_count: number
  contact_count: number
  renewed_from_id: string | null
  renewal_seq: number | null
  has_renewal: boolean
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

export const getContracts = (params?: {
  page?: number
  page_size?: number
  customer_id?: string
  status?: string
  keyword?: string
}) => http.get('/contracts', { params })

export const getContract = (id: string) => http.get(`/contracts/${id}`)
export const createContract = (data: Partial<Contract>) => http.post('/contracts', data)
export const updateContract = (id: string, data: Partial<Contract>) => http.put(`/contracts/${id}`, data)
export const deleteContract = (id: string) => http.delete(`/contracts/${id}`)
export const changeStatus = (id: string, status: Contract['status']) =>
  http.put(`/contracts/${id}/status`, { status })
export const renewContract = (id: string, data: { start_date: string; end_date: string }) =>
  http.post(`/contracts/${id}/renew`, data)