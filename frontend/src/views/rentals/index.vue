<script setup lang="ts">
/**
 * 租赁记录 - 列表页
 *
 * 功能：
 *  - 分页 + 多条件筛选（状态 / 客户 / 关键词搜索）
 *  - 状态用 el-tag 颜色区分
 *  - 通过「详情」按钮进入详情页（不再支持行点击跳转）
 *  - 行内操作：编辑、删除（带确认）
 *  - 表格列自定义：齿轮按钮弹出列设置面板，列显示状态持久化到 localStorage
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Search, Operation as OperationIcon } from '@element-plus/icons-vue'
import {
  deleteRental,
  getRentals,
  updateRental,
  type RentalListItem,
  type RentalListParams,
  type RentalStatus,
} from '@/api/modules/rental'
import { getCustomers, type Customer } from '@/api/modules/customer'
import { BILLING_MODEL_LABEL, safeStatusLabel, safeStatusTagType } from '@/lib/rental'

const router = useRouter()

/** 搜索字段标签枚举：决定 searchText 走哪一个查询参数 */
type SearchField = 'machine_model' | 'private_ip' | 'public_ip' | 'rack_location'

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<RentalListItem[]>([])
const total = ref(0)

// 筛选条件（query 中下拉类筛选用 '' 表示「全部」，发送时跳过）
const searchText = ref('')
/** 当前搜索字段（默认机器型号） */
const searchField = ref<SearchField>('machine_model')
const statusFilter = ref<RentalStatus | ''>('')
const customerFilter = ref('')

const pagination = reactive({
  page: 1,
  page_size: 20,
})

const STATUS_OPTIONS: Array<{ label: string; value: RentalStatus }> = [
  { label: '空闲中', value: '空闲中' },
  { label: '已断电', value: '已断电' },
  { label: '租赁中', value: '租赁中' },
]

/** 搜索字段标签选项 */
const SEARCH_FIELD_OPTIONS: Array<{ label: string; value: SearchField }> = [
  { label: '机器型号', value: 'machine_model' },
  { label: '内网 IP', value: 'private_ip' },
  { label: '公网 IP', value: 'public_ip' },
  { label: '机架位置', value: 'rack_location' },
]

// 客户下拉
const customerOptions = ref<Customer[]>([])
async function loadCustomerOptions() {
  try {
    const res = await getCustomers({ page: 1, page_size: 100 })
    customerOptions.value = res.items.filter((c) => c.status === 'active')
  } catch (e) {
    // 错误已统一处理
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    fetchList()
  }, 300)
}

/**
 * 搜索字段切换：清空文本输入 + 重新拉取列表
 * 约束：搜索标签切换时清空文本输入
 */
function handleSearchFieldChange() {
  searchText.value = ''
  pagination.page = 1
  fetchList()
}

