/**
 * 系统配置 API
 *
 * 对应后端路由：/api/system/*
 */
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================

/** SMTP 配置响应（不含密码） */
export interface SmtpConfig {
  host: string
  port: number
  username: string | null
  sender_name: string | null
  sender_email: string | null
  encryption: 'tls' | 'starttls' | 'none'
}

/** SMTP 配置更新请求（包含密码） */
export interface SmtpConfigUpdate {
  host: string
  port: number
  username?: string
  /** 密码为可选：传空字符串表示不更新 */
  password?: string
  sender_name?: string
  sender_email?: string
  encryption?: 'tls' | 'starttls' | 'none'
}

export interface SmtpTestRequest {
  test_email: string
}

export interface SmtpTestResponse {
  success: boolean
  message: string
}

// ============================================================
// 接口函数
// ============================================================

/** 获取 SMTP 配置（不含密码）；404 不弹错误提示，由调用方处理 */
export function getSmtpConfig(): Promise<SmtpConfig> {
  return request.get('/system/smtp', { __silent: true })
}

/** 更新 SMTP 配置（首次不存在则创建） */
export function updateSmtpConfig(data: SmtpConfigUpdate): Promise<SmtpConfig> {
  return request.put('/system/smtp', data)
}

/** 测试 SMTP 连接（向指定邮箱发送一封测试邮件） */
export function testSmtp(data: SmtpTestRequest): Promise<SmtpTestResponse> {
  return request.post('/system/smtp/test', data)
}

// ============================================================
// 系统配置（键值对）
// ============================================================

/** 系统配置条目 */
export interface SystemConfigItem {
  key: string
  value: string
  description?: string | null
}

/** 获取单个系统配置 */
export function getConfig(key: string): Promise<SystemConfigItem> {
  return request.get(`/system/config/${key}`)
}

/** 更新或创建系统配置 */
export function updateConfig(key: string, value: string): Promise<SystemConfigItem> {
  return request.put(`/system/config/${key}`, { value })
}

// ============================================================
// 通知时间配置（Celery Beat Schedules）
// ============================================================

/** 通知时间配置 */
export interface ScheduleConfig {
  'check-expiring-rentals': string
  'check-expired-rentals': string
  'check-reclaim-expired': string
}

/** 获取通知时间配置 */
export function getSchedules(): Promise<ScheduleConfig> {
  return request.get('/system/config/schedules')
}

/** 更新通知时间配置；返回 detail 和 restart 信息 */
export function updateSchedules(data: ScheduleConfig): Promise<{ detail: string; restart: string }> {
  return request.put('/system/config/schedules', data)
}

// ============================================================
// 钉钉机器人配置
// ============================================================

/** 钉钉机器人配置响应（secret 为脱敏值 "***" 或 ""） */
export interface DingTalkConfig {
  id: string
  webhook_url: string
  secret: string
  is_active: boolean
  created_at: string
  updated_at: string
}

/** 钉钉机器人配置更新请求 */
export interface DingTalkConfigUpdate {
  webhook_url: string
  /** 传 "***" 表示保留原值，传 "" 清空，传其他值更新 */
  secret?: string
  is_active?: boolean
}

/** 钉钉测试发送请求 */
export interface DingTalkTestRequest {
  /** 可选覆盖 webhook 地址，不传则使用已保存配置 */
  webhook_url?: string
  /** 可选覆盖密钥 */
  secret?: string
}

/** 钉钉测试发送响应 */
export interface DingTalkTestResponse {
  success: boolean
  message: string
}

/** 获取钉钉机器人配置（secret 为脱敏值）；404 不弹错误提示，由调用方处理 */
export function getDingTalkConfig(): Promise<DingTalkConfig> {
  return request.get('/system/dingtalk', { __silent: true })
}

/** 更新钉钉机器人配置 */
export function updateDingTalkConfig(data: DingTalkConfigUpdate): Promise<DingTalkConfig> {
  return request.put('/system/dingtalk', data)
}

/** 测试钉钉通知发送 */
export function testDingTalk(data: DingTalkTestRequest): Promise<DingTalkTestResponse> {
  return request.post('/system/dingtalk/test', data)
}
