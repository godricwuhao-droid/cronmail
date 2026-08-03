<script setup lang="ts">
/**
 * 项目管理合同 - 列表页
 *
 * 功能：
 *  - 顶部公司切换（el-radio-group）：fengyun / tianshu / qianxing
 *  - 分页 + 搜索
 *  - 附件状态汇总展示
 *  - 合同类型、金额、日期、服务行数展示
 *  - 行内操作：详情、编辑、删除、附件
 *  - 列自定义：齿轮按钮弹出列设置面板，支持拖拽排序 + 置顶 + 勾选显示（持久化到 localStorage）
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, FolderOpened, Operation as OperationIcon, Search, Top } from '@element-plus/icons-vue'
import {
  deleteProjectContract,
  listProjectContracts,
  type ProjectContractItem,
  type ProjectContractListParams,
  COMPANY_MAP,
  CONTRACT_TYPE_LABEL,
  CONTRACT_TYPE_TAG,
  type ContractType,
} from '@/api/modules/project'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const route = useRoute()
const router = useRouter()

// ============================================================
// 公司切换
// ============================================================
const currentCompany = ref<string>((route.params.company as string) || 'fengyun')

const companyOptions = [
  { label: '蜂云时代', value: 'fengyun' },
  { label: '安徽天枢', value: 'tianshu' },
  { label: '千星控股', value: 'qianxing' },
]

function onCompanyChange(company: string) {
  currentCompany.value = company
  router.replace({ name: 'ProjectList', params: { company } })
  pagination.page = 1
  fetchList()
}

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<ProjectContractItem[]>([])
const total = ref(0)

const searchText = ref('')

const pagination = reactive({
  page: 1,
  page_size: 20,
})

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

async function fetchList() {
  loading.value = true
  try {
    const params: ProjectContractListParams = {
      company: currentCompany.value,
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const res = await listProjectContracts(params)
    list.value = res.items
    total.value = res.total
    loadSummaries(res.items)
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

async function loadSummaries(items: ProjectContractItem[]) {
  for (const item of items) {
    try {
      const summary = await getAttachmentSummary('compute_service', item.id)
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
function goDetail(row: ProjectContractItem) {
  router.push({ name: 'ProjectDetail', params: { company: currentCompany.value, id: row.id } })
}

function goEdit(row: ProjectContractItem) {
  router.push({ name: 'ProjectEdit', params: { company: currentCompany.value, id: row.id } })
}

function goCreate() {
  router.push({ name: 'ProjectCreate', params: { company: currentCompany.value } })
}

function goAttachments(row: ProjectContractItem) {
  router.push({ name: 'ProjectAttachments', params: { company: currentCompany.value, id: row.id } })
}

async function handleDelete(row: ProjectContractItem) {
  try {
    await deleteProjectContract(row.id)
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

function formatAmount(s?: string | null) {
  if (!s) return '-'
  const n = parseFloat(s)
  if (isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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

function getSummary(row: ProjectContractItem): AttachmentSummary | undefined {
  return summaryMap.value[row.id]
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
  { key: 'contract_no', title: '合同编号' },
  { key: 'contract_type', title: '合同类型', default: true },
  { key: 'party_a_name', title: '甲方' },
  { key: 'party_b_name', title: '乙方' },
  { key: 'amount', title: '合同金额', default: true },
  { key: 'start_date', title: '开始日期' },
  { key: 'end_date', title: '结束日期', default: true },
  { key: 'project_name', title: '项目名称' },
  { key: 'project_type', title: '项目类型' },
  { key: 'service_lines_count', title: '服务行数' },
  { key: 'attachment_status', title: '附件状态', default: true },
  { key: 'sort_order', title: '序号' },
  { key: 'remark', title: '备注' },
  { key: 'contract_content', title: '合同内容' },
  { key: 'delivery_requirements', title: '交付要求' },
  { key: 'process_records', title: '过程记录' },
  { key: 'created_at', title: '创建时间' },
  { key: 'actions', title: '操作', default: true, required: true },
]

const STORAGE_KEY = 'project_contract_columns'
const ORDER_STORAGE_KEY = 'project_contract_column_order'
const PIN_STORAGE_KEY = 'project_contract_pinned_columns'

/** 默认显示列 */
const DEFAULT_VISIBLE: string[] = allColumns
  .filter((c) => c.default)
  .map((c) => c.key)

