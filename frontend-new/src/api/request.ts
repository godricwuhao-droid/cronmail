import axios from 'axios'
import { ElMessage } from 'element-plus'
// import router from '@/router'  // TODO: 后端认证上线后恢复

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message || '请求失败'
    // TODO: 后端认证上线后恢复 401 跳转登录逻辑
    // if (error.response?.status === 401) {
    //   localStorage.removeItem('token')
    //   localStorage.removeItem('user')
    //   router.push('/login')
    // } else {
    //   ElMessage.error(message)
    // }
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default http