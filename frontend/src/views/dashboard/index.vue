<template>
  <div class="page-container">
    <div class="page-title">
      <el-icon :size="22" style="color: #409EFF; vertical-align: -3px;"><Odometer /></el-icon>
      <span style="margin-left: 8px;">运营概览</span>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card" v-for="card in statCards" :key="card.key" :style="{ borderTopColor: card.color }">
        <div class="stat-top">
          <div class="stat-icon">
            <el-icon :size="28" :color="card.color"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
        </div>
        <div class="stat-label">{{ card.label }}</div>
      </div>
    </div>

    <!-- 待处理提醒（合同维度） -->
    <el-card shadow="never" style="border-radius: 12px;">
      <template #header>
        <div class="card-header">
          <h2>
            <el-icon style="color: #E6A23C; vertical-align: -2px;"><Bell /></el-icon>
            <span style="margin-left: 6px;">待处理提醒</span>
          </h2>
        </div>
      </template>

      <div v-loading="loading">
        <template v-if="expiringContracts.length === 0">
          <el-empty description="暂无待处理记录" />
        </template>
        <div v-else class="reminder-list">
          <div
            class="reminder-card"
            v-for="row in expiringContracts"
            :key="row.contract_id"
          >
            <div class="reminder-header" @click="toggleExpand(row.contract_id)">
              <div class="reminder-info">
                <span class="reminder-name">{{ row.contract_name }}</span>
                <span class="reminder-customer">{{ row.customer_name }}</span>
                <el-tag :type="contractStatusTagType(row.status)" size="small">{{ contractStatusLabel(row.status) }}</el-tag>
              </div>
              <div class="reminder-meta">
                <span class="reminder-count">设备数：{{ row.rental_count ?? 0 }}</span>
                <span class="reminder-date" style="color: #E6A23C; font-weight: 600;">到期：{{ formatDate(row.end_date) }}</span>
                <el-icon
                  class="expand-arrow"
                  :class="{ expanded: expandedMap[row.contract_id] }"
                  :size="16"
                ><ArrowRightBold /></el-icon>
              </div>
            </div>
            <div class="reminder-body" v-show="expandedMap[row.contract_id]">
              <el-table :data="row.rentals || []" size="small" border>
                <el-table-column label="机架位置" min-width="140">
                  <template #default="{ row: r }">{{ r.rack_location || '-' }}</template>
                </el-table-column>
                <el-table-column prop="machine_model" label="设备型号" min-width="160" />
                <el-table-column label="公网 IP" min-width="140">
                  <template #default="{ row: r }">{{ formatIpList(r.public_ips) }}</template>
                </el-table-column>
                <el-table-column label="内网 IP" min-width="140">
                  <template #default="{ row: r }">{{ r.private_ip || '-' }}</template>
                </el-table-column>
              </el-table>
              <div class="reminder-actions">
                <el-button size="small" type="primary" @click="$router.push(`/contracts/compute-leasing/${row.contract_id}`)">查看详情</el-button>
                <el-button size="small" type="warning" @click="handleSendReminder(row)">发送提醒</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.page-title {
  margin-bottom: 24px;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
}

/* ---- 统计卡片 ---- */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .stat-grid { grid-template-columns: 1fr; }
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border-top: 4px solid;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.stat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #f5f7fa;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
}
.stat-label {
  color: #909399;
  font-size: 14px;
  margin-top: 8px;
}

/* ---- 待处理提醒 ---- */
.reminder-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.reminder-card {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.reminder-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.reminder-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  cursor: pointer;
  user-select: none;
  background: #fafbfc;
  transition: background 0.15s;
}
.reminder-header:hover {
  background: #f0f2f5;
}
.reminder-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.reminder-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}
.reminder-customer {
  font-size: 13px;
  color: #909399;
}
.reminder-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 13px;
  color: #606266;
}
.reminder-count {
  color: #909399;
}
.expand-arrow {
  transition: transform 0.2s;
  color: #909399;
}
.expand-arrow.expanded {
  transform: rotate(90deg);
}
.reminder-body {
  padding: 12px 18px 16px;
  background: #fff;
  border-top: 1px solid #ebeef5;
}
.reminder-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Odometer, Bell, Document, Clock, Checked, CircleCloseFilled, ArrowRightBold } from '@element-plus/icons-vue'
import { getDashboardStats, type DashboardStats } from '@/api/modules/contract'
import { sendExpiryReminder } from '@/api/modules/rental'
function formatIpList(ips: any): string {
  if (!ips) return '-'
  if (Array.isArray(ips)) return ips.join(', ') || '-'
  return String(ips)
}

const loading = ref(false)
const stats = ref({ totalContracts: 0, expiring: 0, expired: 0, reclaimed: 0 })
const expiringContracts = ref<DashboardStats['expiring_contracts']>([])

/** 展开状态映射 */
const expandedMap = reactive<Record<string, boolean>>({})
function toggleExpand(contractId: string) {
  expandedMap[contractId] = !expandedMap[contractId]
}

/** 统计卡片数据 */
const statCards = computed(() => [
  { key: 'total', label: '合同总数', value: stats.value.totalContracts, color: '#409EFF', icon: Document },
  { key: 'expiring', label: '即将到期', value: stats.value.expiring, color: '#E6A23C', icon: Clock },
  { key: 'reclaimed', label: '已回收', value: stats.value.reclaimed, color: '#909399', icon: Checked },
  { key: 'expired', label: '已到期', value: stats.value.expired, color: '#F56C6C', icon: CircleCloseFilled },
])

/** 合同状态标签颜色 */
const contractStatusTagType = (status: string) => {
  const map: Record<string, string> = { active: 'success', expiring: 'warning', expired: 'danger', reclaimed: 'info' }
  return map[status] || 'info'
}
const contractStatusLabel = (status: string) => {
  const map: Record<string, string> = { active: '生效中', expiring: '临期', expired: '已到期', reclaimed: '已回收' }
  return map[status] || status
}

function formatDate(s?: string | null) {
  if (!s) return '-'
  return s.slice(0, 10)
}

const handleSendReminder = async (row: DashboardStats['expiring_contracts'][number]) => {
  const firstRental = row.rentals?.[0]
  if (!firstRental) {
    ElMessage.warning('该合同下无设备，无法发送提醒')
    return
  }
  try {
    await sendExpiryReminder(firstRental.id)
    ElMessage.success('临期提醒已发送')
  } catch {
    ElMessage.error('发送失败')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await getDashboardStats()
    stats.value.totalContracts = data.total_contracts
    stats.value.expiring = data.expiring
    stats.value.reclaimed = (data as any).reclaimed ?? 0
    stats.value.expired = data.expired ?? 0
    expiringContracts.value = data.expiring_contracts || []
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
})
</script>