/** 默认列顺序：与 allColumns 声明顺序一致 */
const DEFAULT_ORDER: string[] = allColumns.map((c) => c.key)

/** 默认置顶列 */
const DEFAULT_PINNED = ['name', 'contract_type', 'amount']

function loadVisibleColumns(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return [...DEFAULT_VISIBLE]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...DEFAULT_VISIBLE]
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
    const valid = parsed.filter(
      (k): k is string => typeof k === 'string' && allColumns.some((c) => c.key === k),
    )
    for (const c of allColumns) {
      if (!valid.includes(c.key)) valid.push(c.key)
    }
    return valid
  } catch {
    return [...DEFAULT_ORDER]
  }
}

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

const visibleColumns = ref<string[]>(loadVisibleColumns())
const columnOrder = ref<string[]>(loadColumnOrder())
const pinnedColumns = ref<string[]>(loadPinned())
const popoverVisible = ref(false)

const dragKey = ref<string>('')
const dragOverKey = ref<string>('')

function persistColumns(val: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
}

function persistOrder(val: string[]) {
  localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(val))
}

function persistPinned(val: string[]) {
  localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify(val))
}

function vis(key: string) {
  return visibleColumns.value.includes(key)
}

function isPinned(key: string) {
  return pinnedColumns.value.includes(key)
}

function pinColumn(key: string) {
  const idx = pinnedColumns.value.indexOf(key)
  if (idx > -1) {
    pinnedColumns.value.splice(idx, 1)
  } else {
    pinnedColumns.value.unshift(key)
  }
  persistPinned(pinnedColumns.value)
}

function guardRequired(next: string[]) {
  if (next.length === 0) {
    visibleColumns.value = ['actions']
    ElMessage.warning('至少需要保留一列可见')
    persistColumns(visibleColumns.value)
    return
  }
  const valid = next.filter((k) => allColumns.some((c) => c.key === k))
  if (!valid.includes('actions')) {
    valid.push('actions')
    ElMessage.warning('操作列不可取消')
  }
  visibleColumns.value = valid
  persistColumns(valid)
}

