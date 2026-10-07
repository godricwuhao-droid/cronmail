<script setup lang="ts">
/**
 * 项目管理合同 - 详情页
 *
 * 展示合同基本信息 + 服务行表格 + 汇总统计 + 关联合同
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Document, Paperclip } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
import {
  deleteProjectContract,
  getProjectContract,
  type ProjectContractDetail,
  CONTRACT_TYPE_LABEL,
  CONTRACT_TYPE_TAG,
  COMPANY_MAP,
  type ContractType,
} from '@/api/modules/project'

const route = useRoute()
const router = useRouter()

const companyCode = computed(() => (route.params.company as string) || 'fengyun')

const record = ref<ProjectContractDetail | null>(null)
const loading = ref(false)

// ============================================================
// 资源统计标签映射
// ============================================================
const STATS_LABELS: Record<string, string> = {
  vcpu: 'vCPU',
  memory_gb: '内存(GB)',
  storage_gb: '存储(GB)',
  gpu_count: 'GPU(卡)',
  gpu_tops: '算力(TOPS)',
  bandwidth_mbps: '带宽(Mbps)',
  rack_count: '机柜(个)',
  ip_count: 'IP(个)',
}

// raw_tables 和 resource_summary 从后端详情中读取
const rawTables = ref<any[]>([])
const resourceSummary = ref<any>(null)

const statsDisplay = computed(() => {
  const stats = resourceSummary.value?.stats || {}
  return Object.entries(stats)
    .filter(([_, v]) => v && Number(v) > 0)
    .map(([k, v]) => ({ label: STATS_LABELS[k] || k, value: v }))
})

function formatDate(s?: string | null) {
  if (!s) return '—'
  return s.length >= 10 ? s.slice(0, 10) : s
}

function formatAmount(val?: string | number | null) {
  if (val === null || val === undefined || val === '') return '—'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '—'
  return '¥' + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ============================================================
// 合同信息 - 日期区间
// ============================================================
const dateRange = computed(() => {
  const s = record.value?.start_date
  const e = record.value?.end_date
  if (!s && !e) return ''
  return `${formatDate(s)} ~ ${formatDate(e)}`
})

// ============================================================
// 合同信息 - 响应式列数（宽屏 3 列 / 中屏 2 列 / 窄屏 1 列）
// ============================================================
const descriptionsColumn = ref(3)

function updateDescriptionsColumn() {
  const w = window.innerWidth
  descriptionsColumn.value = w >= 1200 ? 3 : w >= 768 ? 2 : 1
}

// ============================================================
// 长文本折叠（合同内容 / 交付要求 / 过程记录）
// ============================================================
interface LongTextItem {
  key: string
  label: string
  text: string
}

const LONG_TEXT_COLLAPSE_LIMIT = 300
const longTextExpanded = ref<Record<string, boolean>>({})

const longTextItems = computed<LongTextItem[]>(() => {
  const items: LongTextItem[] = []
  if (record.value?.contract_content) {
    items.push({ key: 'contract_content', label: '合同内容', text: record.value.contract_content })
  }
  if (record.value?.delivery_requirements) {
    items.push({ key: 'delivery_requirements', label: '交付要求', text: record.value.delivery_requirements })
  }
  if (record.value?.process_records) {
    items.push({ key: 'process_records', label: '过程记录', text: record.value.process_records })
  }
  return items
})

function isLongText(text: string): boolean {
  return text.length > LONG_TEXT_COLLAPSE_LIMIT
}

function toggleLongText(key: string) {
  longTextExpanded.value[key] = !longTextExpanded.value[key]
}

async function fetchRecord() {
  loading.value = true
  try {
    const res = await getProjectContract(route.params.id as string)
    record.value = res
    // 从 raw_tables_json 解析原始表格（兼容 {tables:[], resource_summary:{}} 和纯数组格式）
    const detailAny = res as any
    if (detailAny.raw_tables_json) {
      try {
        const parsed = JSON.parse(detailAny.raw_tables_json)
        if (Array.isArray(parsed)) {
          rawTables.value = parsed
        } else {
          rawTables.value = parsed.tables || []
          if (parsed.resource_summary?.stats) {
            resourceSummary.value = { stats: parsed.resource_summary.stats }
          }
        }
      } catch { rawTables.value = [] }
    }
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// 操作
// ============================================================
function goBack() {
  router.push({ name: 'ProjectList', params: { company: companyCode.value } })
}

function handleEdit() {
  router.push({ name: 'ProjectEdit', params: { company: companyCode.value, id: route.params.id as string } })
}

function goAttachments() {
  router.push({ name: 'ProjectAttachments', params: { company: companyCode.value, id: route.params.id as string } })
}

function goRelatedContract(id: string) {
  router.push({ name: 'ProjectDetail', params: { company: companyCode.value, id } })
}

async function handleDelete() {
  if (!record.value?.id) return
  if (!(await confirmDelete('确认删除该合同？'))) return
  try {
    await deleteProjectContract(record.value.id)
    ElMessage.success('合同已删除')
    router.replace({ name: 'ProjectList', params: { company: companyCode.value } })
  } catch {
    // 错误已统一处理
  }
}

onMounted(() => {
  updateDescriptionsColumn()
  window.addEventListener('resize', updateDescriptionsColumn)
  fetchRecord()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDescriptionsColumn)
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="top-bar">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <!-- 标题栏 -->
    <div class="detail-header">
      <div class="header-left">
        <h1 class="header-title">{{ record?.name || '...' }}</h1>
        <div class="header-sub">
          <span class="header-company">{{ COMPANY_MAP[record?.company_code || ''] || record?.company_code || '—' }}</span>
          <el-tag
            v-if="record"
            :type="CONTRACT_TYPE_TAG[record.contract_type as ContractType] || 'info'"
            size="small"
          >
            {{ CONTRACT_TYPE_LABEL[record.contract_type as ContractType] || record.contract_type }}
          </el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button :icon="Document" @click="handleEdit">编辑</el-button>
        <el-button type="danger" @click="handleDelete">删除</el-button>
        <el-button type="primary" @click="goAttachments">
          <el-icon class="btn-icon"><Paperclip /></el-icon>附件管理
        </el-button>
      </div>
    </div>

    <!-- 合同基本信息 -->
    <section class="detail-section">
      <div class="dialog-section-title">合同信息</div>
      <el-descriptions :column="descriptionsColumn" border>
        <el-descriptions-item label="所属公司">
          {{ COMPANY_MAP[record?.company_code || ''] || record?.company_code || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="合同编号">
          <span v-if="record?.contract_no">{{ record.contract_no }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="合同日期">
          <span v-if="dateRange">{{ dateRange }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="甲方">
          <span v-if="record?.party_a_name">{{ record.party_a_name }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="乙方">
          <span v-if="record?.party_b_name">{{ record.party_b_name }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">
          <span v-if="record?.amount" class="col-amount">{{ formatAmount(record.amount) }}</span>
          <span v-else class="muted">自动计算</span>
        </el-descriptions-item>
        <el-descriptions-item label="负责人">
          <span v-if="record?.responsible_person">{{ record.responsible_person }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="商务">
          <span v-if="record?.business_person">{{ record.business_person }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="甲方委派人">
          <span v-if="record?.party_a_contact">{{ record.party_a_contact }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="乙方委派人">
          <span v-if="record?.party_b_contact">{{ record.party_b_contact }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="项目类型">
          <span v-if="record?.project_type">{{ record.project_type }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="所属项目">
          <span v-if="record?.project_name">{{ record.project_name }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="descriptionsColumn">
          <span v-if="record?.remark">{{ record.remark }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 合同详细内容 -->
    <section v-if="longTextItems.length > 0" class="detail-section">
      <div class="dialog-section-title">合同详细内容</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item v-for="item in longTextItems" :key="item.key" :label="item.label">
          <div class="long-text-wrap">
            <div
              class="long-text"
              :class="{ collapsed: isLongText(item.text) && !longTextExpanded[item.key] }"
            >{{ item.text }}</div>
            <el-button
              v-if="isLongText(item.text)"
              link
              type="primary"
              size="small"
              class="long-text-toggle"
              @click="toggleLongText(item.key)"
            >
              {{ longTextExpanded[item.key] ? '收起' : '展开全文' }}
            </el-button>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 服务内容明细（原始表格 + 统计） -->
    <section
      v-if="rawTables.length > 0 || (record?.service_lines && record.service_lines.length > 0)"
      class="detail-section"
    >
      <div class="dialog-section-title">服务内容明细</div>

      <!-- 资源统计 -->
      <div v-if="statsDisplay.length > 0" class="stats-panel">
        <div class="stats-panel-title">交付资源统计</div>
        <div class="stats-panel-body">
          <div v-for="s in statsDisplay" :key="s.label" class="stats-item">
            <span class="stats-label">{{ s.label }}：</span>
            <span class="stats-value">{{ s.value }}</span>
          </div>
        </div>
      </div>

      <!-- 原始表格 -->
      <div v-for="table in rawTables" :key="table.table_index" class="raw-table-block">
        <div v-if="table.title" class="raw-table-title">{{ table.title }}</div>
        <el-table :data="table.rows" stripe max-height="500" class="raw-view-table">
          <el-table-column v-for="(h, hi) in table.headers" :key="hi" :label="h" :prop="String(hi)" min-width="120">
            <template #default="{ row }">
              <span v-if="row[hi]" class="raw-cell-text">{{ row[hi] }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 服务备注 -->
      <div v-if="record?.service_lines && record.service_lines.length > 0" class="service-notes">
        <div class="service-notes-title">服务备注</div>
        <div
          v-for="(line, idx) in record.service_lines"
          :key="line.id || idx"
          class="service-note-card"
        >
          <div class="service-note-name">
            <span v-if="line.item_name">{{ line.item_name }}</span>
            <span v-else class="muted">—</span>
          </div>
          <div class="service-note-desc">
            <span v-if="line.service_description">{{ line.service_description }}</span>
            <span v-else class="muted">—</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 关联合同 -->
    <section v-if="record?.related_contract" class="detail-section">
      <div class="dialog-section-title">关联合同</div>
      <div class="related-contract-card" @click="goRelatedContract(record.related_contract!.id)">
        <div class="related-contract-info">
          <div class="related-contract-name">
            {{ record.related_contract.name }}
          </div>
          <div class="related-contract-meta">
            <span class="related-contract-no">{{ record.related_contract.contract_no || '无编号' }}</span>
            <el-tag
              :type="CONTRACT_TYPE_TAG[record.related_contract.contract_type as ContractType] || 'info'"
              size="small"
            >
              {{ CONTRACT_TYPE_LABEL[record.related_contract.contract_type as ContractType] || record.related_contract.contract_type }}
            </el-tag>
          </div>
        </div>
        <div class="related-contract-arrow">
          查看详情 →
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.top-bar {
  margin-bottom: 0;
}

.detail-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  border-radius: 8px;
}
.header-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}
.header-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 14px;
}
.header-company {
  font-size: 14px;
  color: var(--primary-color);
  font-weight: 500;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.btn-icon {
  margin-right: 4px;
}

.detail-section {
  padding: 20px;
  border-radius: 8px;
}
.detail-section > .dialog-section-title {
  margin-bottom: 12px;
}

.muted {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 400;
  opacity: 0.85;
}
.col-amount {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-primary);
}

.long-text-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.long-text {
  width: 100%;
  white-space: pre-wrap;
  line-height: 1.6;
  word-break: break-word;
  color: var(--text-primary);
  text-align: left;
}
.long-text.collapsed {
  max-height: 300px;
  overflow: hidden;
}
.long-text-toggle {
  padding: 0;
}

.stats-panel {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.stats-panel-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 10px;
}
.stats-panel-body {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}
.stats-item {
  display: flex;
  gap: 6px;
  align-items: baseline;
}
.stats-label {
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}
.stats-value {
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.raw-table-block {
  margin-bottom: 16px;
}
.raw-table-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.raw-view-table :deep(.el-table__cell) {
  padding: 12px 10px;
  vertical-align: middle;
}
.raw-cell-text {
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.service-notes {
  margin-top: 4px;
}
.service-notes-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  margin-bottom: 10px;
}
.service-note-card {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.service-note-name {
  width: clamp(120px, 20%, 240px);
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-word;
}
.service-note-desc {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}

.related-contract-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  cursor: pointer;
  border-radius: 8px;
  padding: 16px 20px;
  background: #f8fafc;
  transition: background 0.2s;
}
.related-contract-card:hover {
  background: #eff6ff;
}
.related-contract-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.related-contract-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
.related-contract-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.related-contract-no {
  font-size: 13px;
  color: var(--text-secondary);
}
.related-contract-arrow {
  flex-shrink: 0;
  white-space: nowrap;
  color: var(--primary-color);
  font-size: 14px;
  font-weight: 500;
}
</style>
