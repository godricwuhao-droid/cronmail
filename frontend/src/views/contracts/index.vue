<script setup lang="ts">
/**
 * 合同管理 - 列表页
 *
 * 功能：
 *  - 分页 + 多条件筛选（合同名称模糊搜索、客户、状态）
 *  - 状态用 el-tag 颜色区分
 *  - 行内操作：详情、编辑、删除（带确认）
 *  - 「+ 新建合同」按钮跳转 /contracts/create
 *  - 列自定义：齿轮按钮弹出列设置面板，支持拖拽排序 + 置顶 + 勾选显示（持久化到 localStorage）
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Download, Operation as OperationIcon, Search, Top } from '@element-plus/icons-vue'
import {
  deleteContract,
  listContracts,
  type ContractItem,
  type ContractListParams,
  type ContractStatus,
} from '@/api/modules/contract'
import { getCustomers, type Customer } from '@/api/modules/customer'
import {
  CONTRACT_BILLING_MODEL_LABEL,
  CONTRACT_STATUS_LABEL,
  CONTRACT_STATUS_TAG,
} from '@/lib/contract'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const router = useRouter()

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<ContractItem[]>([])
const total = ref(0)

const searchText = ref('')
const statusFilter = ref<ContractStatus | ''>('')
const customerFilter = ref('')

const pagination = reactive({
  page: 1,
  page_size: 20,
})

// 客户下拉（仅展示 active 客户 + 业务类型为「算力租赁」）
const customerOptions = ref<Customer[]>([])
async function loadCustomerOptions() {
  try {
    const res = await getCustomers({ business_type: '算力租赁', page: 1, page_size: 100 })
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

async function fetchList() {
  loading.value = true
  try {
    const params: ContractListParams = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (customerFilter.value) params.customer_id = customerFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const res = await listContracts(params)
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

async function loadSummaries(items: ContractItem[]) {
  for (const item of items) {
    try {
      const summary = await getAttachmentSummary('compute_leasing', item.id)
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
function goDetail(row: ContractItem) {
  router.push({ name: 'ContractDetail', params: { id: row.id } })
}

function goEdit(row: ContractItem) {
  router.push({ name: 'ContractEdit', params: { id: row.id } })
}

function goCreate() {
  router.push({ name: 'ContractCreate' })
}

async function handleDelete(row: ContractItem) {
  try {
    await deleteContract(row.id)
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
// 附件状态辅助
// ============================================================
function goAttachments(row: ContractItem) {
  router.push({ name: 'ComputeLeasingAttachments', params: { id: row.id } })
}

function statusDotColor(summary: AttachmentSummary | undefined, code: string): string {
  if (!summary) return '#c0c4cc'
  const item = summary.items[code]
  if (!item || item.file_count === 0) return '#c0c4cc'
  return item.confirmed ? '#10b981' : '#ef4444'
}

function statusDotTitle(summary: AttachmentSummary | undefined, code: string): string {
  if (!summary) return '加载中...'
  const item = summary.items[code]
  if (!item || item.file_count === 0) return '未上传'
  return item.confirmed ? `已确认 (${item.file_count} 个文件)` : `未确认 (${item.file_count} 个文件)`
}

function getSummary(row: ContractItem): AttachmentSummary | undefined {
  return summaryMap.value[row.id]
}

// ============================================================
// 展示辅助
// ============================================================
function statusLabel(s?: string | null) {
  if (!s) return '-'
  return CONTRACT_STATUS_LABEL[s as ContractStatus] ?? s
}
function statusTagType(s?: string | null) {
  if (!s) return 'info'
  return CONTRACT_STATUS_TAG[s as ContractStatus] ?? 'info'
}
function billingLabel(s?: string | null) {
  if (!s) return '-'
  return CONTRACT_BILLING_MODEL_LABEL[s] ?? s
}
function formatDate(s?: string | null) {
  if (!s) return '-'
  return s.length >= 10 ? s.slice(0, 10) : s
}

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

// ============================================================
// 列自定义
// ============================================================
interface ColumnDef {
  key: string
  title: string
  default?: boolean
  required?: boolean
}

const allColumns: ColumnDef[] = [
  { key: 'name', title: '合同名称', default: true },
  { key: 'customer_name', title: '客户', default: true },
  { key: 'contract_no', title: '合同编号' },
  { key: 'sort_order', title: '序号' },
  { key: 'amount', title: '合同金额' },
  { key: 'start_date', title: '开始日期' },
  { key: 'end_date', title: '到期日期', default: true },
  { key: 'billing_model', title: '计费方式' },
  { key: 'rental_count', title: '设备数' },
  { key: 'status', title: '状态', default: true },
  { key: 'attachment_status', title: '附件状态', default: true },
  { key: 'remark', title: '备注' },
  { key: 'created_at', title: '创建时间' },
  { key: 'updated_at', title: '更新时间' },
  { key: 'actions', title: '操作', default: true, required: true },
]

const STORAGE_KEY = 'contract_columns'
const ORDER_STORAGE_KEY = 'contract_column_order'

/** 默认显示列 */
const DEFAULT_VISIBLE: string[] = allColumns
  .filter((c) => c.default)
  .map((c) => c.key)