function toggleColumn(key: string) {
  if (allColumns.find((c) => c.key === key)?.required) return
  const idx = visibleColumns.value.indexOf(key)
  if (idx >= 0) {
    visibleColumns.value.splice(idx, 1)
  } else {
    visibleColumns.value.push(key)
  }
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

/** 按当前顺序排列的列（用于列设置面板），置顶列排在前面，用分割线隔开 */
const orderedColumns = computed(() => {
  const all = columnOrder.value
    .map((key) => allColumns.find((c) => c.key === key))
    .filter((c): c is ColumnDef => !!c)
  const pinned = all.filter((c) => isPinned(c.key))
  const unpinned = all.filter((c) => !isPinned(c.key))
  return [...pinned, ...unpinned]
})

// ============================================================
// 拖拽排序（HTML5 native drag & drop）
// ============================================================
function onDragStart(e: DragEvent, key: string) {
  dragKey.value = key
  dragOverKey.value = ''
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
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

  if (key === 'name') {
    base.prop = 'name'
    base.label = '合同名称'
    base['min-width'] = 200
    base['show-overflow-tooltip'] = true
  } else if (key === 'contract_no') {
    base.prop = 'contract_no'
    base.label = '合同编号'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'contract_type') {
    base.label = '合同类型'
    base.width = 90
  } else if (key === 'party_a_name') {
    base.prop = 'party_a_name'
    base.label = '甲方'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'party_b_name') {
    base.prop = 'party_b_name'
    base.label = '乙方'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'amount') {
    base.label = '合同金额'
    base.width = 140
  } else if (key === 'start_date') {
    base.prop = 'start_date'
    base.label = '开始日期'
    base.width = 120
  } else if (key === 'end_date') {
    base.prop = 'end_date'
    base.label = '结束日期'
    base.width = 120
  } else if (key === 'project_name') {
    base.prop = 'project_name'
    base.label = '项目名称'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'project_type') {
    base.prop = 'project_type'
    base.label = '项目类型'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'service_lines_count') {
    base.label = '服务行数'
    base.width = 90
  } else if (key === 'attachment_status') {
    base.label = '附件状态'
    base.width = 140
  } else if (key === 'sort_order') {
    base.prop = 'sort_order'
    base.label = '序号'
    base.width = 70
    base.align = 'center'
  } else if (key === 'remark') {
    base.prop = 'remark'
    base.label = '备注'
    base['min-width'] = 140
    base['show-overflow-tooltip'] = true
  } else if (key === 'contract_content') {
    base.prop = 'contract_content'
    base.label = '合同内容'
    base['min-width'] = 160
    base['show-overflow-tooltip'] = true
  } else if (key === 'delivery_requirements') {
    base.prop = 'delivery_requirements'
    base.label = '交付要求'
    base['min-width'] = 160
    base['show-overflow-tooltip'] = true
  } else if (key === 'process_records') {
    base.prop = 'process_records'
    base.label = '过程记录'
    base['min-width'] = 160
    base['show-overflow-tooltip'] = true
  } else if (key === 'created_at') {
    base.prop = 'created_at'
    base.label = '创建时间'
    base.width = 120
  } else if (key === 'actions') {
    base.label = '操作'
    base.width = 280
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
  window.open(`/api/project-contracts/export?company=${currentCompany.value}`, '_blank')
}

// ============================================================
// 监听路由参数变化
// ============================================================
watch(
  () => route.params.company,
  (newCompany) => {
    if (newCompany && newCompany !== currentCompany.value) {
      currentCompany.value = newCompany as string
      pagination.page = 1
      fetchList()
    }
  },
)

onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><FolderOpened /></el-icon>
            项目管理
          </span>
          <div class="header-actions">
            <!-- 列自定义 -->
            <el-popover
              v-model:visible="popoverVisible"
              placement="bottom-end"
              :width="260"
              trigger="click"
              popper-class="project-contract-column-popover"
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

      <!-- 公司切换 -->
      <div class="company-switch">
        <el-radio-group v-model="currentCompany" @change="onCompanyChange">
          <el-radio-button
            v-for="opt in companyOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
        <span class="company-hint">
          当前：{{ COMPANY_MAP[currentCompany] || currentCompany }}
        </span>
      </div>

      <!-- 筛选栏 -->
      <div class="toolbar">
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
              <span>{{ row.name }}</span>
            </template>
            <template v-else-if="col.key === 'contract_type'" #default="{ row }">
              <el-tag
                :type="CONTRACT_TYPE_TAG[row.contract_type as ContractType] || 'info'"
                size="small"
              >
                {{ CONTRACT_TYPE_LABEL[row.contract_type as ContractType] || row.contract_type }}
              </el-tag>
            </template>
            <template v-else-if="col.key === 'contract_no'" #default="{ row }">
              <span v-if="row.contract_no">{{ row.contract_no }}</span>
              <span v-else class="muted">-</span>
            </template>
            <template v-else-if="col.key === 'party_a_name'" #default="{ row }">
              {{ row.party_a_name || '-' }}
            </template>
            <template v-else-if="col.key === 'party_b_name'" #default="{ row }">
              {{ row.party_b_name || '-' }}
            </template>
            <template v-else-if="col.key === 'amount'" #default="{ row }">
              <span v-if="row.amount">¥{{ formatAmount(row.amount) }}</span>
              <span v-else class="muted">自动计算</span>
            </template>
            <template v-else-if="col.key === 'start_date'" #default="{ row }">
              {{ formatDate(row.start_date) }}
            </template>
            <template v-else-if="col.key === 'end_date'" #default="{ row }">
              {{ formatDate(row.end_date) }}
            </template>
            <template v-else-if="col.key === 'project_name'" #default="{ row }">
              {{ row.project_name || '-' }}
            </template>
            <template v-else-if="col.key === 'project_type'" #default="{ row }">
              {{ row.project_type || '-' }}
            </template>
            <template v-else-if="col.key === 'service_lines_count'" #default="{ row }">
              {{ row.service_lines_count ?? 0 }}
            </template>
            <template v-else-if="col.key === 'attachment_status'" #default="{ row }">
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
            <template v-else-if="col.key === 'sort_order'" #default="{ row }">
              {{ row.sort_order ?? 0 }}
            </template>
            <template v-else-if="col.key === 'remark'" #default="{ row }">
              {{ row.remark || '-' }}
            </template>
            <template v-else-if="col.key === 'contract_content'" #default="{ row }">
              <span v-if="row.contract_content" class="text-ellipsis">{{ row.contract_content }}</span>
              <span v-else class="muted">-</span>
            </template>
            <template v-else-if="col.key === 'delivery_requirements'" #default="{ row }">
              <span v-if="row.delivery_requirements" class="text-ellipsis">{{ row.delivery_requirements }}</span>
              <span v-else class="muted">-</span>
            </template>
            <template v-else-if="col.key === 'process_records'" #default="{ row }">
              <span v-if="row.process_records" class="text-ellipsis">{{ row.process_records }}</span>
              <span v-else class="muted">-</span>
            </template>
            <template v-else-if="col.key === 'created_at'" #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
            <template v-else-if="col.key === 'actions'" #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" link type="primary" @click="goDetail(row)">详情</el-button>
                <el-button size="small" link type="primary" @click="goEdit(row)">编辑</el-button>
                <el-popconfirm
                  title="确定删除该合同？"
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

.company-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: #fafbfc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.company-hint {
  font-size: 13px;
  color: #909399;
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
.muted {
  color: #c0c4cc;
}
</style>

<style>
/* Popover 内容（非 scoped 才能作用到 el-popover 内部生成的 DOM） */
.project-contract-column-popover .column-popover-body {
  font-size: 13px;
}
.project-contract-column-popover .column-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--text-secondary, #606266);
  font-weight: 600;
}
.project-contract-column-popover .column-list {
  max-height: 400px;
  overflow-y: auto;
}
.project-contract-column-popover .column-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: grab;
  transition: background 0.15s;
}
.project-contract-column-popover .column-item:hover {
  background: #f3f4f6;
}
.project-contract-column-popover .column-item.dragging {
  opacity: 0.4;
}
.project-contract-column-popover .column-item.drag-over {
  border-top: 2px solid #1e40af;
}
.project-contract-column-popover .drag-handle {
  color: #d1d5db;
  font-size: 16px;
  cursor: grab;
  user-select: none;
  line-height: 1;
}
.project-contract-column-popover .column-item:active .drag-handle {
  cursor: grabbing;
}
.project-contract-column-popover .required-tip {
  color: var(--el-color-info, #909399);
  font-size: 12px;
  margin-left: 4px;
}
.project-contract-column-popover .pin-btn {
  padding: 2px;
  margin-right: 4px;
  font-size: 14px;
  opacity: 0.3;
}
.project-contract-column-popover .pin-btn:hover,
.project-contract-column-popover .pin-btn.active {
  opacity: 1;
  color: var(--primary-color);
}
.project-contract-column-popover .column-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 6px;
}
</style>
