<template>
  <div class="page-container">
    <div class="page-header"><div class="flex items-center gap-base"><el-button @click="router.push('/devices')"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>返回列表</el-button><h1 class="page-title">{{ device.name || '设备详情' }}</h1></div></div>
    <div class="content-card">
      <h3 class="content-card__title"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>设备信息</h3>
      <div class="detail-table">
        <div class="detail-row"><span class="detail-label">设备名称</span><span class="detail-value">{{ device.name }}</span></div>
        <div class="detail-row"><span class="detail-label">序列号</span><span class="detail-value">{{ device.serial_number }}</span></div>
        <div class="detail-row"><span class="detail-label">型号</span><span class="detail-value">{{ device.model }}</span></div>
        <div class="detail-row"><span class="detail-label">状态</span><span class="detail-value"><el-tag :type="device.status === 'active' ? 'success' : device.status === 'maintenance' ? 'warning' : 'info'" size="small">{{ { active: '运行中', maintenance: '维护中', offline: '离线' }[device.status] || device.status }}</el-tag></span></div>
        <div class="detail-row"><span class="detail-label">IP地址</span><span class="detail-value">{{ device.ip_address }}</span></div>
        <div class="detail-row"><span class="detail-label">位置</span><span class="detail-value">{{ device.location }}</span></div>
        <div class="detail-row"><span class="detail-label">描述</span><span class="detail-value">{{ device.description || '-' }}</span></div>
      </div>
      <div class="detail-actions"><el-button type="primary" @click="router.push(`/devices/${id}/edit`)"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>编辑设备</el-button></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/api/request'
const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const device = ref<any>({})
onMounted(async () => { try { device.value = await http.get(`/devices/${id}`) } catch { /* ignore */ } })
</script>
<style scoped lang="scss">.content-card { background: var(--color-bg-card); border-radius: var(--radius-lg); border: 1px solid var(--color-border-light); box-shadow: var(--shadow-sm); padding: var(--spacing-xl); }
.content-card__title { font-size: var(--font-size-md); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin-bottom: var(--spacing-lg); display: flex; align-items: center; gap: 8px; }
.detail-table { display: flex; flex-direction: column; gap: 12px; }
.detail-row { display: flex; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); }
.detail-row:last-child { border-bottom: none; }
.detail-label { width: 100px; flex-shrink: 0; color: var(--color-text-tertiary); font-size: var(--font-size-sm); }
.detail-value { flex: 1; color: var(--color-text-primary); font-size: var(--font-size-sm); word-break: break-all; }
.detail-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); }</style>