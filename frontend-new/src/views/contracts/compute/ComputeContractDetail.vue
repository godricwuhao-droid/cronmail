<template>
  <div class="page-container">
    <div class="page-header">
      <div class="flex items-center gap-base">
        <el-button @click="router.push('/contracts/compute')">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          返回列表
        </el-button>
        <h1 class="page-title">{{ contract.contract_no || '合同详情' }}</h1>
      </div>
    </div>
    <div class="detail-grid">
      <div class="content-card">
        <h3 class="content-card__title">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
          合同信息
        </h3>
        <div class="detail-table">
          <div class="detail-row"><span class="detail-label">合同编号</span><span class="detail-value">{{ contract.contract_no }}</span></div>
          <div class="detail-row"><span class="detail-label">合同标题</span><span class="detail-value">{{ contract.title }}</span></div>
          <div class="detail-row"><span class="detail-label">客户</span><span class="detail-value">{{ contract.customer_name }}</span></div>
          <div class="detail-row"><span class="detail-label">合同金额</span><span class="detail-value">{{ contract.amount ? '¥' + Number(contract.amount).toLocaleString() : '-' }}</span></div>
          <div class="detail-row"><span class="detail-label">开始日期</span><span class="detail-value">{{ contract.start_date }}</span></div>
          <div class="detail-row"><span class="detail-label">结束日期</span><span class="detail-value">{{ contract.end_date }}</span></div>
          <div class="detail-row"><span class="detail-label">状态</span><span class="detail-value"><el-tag :type="statusType(contract.status)" size="small">{{ statusLabel(contract.status) }}</el-tag></span></div>
          <div class="detail-row"><span class="detail-label">描述</span><span class="detail-value">{{ contract.description || '-' }}</span></div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" @click="router.push(`/contracts/compute/${id}/edit`)">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            编辑合同
          </el-button>
          <el-button @click="router.push(`/contracts/compute/${id}/attachments`)">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 7h2a4 4 0 0 1 0 8h-2"/><path d="M3 8v8a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V8a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3z"/></svg>
            查看附件
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getContract } from '@/api/contract'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const contract = ref<any>({})

onMounted(async () => { try { contract.value = await getContract(id) } catch { /* ignore */ } })

const statusType = (s: string) => ({ draft: 'info', active: 'success', expired: 'warning', terminated: 'danger' }[s] || 'info')
const statusLabel = (s: string) => ({ draft: '草稿', active: '生效', expired: '已过期', terminated: '已终止' }[s] || s)
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