/** 默认列顺序：与 allColumns 声明顺序一致 */
const DEFAULT_ORDER: string[] = allColumns.map((c) => c.key)

function loadVisibleColumns(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return [...DEFAULT_VISIBLE]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...DEFAULT_VISIBLE]
    // 过滤掉无效 key，且保证 required（操作）列始终存在
    const valid = parsed.filter(
      (k): k is string => typeof k === 'string' && allColumns.some((c) => c.key === k),
    )
    if (!valid.includes('actions')) valid.push('actions')
    return valid
  } catch {
    return [...DEFAULT_VISIBLE]
  }
}

function loadColumnOrder(): string[] {
  try {
    const raw = localStorage.getItem(ORDER_STORAGE_KEY)
    if (!raw) return [...DEFAULT_ORDER]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...DEFAULT_ORDER]
    // 过滤掉无效 key，缺失的补在尾部，未知的多余项丢弃
    const valid = parsed.filter(
      (k): k is string => typeof k === 'string' && allColumns.some((c) => c.key === k),
    )
    // 缺失列补上
    for (const c of allColumns) {
      if (!valid.includes(c.key)) valid.push(c.key)
    }
    return valid
  } catch {
    return [...DEFAULT_ORDER]
  }
}

const visibleColumns = ref<string[]>(loadVisibleColumns())
/** 列顺序（从 localStorage 读取或默认） */
const columnOrder = ref<string[]>(loadColumnOrder())
const popoverVisible = ref(false)

/** 置顶列（按 pin 顺序排列，最新的在最前） */
const PIN_STORAGE_KEY = 'contract_pinned_columns'
const DEFAULT_PINNED = ['name', 'status', 'amount']

function loadPinned(): string[] {
  try {
    const raw = localStorage.getItem(PIN_STORAGE_KEY)
    if (!raw) return [...DEFAULT_PINNED]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...DEFAULT_PINNED]
    return parsed.filter(
      (k): k is string => typeof k === 'string' && allColumns.some((c) => c.key === k),
    )
  } catch {
    return [...DEFAULT_PINNED]
  }
}
function persistPinned(val: string[]) {
  localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify(val))
}

const pinnedColumns = ref<string[]>(loadPinned())

function pinColumn(key: string) {
  const idx = pinnedColumns.value.indexOf(key)
  if (idx > -1) {
    pinnedColumns.value.splice(idx, 1)
  } else {
    pinnedColumns.value.unshift(key)
  }
  persistPinned(pinnedColumns.value)
}
function isPinned(key: string) {
  return pinnedColumns.value.includes(key)
}

/** 按当前顺序排列的列（用于列设置面板），置顶列排在前面，用分割线隔开 */
const orderedColumns = computed(() => {
  const all = columnOrder.value
    .map((key) => allColumns.find((c) => c.key === key))
    .filter((c): c is ColumnDef => !!c)
  const pinned = all.filter((c) => isPinned(c.key))
  const unpinned = all.filter((c) => !isPinned(c.key))
  return [...pinned, ...unpinned]
})

/** 拖拽状态 */
const dragKey = ref<string>('')
const dragOverKey = ref<string>('')

function vis(key: string) {
  return visibleColumns.value.includes(key)
}

/** 持久化当前可见列 */
function persistColumns(val: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
}

/** 持久化当前列顺序 */
function persistOrder(val: string[]) {
  localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(val))
}

/**
 * 处理列勾选变化
 * - 操作列（actions）必选，不可取消
 * - 至少需要保留一列可见（actions 本身算一列，所以至少要剩 actions）
 */
