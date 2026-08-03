<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">合同管理</h1>
    </div>

    <div class="stats-row">
      <div class="stat-card" @click="statusFilter = ''" :class="{ active: !statusFilter }">
        <div class="stat-label">全部合同</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'active'" :class="{ active: statusFilter === 'active' }">
        <div class="stat-label">生效中</div>
        <div class="stat-value" style="color: #52C41A;">{{ stats.active }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'expiring'" :class="{ active: statusFilter === 'expiring' }">
        <div class="stat-label">即将到期</div>
        <div class="stat-value" style="color: #FAAD14;">{{ stats.expiring }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'expired'" :class="{ active: statusFilter === 'expired' }">
        <div class="stat-label">已过期</div>
        <div class="stat-value" style="color: #FF4D4F;">{{ stats.expired }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">合同总金额</div>
        <div class="stat-value" style="color: #1677FF; font-size: 22px;">¥{{ formatAmount(stats.totalAmount) }}</div>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="page-toolbar-left">
        <el-input
          v-model="keyword"
          placeholder="例如：合同名称、编号、客户名称"
          clearable
          style="width: 340px"
          @input="onSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="statusFilter" placeholder="合同状态" clearable style="width: 140px; margin-left: 12px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="生效" value="active" />
          <el-option label="即将到期" value="expiring" />
          <el-option label="已过期" value="expired" />
          <el-option label="已回收" value="reclaimed" />
        </el-select>
        <el-select v-model="customerFilter" placeholder="客户筛选" clearable filterable style="width: 200px; margin-left: 12px" @change="loadData">
          <el-option label="全部客户" value="" />
          <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>
      <div class="page-toolbar-right">
        <el-button :icon="Setting" @click="showColumnCustomizer = true">列设置</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
        <el-button type="primary" :icon="Plus" @click="router.push('/contracts/satellite/create')">新建合同</el-button>
      </div>
    </div>

    <div v-if="selectedRows.length > 0" class="batch-bar">
      <span class="batch-text">已选择 {{ selectedRows.length }} 项</span>
      <el-button type="danger" text @click="handleBatchDelete">批量删除</el-button>
      <el-button text @click="selectedRows = []">取消选择</el-button>
    </div>

    <div class="content-card" style="padding: 0;">
      <el-table
        :data="list"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="onSelectionChange"
        @sort-change="onSortChange"
      >
        <el-table-column v-if="visibleColumns.some(c => c.key === 'selection')" type="selection" width="48" align="center" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'contract_no')" prop="contract_no" label="合同编号" width="160" sortable="custom" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'name')" prop="name" label="合同名称" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="contract-title" @click="router.push(`/contracts/satellite/${row.id}`)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'customer_name')" prop="customer_name" label="客户" width="140" show-overflow-tooltip />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'amount')" prop="amount" label="合同金额" width="130" sortable="custom" align="right">
          <template #default="{ row }">
            <span class="amount">{{ row.amount ? '¥' + formatAmount(row.amount) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'billing_model')" label="计费方式" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="light">{{ billingLabel(row.billing_model) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'start_date')" prop="start_date" label="开始日期" width="120" sortable="custom" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'end_date')" prop="end_date" label="结束日期" width="120" sortable="custom" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'rental_count')" prop="rental_count" label="设备数" width="80" align="center" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'status')" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'created_at')" prop="created_at" label="创建时间" width="180" sortable="custom" />
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/contracts/satellite/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="router.push(`/contracts/satellite/${row.id}/edit`)">编辑</el-button>
            <el-dropdown trigger="click" @command="(cmd: string) => handleMore(cmd, row)">
              <el-button link type="primary">
                更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="renew">续期</el-dropdown-item>
                  <el-dropdown-item command="attachments">附件管理</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无合同数据" style="padding: 60px 20px;">
        <el-button type="primary" @click="router.push('/contracts/satellite/create')">新建合同</el-button>
      </el-empty>

      <div v-if="list.length > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <ColumnCustomizer
      v-model:visible="showColumnCustomizer"
      :columns="columnStates"
      :column-order="columnOrder"
      :pinned-keys="pinnedKeys"
      @toggle="toggleColumn"
      @reset="resetColumns"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Setting, Download, Plus, ArrowDown } from '@element-plus/icons-vue'
import { getContracts, deleteContract } from '@/api/contract'
import { getCustomers } from '@/api/customer'
import ColumnCustomizer from '@/components/ColumnCustomizer.vue'
import { useColumnCustomization, useExportExcel } from '@/composables/useTable'

const router = useRouter()

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')
const customerFilter = ref('')
const selectedRows = ref<any[]>([])
const customers = ref<any[]>([])

