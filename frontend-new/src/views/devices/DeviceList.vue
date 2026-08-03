<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">设备管理</h1>
    </div>

    <div class="stats-row">
      <div class="stat-card" @click="statusFilter = ''" :class="{ active: !statusFilter }">
        <div class="stat-label">全部设备</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = '租赁中'" :class="{ active: statusFilter === '租赁中' }">
        <div class="stat-label">租赁中</div>
        <div class="stat-value" style="color: #52C41A;">{{ stats.renting }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = '空闲中'" :class="{ active: statusFilter === '空闲中' }">
        <div class="stat-label">空闲中</div>
        <div class="stat-value" style="color: #1677FF;">{{ stats.idle }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = '已断电'" :class="{ active: statusFilter === '已断电' }">
        <div class="stat-label">已断电</div>
        <div class="stat-value" style="color: #86909C;">{{ stats.poweredOff }}</div>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="page-toolbar-left">
        <el-input
          v-model="keyword"
          placeholder="例如：机器型号、CPU、IP地址"
          clearable
          style="width: 320px"
          @input="onSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="statusFilter" placeholder="设备状态" clearable style="width: 140px; margin-left: 12px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="空闲中" value="空闲中" />
          <el-option label="租赁中" value="租赁中" />
          <el-option label="已断电" value="已断电" />
        </el-select>
      </div>
      <div class="page-toolbar-right">
        <el-button :icon="Setting" @click="showColumnCustomizer = true">列设置</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
        <el-button type="primary" :icon="Plus" @click="router.push('/devices/create')">创建设备</el-button>
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
        <el-table-column v-if="visibleColumns.some(c => c.key === 'machine_model')" prop="machine_model" label="机器型号" min-width="160">
          <template #default="{ row }">
            <div class="device-cell" @click="router.push(`/devices/${row.id}`)">
              <el-icon :size="20" class="device-icon"><Cpu /></el-icon>
              <div>
                <div class="device-name">{{ row.machine_model }}</div>
                <div class="text-xs text-tertiary">{{ row.cpu_model || '-' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'memory_gb')" label="内存" width="100" align="center" sortable="custom">
          <template #default="{ row }">
            <span>{{ row.memory_gb ? row.memory_gb + 'GB' : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'gpu_info')" prop="gpu_info" label="GPU" min-width="160" show-overflow-tooltip />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'private_ip')" prop="private_ip" label="内网IP" width="140" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'rack_location')" prop="rack_location" label="机架位置" width="140" show-overflow-tooltip />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'status')" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'contract_count')" prop="contract_count" label="合同数" width="80" align="center" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'created_at')" prop="created_at" label="创建时间" width="180" sortable="custom" />
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/devices/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="router.push(`/devices/${row.id}/edit`)">编辑</el-button>
            <el-popconfirm title="确定删除该设备？此操作不可恢复。" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无设备数据" style="padding: 60px 20px;">
        <el-button type="primary" @click="router.push('/devices/create')">创建设备</el-button>
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
import { Search, Setting, Download, Plus, Cpu } from '@element-plus/icons-vue'
import { getRentals, deleteRental } from '@/api/rental'
import ColumnCustomizer from '@/components/ColumnCustomizer.vue'
import { useColumnCustomization, useExportExcel } from '@/composables/useTable'

const router = useRouter()

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')
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
  { key: 'machine_model', label: '机器型号', visible: true, pinned: true },
  { key: 'memory_gb', label: '内存', visible: true, pinned: false },
  { key: 'gpu_info', label: 'GPU', visible: true, pinned: false },
  { key: 'private_ip', label: '内网IP', visible: true, pinned: false },
  { key: 'rack_location', label: '机架位置', visible: true, pinned: false },
  { key: 'status', label: '状态', visible: true, pinned: false },
  { key: 'contract_count', label: '合同数', visible: true, pinned: false },
  { key: 'created_at', label: '创建时间', visible: true, pinned: false },
]

const {
  columnStates,
  columnOrder,
  visibleColumns,
  pinnedKeys,
  toggleColumn,
  resetColumns,
} = useColumnCustomization(defaultColumns, 'device-columns')

const showColumnCustomizer = ref(false)

const stats = ref({ total: 0, renting: 0, idle: 0, poweredOff: 0 })

const statusType = (s: string) => ({ '租赁中': 'success', '空闲中': '', '已断电': 'info' }[s] || 'info')

const loadData = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (statusFilter.value) params.status = statusFilter.value

    const res: any = await getRentals(params)
    list.value = res.items || res
    total.value = res.total || 0

    stats.value.total = total.value
    stats.value.renting = list.value.filter((d: any) => d.status === '租赁中').length
    stats.value.idle = list.value.filter((d: any) => d.status === '空闲中').length
    stats.value.poweredOff = list.value.filter((d: any) => d.status === '已断电').length
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const onSortChange = () => { loadData() }
const onSelectionChange = (rows: any[]) => { selectedRows.value = rows }

const handleDelete = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除该设备？此操作不可恢复。', '删除确认', { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' })
    await deleteRental(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* ignore */ }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个设备？此操作不可恢复。`, '批量删除', { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' })
    for (const row of selectedRows.value) {
      await deleteRental(row.id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    loadData()
  } catch { /* ignore */ }
}

const { exportExcel } = useExportExcel(list, defaultColumns.filter(c => c.key !== 'selection'), '设备列表')
const handleExport = () => {
  if (list.value.length === 0) { ElMessage.warning('暂无数据可导出'); return }
  exportExcel()
  ElMessage.success('导出成功')
}

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
.device-cell {
  display: flex; align-items: center; gap: 12px; cursor: pointer;
  &:hover .device-name { color: #1677ff; }
}
.device-icon { color: #1677ff; }
.device-name { font-weight: 500; color: var(--color-text-primary); transition: color 0.15s; }
.pagination-wrapper {
  padding: 16px 20px; display: flex; justify-content: flex-end;
  border-top: 1px solid var(--color-border-light);
}
</style>