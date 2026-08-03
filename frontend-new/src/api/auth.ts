import http from './request'

export const login = (data: { username: string; password: string }) => http.post('/auth/login', data)
export const getUserInfo = () => http.get('/auth/me')
export const logout = () => http.post('/auth/logout')