function handleFilterChange() {
  pagination.page = 1
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params: RentalListParams = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (customerFilter.value) params.customer_id = customerFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const trimmed = searchText.value.trim()
    if (trimmed) {
      // 根据当前选中的搜索字段，把文本塞到对应参数上
      if (searchField.value === 'machine_model') {
        params.search = trimmed
      } else if (searchField.value === 'private_ip') {
        params.private_ip = trimmed
      } else if (searchField.value === 'public_ip') {
        params.public_ip = trimmed
      } else if (searchField.value === 'rack_location') {
        params.rack_location = trimmed
      }
    }
    const res = await getRentals(params)
    list.value = res.items
    total.value = res.total
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
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
// 行点击 / 操作
// ============================================================
function goEdit(row: RentalListItem) {
  router.push({ name: 'RentalEdit', params: { id: row.id } })
}

function goCreate() {
  router.push({ name: 'RentalCreate' })
}

async function handleDelete(row: RentalListItem) {
  try {
    await deleteRental(row.id)
    ElMessage.success('已删除设备')
    if (list.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    fetchList()
  } catch (e) {
    // 错误已统一处理
  }
}

// ============================================================
// 状态点击切换
// ============================================================
async function toggleStatus(row: RentalListItem) {
  const newStatus = row.status === '空闲中' ? '已断电' : '空闲中'
  try {
    await updateRental(row.id, { status: newStatus })
    row.status = newStatus
    ElMessage.success(`状态已更新为「${newStatus}」`)
  } catch {
    ElMessage.error('状态更新失败')
  }
}

function formatDate(s?: string | null) {
  if (!s) return '-'
  return s.slice(0, 10)
}

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

/** 到期高亮：3 天内到期显示警示色 */
function isExpiring(date?: string | null) {
  if (!date) return false
  const d = new Date(date)
  if (isNaN(d.getTime())) return false
  const now = new Date()
  const diff = Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  return diff <= 3 && diff >= 0
}

/** 状态中文标签（兼容旧状态值） */
function statusLabel(status?: string | null) {
  return safeStatusLabel(status)
}

/** 状态 el-tag 类型（兼容旧状态值） */
function statusTagType(status?: string | null) {
  return safeStatusTagType(status)
}

/** 计费方式中文标签 */
function billingLabel(model?: string | null) {
  if (!model) return '-'
  return BILLING_MODEL_LABEL[model] ?? model
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
  { key: 'customer_name', title: '客户', default: true },
  { key: 'machine_model', title: '机器型号', default: true },
  { key: 'cpu_model', title: 'CPU 型号' },
  { key: 'memory_gb', title: '内存' },
  { key: 'gpu_info', title: 'GPU 信息' },
  { key: 'system_disk_gb', title: '系统盘' },
  { key: 'data_disks', title: '数据盘' },
  { key: 'os_version', title: '操作系统' },
  { key: 'bandwidth_mbps', title: '带宽' },
  { key: 'rack_location', title: '机架位置', default: true },
  { key: 'private_ip', title: '内网 IP' },
  { key: 'public_ips', title: '公网 IP' },
  { key: 'ssh_port', title: 'SSH 端口' },
  { key: 'root_username', title: 'SSH 账号' },
  { key: 'billing_model', title: '计费方式' },
  { key: 'start_date', title: '开通时间' },
  { key: 'end_date', title: '到期时间', default: true },
  { key: 'auto_renew', title: '自动续期' },
  { key: 'remark', title: '备注' },
  { key: 'status', title: '状态', default: true },
  { key: 'created_at', title: '创建时间' },
  { key: 'updated_at', title: '更新时间' },
  { key: 'contacts_count', title: '收件人' },
  { key: 'actions', title: '操作', default: true, required: true },
]

const STORAGE_KEY = 'rental_columns'
const ORDER_STORAGE_KEY = 'rental_column_order'

/** 默认显示列：客户 / 机器型号 / 内网IP / 到期时间 / 状态 / 操作 */
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

/** 按当前顺序排列的列（用于列设置面板） */
const orderedColumns = computed(() => {
  return columnOrder.value
    .map((key) => allColumns.find((c) => c.key === key))
    .filter((c): c is ColumnDef => !!c)
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
  persistColumns(DEFAULT_VISIBLE)
  persistOrder(DEFAULT_ORDER)
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
  if (key === 'customer_name') {
    base.prop = 'customer.name'
    base.label = '客户'
    base['min-width'] = 140
  } else if (key === 'machine_model') {
    base.prop = 'machine_model'
    base.label = '机器型号'
    base['min-width'] = 140
  } else if (key === 'cpu_model') {
    base.prop = 'cpu_model'
    base.label = 'CPU 型号'
    base['min-width'] = 180
    base['show-overflow-tooltip'] = true
  } else if (key === 'gpu_info') {
    base.prop = 'gpu_info'
    base.label = 'GPU 信息'
    base['min-width'] = 180
    base['show-overflow-tooltip'] = true
  } else if (key === 'os_version') {
    base.prop = 'os_version'
    base.label = '操作系统'
    base['min-width'] = 160
    base['show-overflow-tooltip'] = true
  } else if (key === 'rack_location') {
    base.prop = 'rack_location'
    base.label = '机架位置'
    base['min-width'] = 130
    base['show-overflow-tooltip'] = true
  } else if (key === 'private_ip') {
    base.prop = 'private_ip'
    base.label = '内网 IP'
    base['min-width'] = 140
  } else if (key === 'start_date') {
    base.prop = 'start_date'
    base.label = '开通时间'
    base.width = 110
  } else if (key === 'created_at') {
    base.prop = 'created_at'
    base.label = '创建时间'
    base.width = 160
  } else if (key === 'updated_at') {
    base.prop = 'updated_at'
    base.label = '更新时间'
    base.width = 160
  } else if (key === 'remark') {
    base.prop = 'remark'
    base.label = '备注'
    base['min-width'] = 150
    base['show-overflow-tooltip'] = true
  }

  // 特殊列（带自定义 template，仅设置 label / width 等）
  else if (key === 'status') {
    base.label = '状态'
    base.width = 90
  } else if (key === 'end_date') {
    base.label = '到期时间'
    base.width = 110
  } else if (key === 'memory_gb') {
    base.label = '内存'
    base.width = 80
  } else if (key === 'system_disk_gb') {
    base.label = '系统盘'
    base.width = 80
  } else if (key === 'data_disks') {
    base.label = '数据盘'
    base['min-width'] = 150
  } else if (key === 'public_ips') {
    base.label = '公网 IP'
    base['min-width'] = 150
  } else if (key === 'ssh_port') {
    base.label = 'SSH 端口'
    base.width = 90
  } else if (key === 'root_username') {
    base.label = 'SSH 账号'
    base.width = 90
  } else if (key === 'bandwidth_mbps') {
    base.label = '带宽'
    base.width = 100
  } else if (key === 'billing_model') {
    base.label = '计费方式'
    base.width = 90
  } else if (key === 'auto_renew') {
    base.label = '自动续期'
    base.width = 80
  } else if (key === 'contacts_count') {
    base.label = '收件人'
    base.width = 80
  } else if (key === 'actions') {
    base.label = '操作'
    base.width = 200
    base.fixed = 'right'
  }

  return base
}

// ============================================================
// 勾选复制：单选模式
// ============================================================
const selectedRow = ref<RentalListItem | null>(null)

/**
 * 复选框勾选事件：单选模式
 *  - 已选中再点另一个：取消旧的选新的
 *  - 取消勾选：清空
 */
function handleSelect(selection: RentalListItem[]) {
  if (selection.length === 0) {
    selectedRow.value = null
    return
  }
  // 单选模式：始终只保留最后一个被选中的行
  selectedRow.value = selection[selection.length - 1]
}

/** 跳转到创建页，并带上 copy_from 查询参数 */
function handleCopy() {
  if (!selectedRow.value) return
  router.push({ path: '/rentals/create', query: { copy_from: selectedRow.value.id } })
}

// 兜底：监听 visibleColumns 变化，保证 actions 始终在
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
            设备列表
          </span>
          <div class="header-actions">
            <!-- 列自定义：支持拖拽排序 + 勾选显示 -->
            <el-popover
              v-model:visible="popoverVisible"
              placement="bottom-end"
              :width="260"
              trigger="click"
              popper-class="rental-column-popover"
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
                  <div
                    v-for="col in orderedColumns"
                    :key="col.key"
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
                    <el-checkbox
                      :model-value="vis(col.key)"
                      :disabled="col.required"
                      @change="toggleColumn(col.key)"
                    >
                      {{ col.title }}<span v-if="col.required" class="required-tip">（必选）</span>
                    </el-checkbox>
                  </div>
                </div>
              </div>
            </el-popover>
            <el-button type="primary" @click="goCreate">+ 创建设备</el-button>
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
          <el-option
            v-for="opt in STATUS_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
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
        <!-- 搜索：先选字段标签，再输入文本 -->
        <el-select
          v-model="searchField"
          style="width: 140px"
          @change="handleSearchFieldChange"
        >
          <el-option
            v-for="opt in SEARCH_FIELD_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-input
          v-model="searchText"
          :placeholder="`按${SEARCH_FIELD_OPTIONS.find((o) => o.value === searchField)?.label ?? ''}搜索`"
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
        <el-button :disabled="!selectedRow" @click="handleCopy">复制</el-button>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        row-key="id"
        border
        stripe
        style="width: 100%"
        empty-text="暂无设备"
        @selection-change="handleSelect"
      >
        <!-- 勾选列（单选模式：已选行禁止再勾选别的） -->
        <el-table-column
          type="selection"
          width="50"
          :selectable="(row: RentalListItem) => !selectedRow || selectedRow.id === row.id"
        />

        <!-- 动态列：按 columnOrder 顺序渲染，只渲染可见的 -->
        <template v-for="col in orderedColumns" :key="col.key">
          <el-table-column v-if="vis(col.key)" v-bind="getColumnProps(col)">
            <template v-if="col.key === 'status'" #default="{ row }">
              <el-popconfirm
                v-if="row.status === '空闲中' || row.status === '已断电'"
                :title="row.status === '空闲中' ? '确定将该设备设为「已断电」？' : '确定将该设备设为「空闲中」？'"
                @confirm="toggleStatus(row)"
              >
                <template #reference>
                  <el-tag
                    :type="statusTagType(row.status)"
                    size="small"
                    style="cursor: pointer;"
                  >
                    {{ statusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-popconfirm>
              <el-tooltip
                v-else-if="row.status === '租赁中'"
                content="租赁中状态由合同关联自动管理，不可手动修改"
                placement="top"
              >
                <el-tag :type="statusTagType(row.status)" size="small">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </el-tooltip>
            </template>
            <template v-else-if="col.key === 'end_date'" #default="{ row }">
              <span
                :style="{
                  color: isExpiring(row.end_date) ? 'var(--warning-color)' : '',
                  fontWeight: isExpiring(row.end_date) ? 600 : 400,
                }"
              >
                {{ formatDate(row.end_date) }}
              </span>
            </template>
            <template v-else-if="col.key === 'data_disks'" #default="{ row }">
              <template v-if="Array.isArray((row as any).data_disks) && (row as any).data_disks.length">
                <el-tag
                  v-for="(d, i) in (row as any).data_disks"
                  :key="i"
                  size="small"
                  style="margin-right: 4px"
                >{{ d.size_gb }}GB</el-tag>
              </template>
              <span v-else>-</span>
            </template>
            <template v-else-if="col.key === 'public_ips'" #default="{ row }">
              {{ Array.isArray((row as any).public_ips) ? (row as any).public_ips.join(', ') : '-' }}
            </template>
            <template v-else-if="col.key === 'memory_gb'" #default="{ row }">
              {{ (row as any).memory_gb != null ? (row as any).memory_gb + ' GB' : '-' }}
            </template>
            <template v-else-if="col.key === 'system_disk_gb'" #default="{ row }">
              {{ (row as any).system_disk_gb != null ? (row as any).system_disk_gb + ' GB' : '-' }}
            </template>
            <template v-else-if="col.key === 'bandwidth_mbps'" #default="{ row }">
              {{ (row as any).bandwidth_mbps != null ? (row as any).bandwidth_mbps + ' Mbps' : '-' }}
            </template>
            <template v-else-if="col.key === 'ssh_port'" #default="{ row }">
              {{ (row as any).ssh_port || 22 }}
            </template>
            <template v-else-if="col.key === 'root_username'" #default="{ row }">
              {{ (row as any).root_username || 'root' }}
            </template>
            <template v-else-if="col.key === 'billing_model'" #default="{ row }">
              {{ billingLabel((row as any).billing_model) }}
            </template>
            <template v-else-if="col.key === 'auto_renew'" #default="{ row }">
              {{ (row as any).auto_renew ? '是' : '否' }}
            </template>
            <template v-else-if="col.key === 'contacts_count'" #default="{ row }">
              {{ ((row as any).contacts || []).length }}
            </template>
            <template v-else-if="col.key === 'created_at'" #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
            <template v-else-if="col.key === 'updated_at'" #default="{ row }">
              {{ formatDateTime((row as any).updated_at) }}
            </template>
            <template v-else-if="col.key === 'actions'" #default="{ row }">
              <el-button size="small" link type="primary" @click.stop="$router.push(`/rentals/${row.id}`)">
                详情
              </el-button>
              <el-button size="small" link type="primary" @click.stop="goEdit(row)">
                编辑
              </el-button>
              <el-popconfirm title="确定删除?" @confirm="handleDelete(row)">
                <template #reference>
                  <el-button size="small" link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
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
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
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
/* clickable-row 样式已移除：行点击事件取消 */
</style>

<style>
/* Popover 内容（非 scoped 才能作用到 el-popover 内部生成的 DOM） */
.rental-column-popover .column-popover-body {
  font-size: 13px;
}
.rental-column-popover .column-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--text-secondary, #606266);
  font-weight: 600;
}
.rental-column-popover .column-list {
  max-height: 400px;
  overflow-y: auto;
}
.rental-column-popover .column-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: grab;
  transition: background 0.15s;
}
.rental-column-popover .column-item:hover {
  background: #f3f4f6;
}
.rental-column-popover .column-item.dragging {
  opacity: 0.4;
}
.rental-column-popover .column-item.drag-over {
  border-top: 2px solid #1e40af;
}
.rental-column-popover .drag-handle {
  color: #d1d5db;
  font-size: 16px;
  cursor: grab;
  user-select: none;
  line-height: 1;
}
.rental-column-popover .column-item:active .drag-handle {
  cursor: grabbing;
}
.rental-column-popover .required-tip {
  color: var(--el-color-info, #909399);
  font-size: 12px;
  margin-left: 4px;
}
</style>