function guardRequired(next: string[]) {
  // 1. 全空：兜底保留 actions
  if (next.length === 0) {
    visibleColumns.value = ['actions']
    ElMessage.warning('至少需要保留一列可见')
    persistColumns(visibleColumns.value)
    return
  }

  // 2. 过滤非法 key，强制保留 actions
  const valid = next.filter((k) => allColumns.some((c) => c.key === k))
  if (!valid.includes('actions')) {
    valid.push('actions')
    ElMessage.warning('操作列不可取消')
  }

  visibleColumns.value = valid
  persistColumns(valid)
}

/** 切换某一列的可见性 */
function toggleColumn(key: string) {
  if (allColumns.find((c) => c.key === key)?.required) return
  const idx = visibleColumns.value.indexOf(key)
  if (idx >= 0) {
    visibleColumns.value.splice(idx, 1)
  } else {
    visibleColumns.value.push(key)
  }
  // 走 guard 保证 actions 始终存在
  guardRequired(visibleColumns.value)
}

function resetColumns() {
  visibleColumns.value = [...DEFAULT_VISIBLE]
  columnOrder.value = [...DEFAULT_ORDER]
  pinnedColumns.value = [...DEFAULT_PINNED]
  persistColumns(DEFAULT_VISIBLE)
  persistOrder(DEFAULT_ORDER)
  persistPinned(DEFAULT_PINNED)
  ElMessage.success('已恢复默认列设置')
}

// ============================================================
// 拖拽排序（HTML5 native drag & drop）
// ============================================================
function onDragStart(e: DragEvent, key: string) {
  dragKey.value = key
  dragOverKey.value = ''
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    // 某些浏览器需要 setData 才能正确触发 drop
    try {
      e.dataTransfer.setData('text/plain', key)
    } catch {
      /* 忽略 */
    }
  }
  const el = e.target as HTMLElement | null
  el?.classList.add('dragging')
}

function onDragOver(e: DragEvent, key: string) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  if (key !== dragOverKey.value) dragOverKey.value = key
}

function onDragLeave(key: string) {
  if (dragOverKey.value === key) dragOverKey.value = ''
}

function onDrop(e: DragEvent, targetKey: string) {
  e.preventDefault()
  const from = columnOrder.value.indexOf(dragKey.value)
  const to = columnOrder.value.indexOf(targetKey)
  if (from !== -1 && to !== -1 && from !== to) {
    const arr = [...columnOrder.value]
    arr.splice(from, 1)
    arr.splice(to, 0, dragKey.value)
    columnOrder.value = arr
    persistOrder(arr)
  }
  dragKey.value = ''
  dragOverKey.value = ''
}

function onDragEnd(e: DragEvent) {
  const el = e.target as HTMLElement | null
  el?.classList.remove('dragging')
  dragKey.value = ''
  dragOverKey.value = ''
}

// ============================================================
// 动态列：根据 col.key 返回 el-table-column 的 props
// ============================================================
type ColumnProps = Record<string, unknown>

function getColumnProps(col: ColumnDef): ColumnProps {
  const key = col.key
  const base: ColumnProps = {}

  // 普通文本列（直接走 prop）
  if (key === 'name') {
    base.prop = 'name'
    base.label = '合同名称'
    base['min-width'] = 200
    base['show-overflow-tooltip'] = true
  } else if (key === 'customer_name') {
    base.prop = 'customer_name'
    base.label = '客户'
    base['min-width'] = 160
    base['show-overflow-tooltip'] = true
  } else if (key === 'contract_no') {
    base.prop = 'contract_no'
    base.label = '合同编号'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'sort_order') {
    base.prop = 'sort_order'
    base.label = '序号'
    base.width = 70
    base.align = 'center'
  } else if (key === 'start_date') {
    base.prop = 'start_date'
    base.label = '开始日期'
    base.width = 120
  } else if (key === 'end_date') {
    base.prop = 'end_date'
    base.label = '到期日期'
    base.width = 120
  } else if (key === 'remark') {
    base.prop = 'remark'
    base.label = '备注'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'created_at') {
    base.prop = 'created_at'
    base.label = '创建时间'
    base.width = 170
  } else if (key === 'updated_at') {
    base.prop = 'updated_at'
    base.label = '更新时间'
    base.width = 170
  }

  // 特殊列（带自定义 template，仅设置 label / width 等）
  else if (key === 'status') {
    base.label = '状态'
    base.width = 100
  } else if (key === 'amount') {
    base.label = '合同金额'
    base.width = 120
  } else if (key === 'billing_model') {
    base.label = '计费方式'
    base.width = 100
  } else if (key === 'rental_count') {
    base.label = '设备数'
    base.width = 80
  } else if (key === 'attachment_status') {
    base.label = '附件状态'
    base.width = 140
  } else if (key === 'actions') {
    base.label = '操作'
    base.width = 260
    base.fixed = 'right'
  }

  return base
}

