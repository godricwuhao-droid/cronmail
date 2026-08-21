<script setup lang="ts">
/**
 * 卫星数据合同 - 列表页
 *
 * 功能：
 *  - 分页 + 筛选（客户下拉、搜索框）
 *  - 附件状态汇总展示
 *  - 行内操作：详情、编辑、删除 + 附件下拉
 */
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Download, Search, ArrowDown, Refresh, RefreshLeft } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
import {
  deleteSatelliteContract,
  listSatelliteContracts,
  type SatelliteContractItem,
  type SatelliteContractListParams,
} from '@/api/modules/satellite-contract'
import { getCustomers, type Customer } from '@/api/modules/customer'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const router = useRouter()

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<SatelliteContractItem[]>([])
const total = ref(0)

const searchText = ref('')
const customerFilter = ref('')

const pagination = reactive({
  page: 1,
  page_size: 20,
})

// 客户下拉
const customerOptions = ref<Customer[]>([])
async function loadCustomerOptions() {
  try {
    const res = await getCustomers({ business_type: '卫星数据', page: 1, page_size: 100 })
    customerOptions.value = res.items.filter((c) => c.status === 'active')
  } catch {
    // 错误已统一处理
  }
}

// 附件状态汇总缓存
const summaryMap = ref<Record<string, AttachmentSummary>>({})

let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    fetchList()
  }, 300)
}

function handleFilterChange() {
  pagination.page = 1
  fetchList()
}

const hasFilters = computed(
  () => !!(searchText.value.trim() || customerFilter.value),
)

const emptyDescription = computed(() =>
  hasFilters.value ? '未找到匹配合同' : '暂无合同',
)

