import http from './request'

export interface Attachment {
  id: string
  name: string
  category: string
  file_url: string
  file_size: number
  mime_type: string
  related_type: string
  related_id: string
  uploaded_by: string
  created_at: string
}

export interface AttachmentCategory {
  id: string
  name: string
  description: string
}

export const getAttachments = (params?: {
  page?: number
  page_size?: number
  category?: string
  related_type?: string
}) => http.get('/attachments', { params })

export const getAttachment = (id: string) => http.get(`/attachments/${id}`)
export const uploadAttachment = (data: FormData) =>
  http.post('/attachments/upload', data, { headers: { 'Content-Type': 'multipart/form-data' } })
export const deleteAttachment = (id: string) => http.delete(`/attachments/${id}`)

export const getAttachmentCategories = () => http.get('/attachments/categories')
export const createAttachmentCategory = (data: Partial<AttachmentCategory>) =>
  http.post('/attachments/categories', data)
export const updateAttachmentCategory = (id: string, data: Partial<AttachmentCategory>) =>
  http.put(`/attachments/categories/${id}`, data)
export const deleteAttachmentCategory = (id: string) =>
  http.delete(`/attachments/categories/${id}`)