// 兜底：保证 actions 始终存在
watch(
  visibleColumns,
  (val) => {
    if (val.length === 0 || !val.includes('actions')) {
      const fixed = val.length === 0 ? ['actions'] : [...val, 'actions']
      visibleColumns.value = fixed
      persistColumns(fixed)
    }
  },
  { deep: true },
)

// ============================================================
// 导出 Excel
// ============================================================
function handleExport() {
  const params = new URLSearchParams()
  if (customerFilter.value) params.append('customer_id', customerFilter.value)
  if (statusFilter.value) params.append('status', statusFilter.value)
  if (searchText.value.trim()) params.append('search', searchText.value.trim())
  window.open(`/api/contracts/export?${params.toString()}`, '_blank')
}

onMounted(() => {
  loadCustomerOptions()
  fetchList()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Document /></el-icon>
            算力租赁合同
          </span>
          <div class="header-actions">
            <!-- 列自定义：支持拖拽排序 + 置顶 + 勾选显示 -->
            <el-popover
              v-model:visible="popoverVisible"
              placement="bottom-end"
              :width="260"
              trigger="click"
              popper-class="contract-column-popover"
            >
              <template #reference>
                <el-button :icon="OperationIcon" :disabled="loading">列设置</el-button>
              </template>
              <div class="column-popover-body">
                <div class="column-popover-header">
                  <span>拖拽调整顺序 · 勾选显示</span>
                  <el-link type="primary" :underline="false" @click="resetColumns">重置默认</el-link>
                </div>
                <div class="column-list">
                  <template v-for="(col, idx) in orderedColumns" :key="col.key">
                    <div
                      v-if="idx > 0 && isPinned(col.key) !== isPinned(orderedColumns[idx - 1]?.key || '')"
                      class="column-divider"
                    />
                    <div
                      class="column-item"
                      :class="{
                        'drag-over': dragOverKey === col.key && dragKey !== col.key,
                        dragging: dragKey === col.key,
                      }"
                      draggable="true"
                      @dragstart="onDragStart($event, col.key)"
                      @dragover="onDragOver($event, col.key)"
                      @dragleave="onDragLeave(col.key)"
                      @drop="onDrop($event, col.key)"
                      @dragend="onDragEnd"
                    >
                      <span class="drag-handle" aria-hidden="true">⠿</span>
                      <el-button
                        link
                        class="pin-btn"
                        :class="{ active: isPinned(col.key) }"
                        @click="pinColumn(col.key)"
                        :title="isPinned(col.key) ? '取消置顶' : '置顶到最前'"
                      >
                        <el-icon><Top /></el-icon>
                      </el-button>
                      <el-checkbox
                        :model-value="vis(col.key)"
                        :disabled="col.required"
                        @change="toggleColumn(col.key)"
                      >
                        {{ col.title }}<span v-if="col.required" class="required-tip">（必选）</span>
                      </el-checkbox>
                    </div>
                  </template>
                </div>
              </div>
            </el-popover>
            <el-button :icon="Download" @click="handleExport" :disabled="loading">导出</el-button>
            <el-button type="primary" @click="goCreate">+ 新建合同</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="toolbar">
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 140px"
          @change="handleFilterChange"
        >
          <el-option label="生效中" value="active" />
          <el-option label="临期" value="expiring" />
          <el-option label="已到期" value="expired" />
          <el-option label="已回收" value="reclaimed" />
        </el-select>
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
        <el-button @click="fetchList">刷新</el-button>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        row-key="id"
        border
        stripe
        style="width: 100%"
        empty-text="暂无合同"
      >
        <!-- 动态列：按 orderedColumns 顺序渲染，只渲染可见的 -->
        <template v-for="col in orderedColumns" :key="col.key">
          <el-table-column v-if="vis(col.key)" v-bind="getColumnProps(col)">
            <template v-if="col.key === 'name'" #default="{ row }">
              <span>{{ row.name }}{{ row.renewal_seq > 0 ? `(续${row.renewal_seq})` : '' }}</span>
            </template>
            <template v-else-if="col.key === 'sort_order'" #default="{ row }">
              {{ row.sort_order ?? 0 }}
            </template>
            <template v-else-if="col.key === 'status'" #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
            <template v-else-if="col.key === 'amount'" #default="{ row }">
              {{ row.amount != null ? '¥' + row.amount.toLocaleString() : '-' }}
            </template>
            <template v-else-if="col.key === 'start_date'" #default="{ row }">
              {{ formatDate(row.start_date) }}
            </template>
            <template v-else-if="col.key === 'end_date'" #default="{ row }">
              {{ formatDate(row.end_date) }}
            </template>
            <template v-else-if="col.key === 'billing_model'" #default="{ row }">
              {{ billingLabel(row.billing_model) }}
            </template>
            <template v-else-if="col.key === 'rental_count'" #default="{ row }">
              {{ row.rental_count ?? 0 }}
            </template>
            <template v-else-if="col.key === 'attachment_status'" #default="{ row }">
              <el-tooltip
                v-for="code in ['contract_agreement', 'acceptance_material', 'process_material']"
                :key="code"
                :content="statusDotTitle(getSummary(row), code)"
                placement="top"
              >
                <span class="status-dot" :style="{ backgroundColor: statusDotColor(getSummary(row), code) }" />
              </el-tooltip>
            </template>
            <template v-else-if="col.key === 'remark'" #default="{ row }">
              {{ row.remark || '-' }}
            </template>
            <template v-else-if="col.key === 'created_at'" #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
            <template v-else-if="col.key === 'updated_at'" #default="{ row }">
              {{ formatDateTime(row.updated_at) }}
            </template>
            <template v-else-if="col.key === 'actions'" #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" link type="primary" @click="goDetail(row)">详情</el-button>
                <el-button size="small" link type="primary" @click="goEdit(row)">编辑</el-button>
                <el-popconfirm
                  title="确定删除该合同？关联设备不会被删除"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="handleDelete(row)"
                >
                  <template #reference>
                    <el-button size="small" link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
                <el-button size="small" link type="primary" @click="goAttachments(row)">
                  附件
                </el-button>
                <el-tooltip
                  v-if="row.has_renewal"
                  content="已被续期"
                  placement="top"
                >
                  <span class="renewal-indicator">🔗</span>
                </el-tooltip>
                <el-tooltip
                  v-else-if="row.renewed_from_id"
                  content="续期合同"
                  placement="top"
                >
                  <span class="renewal-indicator" style="color: #409eff">🔗</span>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </template>
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
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-header .title {
  font-size: 16px;
  font-weight: 600;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin: 0 2px;
  cursor: default;
}
.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
.renewal-indicator {
  font-size: 14px;
  cursor: default;
  margin-left: 2px;
}
</style>

<style>
/* Popover 内容（非 scoped 才能作用到 el-popover 内部生成的 DOM） */
.contract-column-popover .column-popover-body {
  font-size: 13px;
}
.contract-column-popover .column-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--text-secondary, #606266);
  font-weight: 600;
}
.contract-column-popover .column-list {
  max-height: 400px;
  overflow-y: auto;
}
.contract-column-popover .column-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: grab;
  transition: background 0.15s;
}
.contract-column-popover .column-item:hover {
  background: #f3f4f6;
}
.contract-column-popover .column-item.dragging {
  opacity: 0.4;
}
.contract-column-popover .column-item.drag-over {
  border-top: 2px solid #1e40af;
}
.contract-column-popover .drag-handle {
  color: #d1d5db;
  font-size: 16px;
  cursor: grab;
  user-select: none;
  line-height: 1;
}
.contract-column-popover .column-item:active .drag-handle {
  cursor: grabbing;
}
.contract-column-popover .required-tip {
  color: var(--el-color-info, #909399);
  font-size: 12px;
  margin-left: 4px;
}
.contract-column-popover .pin-btn {
  padding: 2px;
  margin-right: 4px;
  font-size: 14px;
  opacity: 0.3;
}
.contract-column-popover .pin-btn:hover,
.contract-column-popover .pin-btn.active {
  opacity: 1;
  color: var(--primary-color);
}
.contract-column-popover .column-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 6px;
}
</style>
