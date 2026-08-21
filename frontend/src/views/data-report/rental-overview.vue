<template>
  <div class="page-container rental-overview-page">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="page-header__left">
        <div class="page-header__icon">
          <el-icon :size="18"><Odometer /></el-icon>
        </div>
        <span class="page-header__title">租赁概览</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div
        class="stat-card"
        v-for="card in statCards"
        :key="card.key"
        @click="openContractDialog(card.key)"
      >
        <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
          <el-icon :size="20"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
        </div>
        <span class="stat-card__action">
          查看
          <el-icon :size="12"><ArrowRightBold /></el-icon>
        </span>
      </div>
    </div>

    <!-- 待处理提醒（合同维度） -->
    <div class="panel-card">
      <div class="panel-card__header">
        <span class="panel-card__title">待处理提醒</span>
      </div>
      <div class="panel-card__body" v-loading="loading">
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
                <span class="reminder-date">到期：{{ formatDate(row.end_date) }}</span>
                <el-icon
                  class="expand-arrow"
                  :class="{ expanded: expandedMap[row.contract_id] }"
                  :size="16"
                ><ArrowRightBold /></el-icon>
              </div>
            </div>
            <div class="reminder-body" v-show="expandedMap[row.contract_id]">
              <el-table
                :data="row.rentals || []"
                row-key="id"
                stripe
                style="width: 100%"
              >
                <el-table-column prop="machine_model" label="设备型号" min-width="180" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <span
                      v-if="r.machine_model"
                      class="col-name-link"
                      @click="goRental(r.id)"
                    >{{ r.machine_model }}</span>
                    <span v-else class="col-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="机架位置" min-width="140" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <span v-if="r.rack_location">{{ r.rack_location }}</span>
                    <span v-else class="col-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="公网 IP" min-width="160" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <span v-if="formatIpList(r.public_ips) !== '-'" class="col-ip">{{ formatIpList(r.public_ips) }}</span>
                    <span v-else class="col-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="内网 IP" min-width="140" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <span v-if="r.private_ip" class="col-ip">{{ r.private_ip }}</span>
                    <span v-else class="col-muted">-</span>
                  </template>
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
    </div>

    <!-- 合同列表弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="800px"
      destroy-on-close
    >
      <el-table
        :data="dialogContracts"
        stripe
        v-loading="dialogLoading"
        style="width: 100%"
      >
        <template #empty>
          <div class="table-empty">
            <el-empty description="暂无数据" :image-size="72" />
          </div>
        </template>
        <el-table-column prop="name" label="合同名称" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span
              v-if="row.name"
              class="col-name-link"
              @click="goContractDetail(row.id)"
            >{{ row.name }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="客户" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.customer_name">{{ row.customer_name }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="到期日期" width="120" align="center">
          <template #default="{ row }">
            <span class="col-secondary">{{ formatDate(row.end_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="设备数" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.rental_count != null">{{ row.rental_count }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="contractStatusTagType(row.status)" size="small">{{ contractStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="goContractDetail(row.id)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ============================================================
 * 页面头部
 * ============================================================ */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-header__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  color: #fff;
}

.page-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

/* ============================================================
 * 统计卡片
 * ============================================================ */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--card-bg);
  border-radius: 12px;
  padding: 18px 16px 18px 18px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
  cursor: pointer;
  user-select: none;
}

.stat-card:hover {
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.08), 0 2px 6px rgba(15, 23, 42, 0.04);
  transform: translateY(-2px);
}

.stat-card:hover .stat-card__action {
  color: var(--primary-color);
  opacity: 1;
}

.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.5px;
}

.stat-card__action {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  align-self: flex-start;
  margin-top: 2px;
  padding: 2px 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  opacity: 0.85;
  transition: color 0.2s, opacity 0.2s;
  flex-shrink: 0;
}

/* ============================================================
 * 面板卡片
 * ============================================================ */
.panel-card {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  border: none;
  transition: box-shadow 0.25s ease;
}