function clearFilters() {
  searchText.value = ''
  customerFilter.value = ''
  pagination.page = 1
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params: SatelliteContractListParams = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (customerFilter.value) params.customer_id = customerFilter.value
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const res = await listSatelliteContracts(params)
    list.value = res.items
    total.value = res.total
    // 异步加载附件汇总
    loadSummaries(res.items)
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

async function loadSummaries(items: SatelliteContractItem[]) {
  for (const item of items) {
    try {
      const summary = await getAttachmentSummary('satellite_data', item.id)
      summaryMap.value[item.id] = summary
    } catch {
      // 忽略
    }
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchList()
}

function handleSizeChange(size: number) {
  pagination.page_size = size
  pagination.page = 1
  fetchList()
}

// ============================================================
// 行操作
// ============================================================
function goDetail(row: SatelliteContractItem) {
  router.push({ name: 'SatelliteContractDetail', params: { id: row.id } })
}

function goEdit(row: SatelliteContractItem) {
  router.push({ name: 'SatelliteContractEdit', params: { id: row.id } })
}

function goCreate() {
  router.push({ name: 'SatelliteContractCreate' })
}

function goAttachments(row: SatelliteContractItem) {
  router.push({ name: 'SatelliteDataAttachments', params: { id: row.id } })
}

async function handleDelete(row: SatelliteContractItem) {
  if (!(await confirmDelete('确定删除该合同？'))) return
  try {
    await deleteSatelliteContract(row.id)
    ElMessage.success('合同已删除')
    if (list.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    fetchList()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 展示辅助
// ============================================================
function formatDate(s?: string | null) {
  if (!s) return '-'
  return s.length >= 10 ? s.slice(0, 10) : s
}

/** 附件状态图标颜色 */
function statusDotColor(summary: AttachmentSummary | undefined, code: string): string {
  if (!summary) return '#c0c4cc'
  const item = summary.items[code]
  if (!item || item.file_count === 0) return '#c0c4cc'
  return item.confirmed ? '#10b981' : '#ef4444'
}

/** 附件状态 hover 提示 */
function statusDotTitle(summary: AttachmentSummary | undefined, code: string): string {
  if (!summary) return '加载中...'
  const item = summary.items[code]
  if (!item || item.file_count === 0) return '未上传'
  return item.confirmed ? `已确认 (${item.file_count} 个文件)` : `未确认 (${item.file_count} 个文件)`
}

function getSummary(row: SatelliteContractItem): AttachmentSummary | undefined {
  return summaryMap.value[row.id]
}

// ============================================================
// 导出 Excel
// ============================================================
function handleExport() {
  const params = new URLSearchParams()
  if (customerFilter.value) params.append('customer_id', customerFilter.value)
  if (searchText.value.trim()) params.append('search', searchText.value.trim())
  window.open(`/api/satellite-data-contracts/export?${params.toString()}`, '_blank')
}

onMounted(() => {
  loadCustomerOptions()
  fetchList()
})
</script>

<template>
  <div class="page-container">
    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><DataAnalysis /></el-icon>
          卫星数据合同
        </span>
        <div class="header-actions">
          <el-button type="primary" @click="goCreate">+ 新建合同</el-button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="toolbar">
        <el-select
          v-model="customerFilter"
          placeholder="客户"
          clearable
          filterable
          style="width: 200px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="c in customerOptions"
            :key="c.id"
            :label="c.name"
            :value="c.id"
          />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="按合同名称搜索"
          clearable
          style="width: 260px"
          @input="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button :icon="Refresh" :disabled="loading" @click="fetchList">刷新</el-button>
        <el-button :icon="RefreshLeft" :disabled="!hasFilters" @click="clearFilters">重置</el-button>
        <el-button :icon="Download" @click="handleExport" :disabled="loading">导出</el-button>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        row-key="id"
        stripe
        style="width: 100%"
      >
        <template #empty>
          <div class="table-empty">
            <el-empty :description="emptyDescription" :image-size="72" />
          </div>
        </template>
        <el-table-column prop="name" label="合同名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="col-name-link" @click="goDetail(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="客户" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.customer_name">{{ row.customer_name }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="contract_no" label="合同编号" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.contract_no">{{ row.contract_no }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ row }">
            {{ row.sort_order ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column label="附件状态" width="140" align="center">
          <template #default="{ row }">
            <el-tooltip
              v-for="code in ['contract_agreement', 'acceptance_material', 'process_material']"
              :key="code"
              :content="statusDotTitle(getSummary(row), code)"
              placement="top"
            >
              <span
                class="status-dot"
                :style="{ backgroundColor: statusDotColor(getSummary(row), code) }"
              />
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="创建日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" link type="primary" @click="goDetail(row)">详情</el-button>
              <el-divider direction="vertical" />
              <el-button size="small" link type="primary" @click="goEdit(row)">编辑</el-button>
              <el-divider direction="vertical" />
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
              <el-divider direction="vertical" />
              <el-dropdown trigger="click" @command="goAttachments(row)">
                <el-button size="small" link type="primary">
                  附件 <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item>
                      <span class="status-dot-sm" :style="{ backgroundColor: statusDotColor(getSummary(row), 'contract_agreement') }" />
                      合同协议
                    </el-dropdown-item>
                    <el-dropdown-item>
                      <span class="status-dot-sm" :style="{ backgroundColor: statusDotColor(getSummary(row), 'acceptance_material') }" />
                      交付材料
                    </el-dropdown-item>
                    <el-dropdown-item>
                      <span class="status-dot-sm" :style="{ backgroundColor: statusDotColor(getSummary(row), 'process_material') }" />
                      过程材料
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.card-header .title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.card-header .title .el-icon {
  color: var(--primary-color);
  font-size: 18px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.col-name-link {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
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
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin: 0 2px;
  cursor: default;
}
.status-dot-sm {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.action-buttons {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.action-buttons :deep(.el-button + .el-button) {
  margin-left: 0;
}
.action-buttons :deep(.el-divider--vertical) {
  margin: 0 8px;
  height: 12px;
  border-color: #e5e7eb;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.muted,
.col-muted {
  color: #c0c4cc;
}
</style>
