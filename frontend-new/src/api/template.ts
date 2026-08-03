import http from './request'

export interface Template {
  id: string
  name: string
  subject: string
  content: string
  content_type: 'html' | 'text'
  is_active: boolean
  created_at: string
  updated_at: string
}

export const getTemplates = (params?: { page?: number; page_size?: number; keyword?: string }) =>
  http.get('/templates', { params })

export const getTemplate = (id: string) => http.get(`/templates/${id}`)
export const createTemplate = (data: Partial<Template>) => http.post('/templates', data)
export const updateTemplate = (id: string, data: Partial<Template>) => http.put(`/templates/${id}`, data)
export const deleteTemplate = (id: string) => http.delete(`/templates/${id}`)