.panel-card:hover {
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.08), 0 2px 6px rgba(15, 23, 42, 0.04);
}

.panel-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 4px;
  background: var(--card-bg);
}

.panel-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  position: relative;
  padding-left: 10px;
}

.panel-card__title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--primary-color);
}

.panel-card__body {
  padding: 8px 20px 20px;
}

/* ============================================================
 * 待处理提醒
 * ============================================================ */
.reminder-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reminder-card {
  border: none;
  border-radius: 10px;
  overflow: hidden;
  background: #f8fafc;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.2s;
}

.reminder-card:hover {
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.reminder-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  cursor: pointer;
  user-select: none;
  background: transparent;
  transition: background 0.15s;
}

.reminder-header:hover {
  background: rgba(37, 99, 235, 0.04);
}

.reminder-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.reminder-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.reminder-customer {
  font-size: 13px;
  color: var(--text-secondary);
}

.reminder-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 13px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.reminder-count {
  color: var(--text-secondary);
}

.reminder-date {
  color: var(--warning-color);
  font-weight: 600;
}

.expand-arrow {
  transition: transform 0.2s;
  color: var(--text-secondary);
}

.expand-arrow.expanded {
  transform: rotate(90deg);
}

.reminder-body {
  padding: 4px 18px 16px;
  background: var(--card-bg);
}

.reminder-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

@media (max-width: 768px) {
  .stat-value {
    font-size: 22px;
  }

  .reminder-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .reminder-meta {
    width: 100%;
    justify-content: flex-start;
  }
}
.col-name-link {
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
}
.col-name-link:hover {
  color: var(--primary-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.col-ip {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: var(--text-primary);
}
.col-secondary {
  color: var(--text-secondary);
}
.col-muted {
  color: #c0c4cc;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Odometer, Document, Clock, Checked, CircleCloseFilled, ArrowRightBold } from '@element-plus/icons-vue'
import { getDashboardStats, listContracts, type DashboardStats, type ContractItem, type ContractStatus } from '@/api/modules/contract'
import { sendExpiryReminder } from '@/api/modules/rental'

const router = useRouter()
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

/** 统计卡片数据（配色对齐全局主题） */
const statCards = computed(() => [
  { key: 'total', label: '合同总数', value: stats.value.totalContracts, color: '#2563EB', bg: 'rgba(37, 99, 235, 0.1)', icon: Document },
  { key: 'expiring', label: '即将到期', value: stats.value.expiring, color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', icon: Clock },
  { key: 'reclaimed', label: '已回收', value: stats.value.reclaimed, color: '#64748b', bg: 'rgba(100, 116, 139, 0.1)', icon: Checked },
  { key: 'expired', label: '已到期', value: stats.value.expired, color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', icon: CircleCloseFilled },
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

// ============================================================
// 合同列表弹窗
// ============================================================
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogContracts = ref<ContractItem[]>([])
const dialogLoading = ref(false)

async function openContractDialog(type: string) {
  const titleMap: Record<string, string> = {
    total: '全部合同',
    expiring: '即将到期合同',
    expired: '已到期合同',
    reclaimed: '已回收合同',
  }
  dialogTitle.value = titleMap[type] || '合同列表'
  dialogVisible.value = true
  dialogLoading.value = true
  try {
    const statusMap: Record<string, string | undefined> = {
      total: undefined,
      expiring: 'expiring',
      expired: 'expired',
      reclaimed: 'reclaimed',
    }
    const { items } = await listContracts({ status: statusMap[type] as ContractStatus | undefined, page: 1, page_size: 100 })
    dialogContracts.value = items
  } catch {
    dialogContracts.value = []
  }
  dialogLoading.value = false
}

function goContractDetail(contractId: string) {
  dialogVisible.value = false
  router.push({ name: 'ContractDetail', params: { id: contractId } })
}

function goRental(id: string) {
  router.push({ name: 'RentalDetail', params: { id } })
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
