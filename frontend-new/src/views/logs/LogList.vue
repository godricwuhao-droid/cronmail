<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">发送日志</h1>
    </div>

    <div class="stats-row">
      <div class="stat-card" @click="statusFilter = ''" :class="{ active: !statusFilter }">
        <div class="stat-label">全部日志</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'sent'" :class="{ active: statusFilter === 'sent' }">
        <div class="stat-label">已发送</div>
        <div class="stat-value" style="color: #52C41A;">{{ stats.sent }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'failed'" :class="{ active: statusFilter === 'failed' }">
        <div class="stat-label">发送失败</div>
        <div class="stat-value" style="color: #FF4D4F;">{{ stats.failed }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">成功率</div>
        <div class="stat-value" style="color: #1677FF; font-size: 22px;">{{ successRate }}%</div>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="page-toolbar-left">
        <el-input
          v-model="keyword"
          placeholder="例如：收件人、主题"
          clearable
          style="width: 340px"
          @input="onSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="statusFilter" placeholder="发送状态" clearable style="width: 140px; margin-left: 12px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="待发送" value="pending" />
          <el-option label="发送中" value="sending" />
          <el-option label="已发送" value="sent" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px; margin-left: 12px"
          @change="onDateChange"
        />
      </div>
      <div class="page-toolbar-right">
        <el-button :icon="Setting" @click="showColumnCustomizer = true">列设置</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>
    </div>

    <div class="content-card" style="padding: 0;">
      <el-table
        :data="list"
        v-loading="loading"
        stripe
        style="width: 100%"
        @sort-change="onSortChange"
      >
        <el-table-column v-if="visibleColumns.some(c => c.key === 'trigger_type')" label="触发类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.trigger_type" size="small" effect="light">{{ triggerLabel(row.trigger_type) }}</el-tag>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'recipient')" prop="recipient" label="收件人" min-width="200" show-overflow-tooltip />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'subject')" prop="subject" label="主题" min-width="240" show-overflow-tooltip />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'status')" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'sent_at')" prop="sent_at" label="发送时间" width="180" sortable="custom" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'error_msg')" prop="error_msg" label="错误信息" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error_msg" class="error-text">{{ row.error_msg }}</span>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'created_at')" prop="created_at" label="创建时间" width="180" sortable="custom" />
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无日志数据" style="padding: 60px 20px;" />

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

    <el-dialog v-model="detailVisible" title="日志详情" width="640px" :close-on-click-modal="false">
      <div class="detail-table">
        <div class="detail-row">
          <span class="detail-label">触发类型</span>
          <span class="detail-value">{{ currentLog.trigger_type ? triggerLabel(currentLog.trigger_type) : '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">收件人</span>
          <span class="detail-value">{{ currentLog.recipient || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">收件人类型</span>
          <span class="detail-value">{{ currentLog.recipient_type || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">邮件主题</span>
          <span class="detail-value">{{ currentLog.subject || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">发送状态</span>
          <span class="detail-value">
            <el-tag :type="statusType(currentLog.status)" size="small" effect="light">
              {{ statusLabel(currentLog.status) }}
            </el-tag>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">发送时间</span>
          <span class="detail-value">{{ currentLog.sent_at || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">错误信息</span>
          <span class="detail-value" :class="{ 'error-text': currentLog.error_msg }">
            {{ currentLog.error_msg || '-' }}
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">创建时间</span>
          <span class="detail-value">{{ currentLog.created_at || '-' }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

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
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Setting, Download, Refresh } from '@element-plus/icons-vue'
import { getLogs } from '@/api/log'
import ColumnCustomizer from '@/components/ColumnCustomizer.vue'
import { useColumnCustomization, useExportExcel } from '@/composables/useTable'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')
const dateRange = ref<[string, string] | null>(null)
const detailVisible = ref(false)
const currentLog = ref<any>({})

const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null
const onSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
}

const onDateChange = () => {
  page.value = 1
  loadData()
}

const defaultColumns = [
  { key: 'trigger_type', label: '触发类型', visible: true, pinned: false },
  { key: 'recipient', label: '收件人', visible: true, pinned: true },
  { key: 'subject', label: '主题', visible: true, pinned: false },
  { key: 'status', label: '状态', visible: true, pinned: false },
  { key: 'sent_at', label: '发送时间', visible: true, pinned: false },
  { key: 'error_msg', label: '错误信息', visible: true, pinned: false },
  { key: 'created_at', label: '创建时间', visible: true, pinned: false },
]

const {
  columnStates,
  columnOrder,
  visibleColumns,
  pinnedKeys,
  toggleColumn,
  resetColumns,
} = useColumnCustomization(defaultColumns, 'log-columns')

const showColumnCustomizer = ref(false)

const stats = ref({ total: 0, sent: 0, failed: 0 })

const successRate = computed(() => {
  const total = stats.value.sent + stats.value.failed
  return total > 0 ? Math.round((stats.value.sent / total) * 100) : 0
})

const statusType = (s: string) => ({ pending: 'info', sending: 'warning', sent: 'success', failed: 'danger' }[s] || 'info')
const statusLabel = (s: string) => ({ pending: '待发送', sending: '发送中', sent: '已发送', failed: '失败' }[s] || s)
const triggerLabel = (s: string) => ({ contract_expiry: '合同到期', manual: '手动发送', scheduled: '定时发送' }[s] || s)

const loadData = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (statusFilter.value) params.status = statusFilter.value
    if (dateRange.value) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    const res: any = await getLogs(params)
    list.value = res.items || res
    total.value = res.total || 0

    stats.value.total = total.value
    stats.value.sent = list.value.filter((l: any) => l.status === 'sent').length
    stats.value.failed = list.value.filter((l: any) => l.status === 'failed').length
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const onSortChange = () => { loadData() }

const viewDetail = (row: any) => {
  currentLog.value = row
  detailVisible.value = true
}

const { exportExcel } = useExportExcel(list, defaultColumns, '发送日志')
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
.error-text { color: #FF4D4F; }
.detail-table { display: flex; flex-direction: column; gap: 0; }
.detail-row {
  display: flex; padding: 12px 0; border-bottom: 1px solid #f0f0f0;
  &:last-child { border-bottom: none; }
}
.detail-label { width: 100px; flex-shrink: 0; color: #86909C; font-size: 13px; }
.detail-value { flex: 1; color: #1f2329; font-size: 13px; word-break: break-all; }
.pagination-wrapper {
  padding: 16px 20px; display: flex; justify-content: flex-end;
  border-top: 1px solid var(--color-border-light);
}
</style>