const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null
const onSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
}

const defaultColumns = [
  { key: 'selection', label: '选择', visible: false, pinned: false },
  { key: 'contract_no', label: '合同编号', visible: true, pinned: true },
  { key: 'name', label: '合同名称', visible: true, pinned: true },
  { key: 'customer_name', label: '客户', visible: true, pinned: false },
  { key: 'amount', label: '合同金额', visible: true, pinned: false },
  { key: 'billing_model', label: '计费方式', visible: true, pinned: false },
  { key: 'start_date', label: '开始日期', visible: true, pinned: false },
  { key: 'end_date', label: '结束日期', visible: true, pinned: false },
  { key: 'rental_count', label: '设备数', visible: true, pinned: false },
  { key: 'status', label: '状态', visible: true, pinned: false },
  { key: 'created_at', label: '创建时间', visible: true, pinned: false },
]

const {
  columnStates,
  columnOrder,
  visibleColumns,
  pinnedKeys,
  toggleColumn,
  resetColumns,
} = useColumnCustomization(defaultColumns, 'satellite-contract-columns')

const showColumnCustomizer = ref(false)

const stats = ref({ total: 0, active: 0, expiring: 0, expired: 0, totalAmount: 0 })

const formatAmount = (amount: number | string) => {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  return num ? num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) : '0'
}

const statusType = (s: string) => ({ active: 'success', expiring: 'warning', expired: 'danger', reclaimed: 'info' }[s] || 'info')
const statusLabel = (s: string) => ({ active: '生效', expiring: '即将到期', expired: '已过期', reclaimed: '已回收' }[s] || s)
const billingLabel = (s: string) => ({ monthly: '月付', quarterly: '季付', yearly: '年付' }[s] || s)

const loadData = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (statusFilter.value) params.status = statusFilter.value
    if (customerFilter.value) params.customer_id = customerFilter.value

    const res: any = await getContracts(params)
    list.value = res.items || res
    total.value = res.total || 0

    stats.value.total = total.value
    stats.value.active = list.value.filter((c: any) => c.status === 'active').length
    stats.value.expiring = list.value.filter((c: any) => c.status === 'expiring').length
    stats.value.expired = list.value.filter((c: any) => c.status === 'expired').length
    stats.value.totalAmount = list.value.reduce((sum: number, c: any) => sum + (parseFloat(c.amount) || 0), 0)
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const loadCustomers = async () => {
  try {
    const res: any = await getCustomers({ page: 1, page_size: 1000 })
    customers.value = res.items || res
  } catch { /* ignore */ }
}

const onSortChange = () => { loadData() }
const onSelectionChange = (rows: any[]) => { selectedRows.value = rows }

const handleMore = (command: string, row: any) => {
  if (command === 'renew') {
    router.push(`/contracts/satellite/${row.id}/renew`)
  } else if (command === 'attachments') {
    router.push(`/contracts/satellite/${row.id}/attachments`)
  } else if (command === 'delete') {
    handleDelete(row.id)
  }
}

const handleDelete = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除该合同？此操作不可恢复。', '删除确认', { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' })
    await deleteContract(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* ignore */ }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个合同？此操作不可恢复。`, '批量删除', { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' })
    for (const row of selectedRows.value) {
      await deleteContract(row.id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    loadData()
  } catch { /* ignore */ }
}

const { exportExcel } = useExportExcel(list, defaultColumns.filter(c => c.key !== 'selection'), '合同列表')
const handleExport = () => {
  if (list.value.length === 0) { ElMessage.warning('暂无数据可导出'); return }
  exportExcel()
  ElMessage.success('导出成功')
}

onMounted(() => { loadData(); loadCustomers() })
</script>

<style scoped lang="scss">
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.15s;
  &:hover { border-color: #1677ff; box-shadow: 0 2px 8px rgba(22, 119, 255, 0.08); }
  &.active { border-color: #1677ff; background: #f0f7ff; }
}
.stat-label { font-size: 13px; color: #86909C; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1f2329; line-height: 1; }
.batch-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 20px; background: #e6f4ff; border: 1px solid #91caff; border-radius: 8px; margin-bottom: 12px;
}
.batch-text { font-size: 13px; color: #1677ff; font-weight: 500; }
.contract-title { color: #1677ff; cursor: pointer; font-weight: 500; &:hover { text-decoration: underline; } }
.amount { font-weight: 600; font-variant-numeric: tabular-nums; }
.pagination-wrapper {
  padding: 16px 20px; display: flex; justify-content: flex-end;
  border-top: 1px solid var(--color-border-light);
}
</style>