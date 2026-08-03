import http from './request'

export interface RentalRecord {
  id: string
  customer_id: string | null
  machine_model: string
  cpu_model: string | null
  memory_gb: number | null
  gpu_info: string | null
  system_disk: string | null
  data_disks: string[] | null
  os_version: string | null
  bandwidth_mbps: number | null
  rack_location: string | null
  private_ip: string | null
  public_ips: string[] | null
  ssh_port: number
  root_username: string | null
  billing_model: string
  start_date: string | null
  end_date: string | null
  auto_renew: boolean
  status: string
  remark: string | null
  contract_count: number
  contact_count: number
  created_at: string
  updated_at: string
}

export const getRentals = (params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
}) => http.get('/rentals', { params })

export const getRental = (id: string) => http.get(`/rentals/${id}`)
export const createRental = (data: Partial<RentalRecord>) => http.post('/rentals', data)
export const updateRental = (id: string, data: Partial<RentalRecord>) => http.put(`/rentals/${id}`, data)
export const deleteRental = (id: string) => http.delete(`/rentals/${id}`)