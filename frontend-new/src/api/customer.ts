import http from './request'

export interface Customer {
  id: string
  name: string
  code: string
  status: string
  business_types: string[] | null
  contact_count: number
  contract_stats: {
    total: number
    active: number
    expired: number
  }
  created_at: string
  updated_at: string | null
}

export interface Contact {
  id: string
  customer_id: string | null
  name: string
  email: string
  phone: string | null
  department: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export const getCustomers = (params?: { page?: number; page_size?: number; keyword?: string; status?: string }) =>
  http.get('/customers', { params })

export const getCustomer = (id: string) => http.get(`/customers/${id}`)
export const createCustomer = (data: Partial<Customer>) => http.post('/customers', data)
export const updateCustomer = (id: string, data: Partial<Customer>) => http.put(`/customers/${id}`, data)
export const deleteCustomer = (id: string) => http.delete(`/customers/${id}`)

export const getContacts = (customerId: string) => http.get(`/customers/${customerId}/contacts`)
export const createContact = (customerId: string, data: Partial<Contact>) => http.post(`/customers/${customerId}/contacts`, data)
export const updateContact = (customerId: string, contactId: string, data: Partial<Contact>) =>
  http.put(`/customers/${customerId}/contacts/${contactId}`, data)
export const deleteContact = (customerId: string, contactId: string) =>
  http.delete(`/customers/${customerId}/contacts/${contactId}`)