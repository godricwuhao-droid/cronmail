import http from './request'

export interface SmtpConfig {
  id: string
  name: string
  host: string
  port: number
  username: string
  password: string
  use_tls: boolean
  is_default: boolean
}

export interface Colleague {
  id: string
  name: string
  email: string
  phone: string
  department: string
}

export interface DingtalkConfig {
  enabled: boolean
  webhook: string
  secret: string
}

export interface SystemConfig {
  mail_from: string
  mail_from_name: string
  default_template_id: string
  cron_expression: string
}

export const getSmtpConfigs = () => http.get('/system/smtp')
export const createSmtpConfig = (data: Partial<SmtpConfig>) => http.post('/system/smtp', data)
export const updateSmtpConfig = (id: string, data: Partial<SmtpConfig>) => http.put(`/system/smtp/${id}`, data)
export const deleteSmtpConfig = (id: string) => http.delete(`/system/smtp/${id}`)

export const getColleagues = () => http.get('/system/colleagues')
export const createColleague = (data: Partial<Colleague>) => http.post('/system/colleagues', data)
export const updateColleague = (id: string, data: Partial<Colleague>) => http.put(`/system/colleagues/${id}`, data)
export const deleteColleague = (id: string) => http.delete(`/system/colleagues/${id}`)

export const getDingtalkConfig = () => http.get('/system/dingtalk')
export const updateDingtalkConfig = (data: DingtalkConfig) => http.put('/system/dingtalk', data)

export const getSystemConfig = () => http.get('/system/config')
export const updateSystemConfig = (data: Partial<SystemConfig>) => http.put('/system/config', data)