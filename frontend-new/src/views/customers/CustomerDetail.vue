<template>
  <div class="page-container">
    <div class="page-header">
      <div class="flex items-center gap-base">
        <el-button @click="router.push('/customers')">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          返回列表
        </el-button>
        <h1 class="page-title">{{ customer.name || '客户详情' }}</h1>
      </div>
    </div>

    <div class="detail-grid">
      <div class="content-card">
        <h3 class="content-card__title">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
          基本信息
        </h3>
        <div class="detail-table">
          <div class="detail-row"><span class="detail-label">客户名称</span><span class="detail-value">{{ customer.name }}</span></div>
          <div class="detail-row"><span class="detail-label">客户编码</span><span class="detail-value">{{ customer.code }}</span></div>
          <div class="detail-row"><span class="detail-label">联系人</span><span class="detail-value">{{ customer.contact_person }}</span></div>
          <div class="detail-row"><span class="detail-label">联系电话</span><span class="detail-value">{{ customer.contact_phone }}</span></div>
          <div class="detail-row"><span class="detail-label">联系邮箱</span><span class="detail-value">{{ customer.contact_email }}</span></div>
          <div class="detail-row"><span class="detail-label">地址</span><span class="detail-value">{{ customer.address }}</span></div>
          <div class="detail-row"><span class="detail-label">描述</span><span class="detail-value">{{ customer.description || '-' }}</span></div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" @click="router.push(`/customers/${id}/edit`)">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            编辑
          </el-button>
          <el-button @click="router.push(`/customers/${id}/contacts`)">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/></svg>
            管理联系人
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCustomer } from '@/api/customer'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const customer = ref<any>({})

onMounted(async () => {
  try { customer.value = await getCustomer(id) } catch { /* ignore */ }
})
</script>

<style scoped lang="scss">
.detail-grid { display: grid; grid-template-columns: 1fr; gap: var(--spacing-xl); }
.content-card { background: var(--color-bg-card); border-radius: var(--radius-lg); border: 1px solid var(--color-border-light); box-shadow: var(--shadow-sm); padding: var(--spacing-xl); }
.content-card__title { font-size: var(--font-size-md); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin-bottom: var(--spacing-lg); display: flex; align-items: center; gap: 8px; }
.detail-table { display: flex; flex-direction: column; gap: 12px; }
.detail-row { display: flex; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); }
.detail-row:last-child { border-bottom: none; }
.detail-label { width: 100px; flex-shrink: 0; color: var(--color-text-tertiary); font-size: var(--font-size-sm); }
.detail-value { flex: 1; color: var(--color-text-primary); font-size: var(--font-size-sm); word-break: break-all; }
.detail-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); }
</style>