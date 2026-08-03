import http from './request'

export interface Log {
  id: string
  rental_id: string | null
  template_id: string | null
  trigger_type: string | null
  recipient: string
  recipient_type: string | null
  subject: string | null
  status: 'pending' | 'sending' | 'sent' | 'failed'
  error_msg: string | null
  sent_at: string | null
  created_at: string
  extra_data: Record<string, any> | null
}

export const getLogs = (params?: {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
  start_date?: string
  end_date?: string
}) => http.get('/logs', { params })

export const getLog = (id: string) => http.get(`/logs/${id}`)