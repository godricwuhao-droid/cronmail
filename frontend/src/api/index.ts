/**
 * Axios 实例与全局拦截器
 *
 * - baseURL: /api（开发阶段由 Vite 代理到后端 http://192.168.180.170:30082）
 * - 请求拦截器：打印日志（后续可在此注入 token）
 * - 响应拦截器：统一错误处理（ElMessage 提示）+ 直接返回 response.data
 */
import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'

const instance: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================================
// 自定义 axios 配置扩展：用于「静默请求」标记
// ============================================================
declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 静默标记：true 时不弹错误提示，业务自行处理 */
    __silent?: boolean
  }
  export interface InternalAxiosRequestConfig {
    __silent?: boolean
  }
}

// ============================================================
// 请求拦截器
// ============================================================
instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 开发期打印请求日志
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.params ?? config.data)
    }
    return config
  },
  (error) => {
    // eslint-disable-next-line no-console
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  },
)

// ============================================================
// 响应拦截器
// ============================================================
instance.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // 统一错误提示
    const status = error.response?.status
    let message = '网络异常，请稍后重试'

    if (status === 400) {
      message = error.response?.data?.detail || '请求参数错误'
    } else if (status === 401) {
      message = '未登录或登录已过期'
    } else if (status === 403) {
      message = '没有访问权限'
    } else if (status === 404) {
      message = '请求的资源不存在'
    } else if (status && status >= 500) {
      message = '服务器异常，请稍后重试'
    } else if (error.message) {
      message = error.message
    }

    // 静默标记：某些业务接口不希望弹错，可通过 config.__silent 处理
    const silent = error.config?.__silent
    if (!silent) {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  },
)

// ============================================================
// 包装 request 方法：让调用方拿到的就是 response.data 而非 AxiosResponse
// ============================================================
type RequestInstance = Omit<AxiosInstance, 'request' | 'get' | 'post' | 'put' | 'delete' | 'patch'> & {
  request<T = unknown>(config: AxiosRequestConfig): Promise<T>
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
}

const request = instance as unknown as RequestInstance

export default request
