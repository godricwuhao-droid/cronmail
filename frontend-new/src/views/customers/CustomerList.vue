<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">客户管理</h1>
    </div>

    <div class="stats-row">
      <div class="stat-card" @click="filterStatus = ''" :class="{ active: !filterStatus }">
        <div class="stat-label">全部客户</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card" @click="filterStatus = 'active'" :class="{ active: filterStatus === 'active' }">
        <div class="stat-label">活跃客户</div>
        <div class="stat-value" style="color: #52C41A;">{{ stats.active }}</div>
      </div>
      <div class="stat-card" @click="filterStatus = 'inactive'" :class="{ active: filterStatus === 'inactive' }">
        <div class="stat-label">非活跃</div>
        <div class="stat-value" style="color: #86909C;">{{ stats.inactive }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总合同数</div>
        <div class="stat-value" style="color: #1677FF;">{{ stats.totalContracts }}</div>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="page-toolbar-left">
        <el-input
          v-model="keyword"
          placeholder="例如：客户名称、编码"
          clearable
          style="width: 320px"
          @input="onSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px; margin-left: 12px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="活跃" value="active" />
          <el-option label="非活跃" value="inactive" />
        </el-select>
      </div>
      <div class="page-toolbar-right">
        <el-button :icon="Setting" @click="showColumnCustomizer = true">列设置</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
        <el-button type="primary" :icon="Plus" @click="router.push('/customers/create')">新建客户</el-button>
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
        <el-table-column v-if="visibleColumns.some(c => c.key === 'name')" prop="name" label="客户名称" min-width="200">
          <template #default="{ row }">
            <div class="customer-cell" @click="router.push(`/customers/${row.id}`)">
              <div class="avatar" :style="{ background: avatarColors[row.name.charCodeAt(0) % avatarColors.length] }">
                {{ row.name.charAt(0) }}
              </div>
              <div>
                <div class="customer-name">{{ row.name }}</div>
                <div class="text-xs text-tertiary">{{ row.code }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'business_types')" label="业务类型" min-width="180">
          <template #default="{ row }">
            <div v-if="row.business_types && row.business_types.length" class="tag-group">
              <el-tag v-for="bt in row.business_types" :key="bt" size="small" effect="light">{{ bt }}</el-tag>
            </div>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'contact_count')" prop="contact_count" label="联系人" width="90" align="center" sortable="custom" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'contract_stats')" label="合同统计" width="160" align="center">
          <template #default="{ row }">
            <span class="text-xs">共{{ row.contract_stats?.total || 0 }} / 生效{{ row.contract_stats?.active || 0 }} / 过期{{ row.contract_stats?.expired || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'status')" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '活跃' : '非活跃' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'created_at')" prop="created_at" label="创建时间" width="180" sortable="custom" />
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/customers/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="router.push(`/customers/${row.id}/edit`)">编辑</el-button>
            <el-popconfirm title="确定删除该客户？此操作不可恢复。" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无客户数据" style="padding: 60px 20px;">
        <el-button type="primary" @click="router.push('/customers/create')">新建客户</el-button>
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
import { Search, Setting, Download, Plus } from '@element-plus/icons-vue'
import { getCustomers, deleteCustomer } from '@/api/customer'
import ColumnCustomizer from '@/components/ColumnCustomizer.vue'
import { useColumnCustomization, useExportExcel } from '@/composables/useTable'

const router = useRouter()

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterStatus = ref('')
const selectedRows = ref<any[]>([])

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
  { key: 'name', label: '客户名称', visible: true, pinned: true },
  { key: 'business_types', label: '业务类型', visible: true, pinned: false },
  { key: 'contact_count', label: '联系人', visible: true, pinned: false },
  { key: 'contract_stats', label: '合同统计', visible: true, pinned: false },
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
} = useColumnCustomization(defaultColumns, 'customer-columns')

const showColumnCustomizer = ref(false)

const stats = ref({
  total: 0,
  active: 0,
  inactive: 0,
  totalContracts: 0,
})

const loadData = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value) params.status = filterStatus.value

    const res: any = await getCustomers(params)
    list.value = res.items || res
    total.value = res.total || 0

    stats.value.total = total.value
    stats.value.active = list.value.filter((c: any) => c.status === 'active').length
    stats.value.inactive = list.value.filter((c: any) => c.status !== 'active').length
    stats.value.totalContracts = list.value.reduce((sum: number, c: any) => sum + (c.contract_stats?.total || 0), 0)
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const onSortChange = () => { loadData() }
const onSelectionChange = (rows: any[]) => { selectedRows.value = rows }

const handleDelete = async (id: string) => {
  try {
    await deleteCustomer(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* ignore */ }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个客户？此操作不可恢复。`, '批量删除', { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' })
    for (const row of selectedRows.value) {
      await deleteCustomer(row.id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    loadData()
  } catch { /* ignore */ }
}

const { exportExcel } = useExportExcel(list, defaultColumns.filter(c => c.key !== 'selection'), '客户列表')
const handleExport = () => {
  if (list.value.length === 0) { ElMessage.warning('暂无数据可导出'); return }
  exportExcel()
  ElMessage.success('导出成功')
}

const avatarColors = ['#1677FF', '#52C41A', '#FAAD14', '#FF4D4F', '#13C2C2', '#722ED1']

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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
.customer-cell {
  display: flex; align-items: center; gap: 12px; cursor: pointer;
  &:hover .customer-name { color: #1677ff; }
}
.avatar {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 14px; color: white; flex-shrink: 0;
}
.customer-name { font-weight: 500; color: var(--color-text-primary); transition: color 0.15s; }
.tag-group { display: flex; gap: 4px; flex-wrap: wrap; }
.pagination-wrapper {
  padding: 16px 20px; display: flex; justify-content: flex-end;
  border-top: 1px solid var(--color-border-light);
}
</style>