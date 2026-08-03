import http from './request'

export interface DashboardStats {
  total_contracts: number
  active_contracts: number
  total_customers: number
  total_templates: number
  total_logs: number
  sent_today: number
  success_rate: number
}

export const getDashboardStats = () => http.get('/dashboard/stats')
export const getRentalDashboard = () => http.get('/dashboard/rental')