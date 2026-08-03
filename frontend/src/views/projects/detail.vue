<script setup lang="ts">
/**
 * 项目管理合同 - 详情页
 *
 * 展示合同基本信息 + 服务行表格 + 汇总统计 + 关联合同 + 附件状态
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Document, Paperclip } from '@element-plus/icons-vue'
import {
  deleteProjectContract,
  getProjectContract,
  type ProjectContractDetail,
  CONTRACT_TYPE_LABEL,
  CONTRACT_TYPE_TAG,
  COMPANY_MAP,
  type ContractType,
} from '@/api/modules/project'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const route = useRoute()
const router = useRouter()

const companyCode = computed(() => (route.params.company as string) || 'fengyun')

const record = ref<ProjectContractDetail | null>(null)
const loading = ref(false)
const summary = ref<AttachmentSummary | null>(null)

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
  if (!s) return '-'
  return s.length >= 10 ? s.slice(0, 10) : s
}

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

function formatAmount(val?: string | number | null) {
  if (val === null || val === undefined || val === '') return '-'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '-'
  return '¥' + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function fetchRecord() {
  loading.value = true
  try {
    const res = await getProjectContract(route.params.id as string)
    record.value = res
    // 从 raw_tables_json 解析原始表格
    const detailAny = res as any
    if (detailAny.raw_tables_json) {
      try {
        rawTables.value = JSON.parse(detailAny.raw_tables_json)
      } catch { rawTables.value = [] }
    }
    try {
      summary.value = await getAttachmentSummary('project', res.id)
    } catch {
      summary.value = null
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
  try {
    await ElMessageBox.confirm('确认删除该合同？', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteProjectContract(record.value.id)
    ElMessage.success('合同已删除')
    router.replace({ name: 'ProjectList', params: { company: companyCode.value } })
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 附件状态辅助
// ============================================================
function statusTagType(confirmed: boolean, fileCount: number): 'success' | 'danger' | 'info' {
  if (fileCount === 0) return 'info'
  return confirmed ? 'success' : 'danger'
}

function statusText(confirmed: boolean, fileCount: number): string {
  if (fileCount === 0) return '未上传'
  return confirmed ? '已确认' : '未确认'
}

const categoryLabels: Record<string, string> = {
  contract_agreement: '合同协议',
  acceptance_material: '交付材料',
  process_material: '过程材料',
}

onMounted(() => {
  fetchRecord()
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <!-- 顶部返回 -->
    <div style="margin-bottom: 16px;">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
    </div>

    <!-- 标题栏 -->
    <div class="detail-header">
      <div class="header-left">
        <h1 class="header-title">{{ record?.name || '...' }}</h1>
        <div class="header-sub">
          <span class="header-company">{{ COMPANY_MAP[record?.company_code || ''] || record?.company_code || '-' }}</span>
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
          <el-icon style="margin-right:4px"><Paperclip /></el-icon>附件管理
        </el-button>
      </div>
    </div>

    <!-- 合同基本信息 -->
    <section class="detail-section">
      <h3 class="section-title">合同信息</h3>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="合同名称">{{ record?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="所属公司">
          {{ COMPANY_MAP[record?.company_code || ''] || record?.company_code || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="合同编号">
          {{ record?.contract_no || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="甲方">
          {{ record?.party_a_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="乙方">
          {{ record?.party_b_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="合同日期">
          {{ formatDate(record?.start_date) }} ~ {{ formatDate(record?.end_date) }}
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">
          <span v-if="record?.amount">{{ formatAmount(record.amount) }}</span>
          <span v-else class="muted">自动计算</span>
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">
          {{ formatAmount(record?.amount) }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="3">
          {{ formatDateTime(record?.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间" :span="3">
          {{ formatDateTime(record?.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="所属项目" :span="3">
          <span v-if="record?.project_name">{{ record.project_name }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="项目类型" :span="3">
          <span v-if="record?.project_type">{{ record.project_type }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">
          <span v-if="record?.remark">{{ record.remark }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 合同详细内容 -->
    <section v-if="record?.contract_content || record?.delivery_requirements || record?.process_records" class="detail-section">
      <h3 class="section-title">合同详细内容</h3>
      <el-descriptions :column="1" border>
        <el-descriptions-item v-if="record?.contract_content" label="合同内容">
          <div class="long-text">{{ record.contract_content }}</div>
        </el-descriptions-item>
        <el-descriptions-item v-if="record?.delivery_requirements" label="交付要求">
          <div class="long-text">{{ record.delivery_requirements }}</div>
        </el-descriptions-item>
        <el-descriptions-item v-if="record?.process_records" label="过程记录">
          <div class="long-text">{{ record.process_records }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 文档表格展示区 -->
    <section v-if="rawTables.length > 0" class="detail-section">
      <h3 class="section-title">文档表格</h3>
      <div v-for="table in rawTables" :key="table.table_index" style="margin-bottom: 16px;">
        <div v-if="table.title" style="font-weight: 600; margin-bottom: 8px;">{{ table.title }}</div>
        <el-table :data="table.rows" border size="small" max-height="400">
          <el-table-column v-for="(h, hi) in table.headers" :key="hi" :label="h" :prop="String(hi)" min-width="100">
            <template #default="{ row }">{{ row[hi] || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <!-- 资源统计面板 -->
    <section v-if="statsDisplay.length > 0" class="detail-section">
      <h3 class="section-title">📊 交付资源统计</h3>
      <div style="display: flex; flex-wrap: wrap; gap: 16px; padding: 12px; background: #f5f7fa; border-radius: 6px;">
        <div v-for="s in statsDisplay" :key="s.label" style="display: flex; gap: 6px;">
          <span style="color: #909399;">{{ s.label }}：</span>
          <span style="font-weight: 600; color: #1a3270;">{{ s.value }}</span>
        </div>
      </div>
    </section>

    <!-- 服务内容明细（原始表格 + 统计） -->
    <section v-if="rawTables.length > 0 || (record?.service_lines && record.service_lines.length > 0)" class="detail-section">
      <h3 class="section-title">服务内容明细</h3>
      
      <!-- 原始表格 -->
      <div v-for="table in rawTables" :key="table.table_index" style="margin-bottom: 16px;">
        <div v-if="table.title" style="font-weight: 600; margin-bottom: 8px;">📋 {{ table.title }}</div>
        <el-table :data="table.rows" border size="small" max-height="500">
          <el-table-column v-for="(h, hi) in table.headers" :key="hi" :label="h" :prop="String(hi)" min-width="100">
            <template #default="{ row }">{{ row[hi] || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 资源统计 -->
      <div v-if="statsDisplay.length > 0" style="padding: 12px; background: #f5f7fa; border-radius: 6px; margin-bottom: 12px;">
        <div style="font-weight: 600; margin-bottom: 8px;">📊 交付资源统计</div>
        <div style="display: flex; flex-wrap: wrap; gap: 16px;">
          <div v-for="s in statsDisplay" :key="s.label" style="display: flex; gap: 6px;">
            <span style="color: #909399;">{{ s.label }}：</span>
            <span style="font-weight: 600; color: #1a3270;">{{ s.value }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 关联合同 -->
    <section v-if="record?.related_contract" class="detail-section">
      <h3 class="section-title">关联合同</h3>
      <el-card shadow="hover" class="related-contract-card" @click="goRelatedContract(record.related_contract!.id)">
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
      </el-card>
    </section>

    <!-- 附件状态 -->
    <section class="detail-section">
      <h3 class="section-title">附件状态</h3>
      <div class="attachment-status-grid">
        <el-card
          v-for="(label, code) in categoryLabels"
          :key="code"
          shadow="hover"
          class="status-card"
        >
          <template #header>
            <div class="status-card-header">
              <span>{{ label }}</span>
              <el-tag
                :type="statusTagType(
                  summary?.items?.[code]?.confirmed ?? false,
                  summary?.items?.[code]?.file_count ?? 0
                )"
                size="small"
              >
                {{ statusText(
                  summary?.items?.[code]?.confirmed ?? false,
                  summary?.items?.[code]?.file_count ?? 0
                ) }}
              </el-tag>
            </div>
          </template>
          <div class="status-card-body">
            <span class="status-stat">
              <strong>{{ summary?.items?.[code]?.file_count ?? 0 }}</strong> 个文件
            </span>
          </div>
        </el-card>
      </div>
      <div style="margin-top: 12px;">
        <span class="muted">
          总计：{{ summary?.confirmed_items ?? 0 }} / {{ summary?.total_items ?? 0 }} 项已确认
        </span>
        <el-tag
          v-if="summary?.all_confirmed"
          type="success"
          size="small"
          style="margin-left: 8px;"
        >
          全部完成
        </el-tag>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-header {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}
.header-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}
.header-sub {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}
.header-company {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* 服务行表格 */
.lines-empty {
  text-align: center;
  padding: 24px;
  color: #909399;
}
.line-total-price {
  font-weight: 700;
  color: #1a73e8;
}
.amount-diff-warn {
  color: #e6a23c;
  font-weight: 600;
}

/* 汇总统计 */
.lines-summary {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding: 14px 18px;
  background: #fafbfc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.summary-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.summary-stat-label {
  font-size: 12px;
  color: #909399;
}
.summary-stat-value {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

/* 关联合同 */
.related-contract-card {
  cursor: pointer;
  border-radius: 8px;
  transition: box-shadow 0.2s;
}
.related-contract-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.related-contract-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.related-contract-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.related-contract-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.related-contract-no {
  font-size: 13px;
  color: #909399;
}
.related-contract-arrow {
  position: absolute;
  top: 50%;
  right: 20px;
  transform: translateY(-50%);
  color: #1a73e8;
  font-size: 14px;
  font-weight: 500;
}

/* 附件状态 */
.attachment-status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.status-card {
  border-radius: 8px;
}
.status-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.status-card-body {
  padding: 8px 0;
}
.status-stat {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 长文本内容 */
.long-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  color: #303133;
}
</style>
