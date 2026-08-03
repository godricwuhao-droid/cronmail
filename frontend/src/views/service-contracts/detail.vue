<script setup lang="ts">
/**
 * 算力服务合同 - 详情页
 *
 * ADR-012: 展示合同基本信息 + 服务行表格 + 汇总统计 + 关联合同 + 附件状态
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Document } from '@element-plus/icons-vue'
import {
  deleteServiceContract,
  getServiceContract,
  type ServiceContractDetail,
  CONTRACT_TYPE_LABEL,
  CONTRACT_TYPE_TAG,
  type ContractType,
} from '@/api/modules/service-contract'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const route = useRoute()
const router = useRouter()

const record = ref<ServiceContractDetail | null>(null)
const loading = ref(false)
const summary = ref<AttachmentSummary | null>(null)

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

// 自动汇总
const autoCalcTotal = computed(() => {
  if (!record.value?.service_lines) return 0
  return record.value.service_lines.reduce((sum, line) => sum + line.total_price, 0)
})

const totalVcpu = computed(() => {
  if (!record.value?.service_lines) return 0
  return record.value.service_lines.reduce((sum, line) => {
    const v = Number(line.vcpu_count || 0)
    const q = Number(line.quantity || 0)
    return sum + v * q
  }, 0)
})

const totalMemory = computed(() => {
  if (!record.value?.service_lines) return 0
  return record.value.service_lines.reduce((sum, line) => {
    const v = Number(line.memory_gb || 0)
    const q = Number(line.quantity || 0)
    return sum + v * q
  }, 0)
})

const totalStorage = computed(() => {
  if (!record.value?.service_lines) return 0
  return record.value.service_lines.reduce((sum, line) => {
    const v = Number(line.storage_gb || 0)
    const q = Number(line.quantity || 0)
    return sum + v * q
  }, 0)
})

function hasAnyExtraInfo(row: any): boolean {
  if (row.gpu_count) return true
  if (row.specification && Object.keys(row.specification).length > 0) return true
  if (row.service_description) return true
  return false
}

// 金额对比
const amountMismatch = computed(() => {
  if (!record.value) return null
  const manual = record.value.amount ? parseFloat(record.value.amount) : null
  const auto = autoCalcTotal.value
  if (manual === null) return null
  if (Math.abs(manual - auto) < 0.01) return null
  return manual - auto
})

async function fetchRecord() {
  loading.value = true
  try {
    const res = await getServiceContract(route.params.id as string)
    record.value = res
    try {
      summary.value = await getAttachmentSummary('compute_service', res.id)
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
  router.push({ name: 'ServiceContractList' })
}

function handleEdit() {
  router.push({ name: 'ServiceContractEdit', params: { id: route.params.id as string } })
}

function goAttachments() {
  router.push({ name: 'ComputeServiceAttachments', params: { id: route.params.id as string } })
}

function goRelatedContract(id: string) {
  router.push({ name: 'ServiceContractDetail', params: { id } })
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
    await deleteServiceContract(record.value.id)
    ElMessage.success('合同已删除')
    router.replace({ name: 'ServiceContractList' })
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
          <span class="header-customer">{{ record?.customer_name || '-' }}</span>
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
        <el-descriptions-item label="客户">{{ record?.customer_name || '-' }}</el-descriptions-item>
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
        <el-descriptions-item label="自动汇总">
          {{ formatAmount(autoCalcTotal) }}
        </el-descriptions-item>
        <el-descriptions-item label="金额差异">
          <template v-if="amountMismatch !== null && Math.abs(amountMismatch) >= 0.01">
            <span class="amount-diff-warn">
              {{ amountMismatch > 0 ? '+' : '' }}{{ formatAmount(Math.abs(amountMismatch)) }}
            </span>
          </template>
          <span v-else class="muted">一致</span>
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

    <!-- 服务行表格 -->
    <section class="detail-section">
      <h3 class="section-title">服务内容明细</h3>
      <div v-if="!record?.service_lines || record.service_lines.length === 0" class="lines-empty">
        暂无服务行数据
      </div>
      <el-table
        v-else
        :data="record.service_lines"
        row-key="id"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="category" label="服务大类" width="130" />
        <el-table-column prop="item_name" label="服务项" min-width="160" show-overflow-tooltip />
        <el-table-column label="附加信息" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <div v-if="hasAnyExtraInfo(row)" class="line-extra">
              <template v-if="row.specification && Object.keys(row.specification).length > 0">
                <span v-for="(v, k) in row.specification" :key="k" class="info-chip">
                  {{ k }}: {{ v }}
                </span>
              </template>
              <span v-if="row.service_description" class="info-chip info-desc">
                {{ row.service_description }}
              </span>
              <span v-if="row.gpu_count" class="info-chip info-gpu">
                {{ row.gpu_model || 'GPU' }} × {{ row.gpu_count }}卡，显存 {{ row.gpu_memory_gb ?? '-' }}GB，算力 {{ row.gpu_tops ?? '-' }}TOPS
              </span>
            </div>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="vCPU" width="70" align="center">
          <template #default="{ row }">
            {{ row.vcpu_count != null ? Math.floor(Number(row.vcpu_count)) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="内存GB" width="80" align="center">
          <template #default="{ row }">{{ row.memory_gb ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="存储GB" width="80" align="center">
          <template #default="{ row }">{{ row.storage_gb ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="90" />
        <el-table-column label="数量" width="70" align="center">
          <template #default="{ row }">{{ row.quantity }}</template>
        </el-table-column>
        <el-table-column label="周期(月)" width="85" align="center">
          <template #default="{ row }">{{ row.period_months }}</template>
        </el-table-column>
        <el-table-column label="单价" width="130" align="right">
          <template #default="{ row }">{{ formatAmount(row.unit_price) }}</template>
        </el-table-column>
        <el-table-column label="总价" width="140" align="right">
          <template #default="{ row }">
            <span class="line-total-price">{{ formatAmount(row.total_price) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 汇总统计 -->
      <div v-if="record?.service_lines && record.service_lines.length > 0" class="lines-summary">
        <div class="summary-stat">
          <span class="summary-stat-label">总金额</span>
          <span class="summary-stat-value">{{ formatAmount(autoCalcTotal) }}</span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">总 vCPU</span>
          <span class="summary-stat-value">{{ totalVcpu }} 核</span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">总内存</span>
          <span class="summary-stat-value">{{ totalMemory }} GB</span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">总存储</span>
          <span class="summary-stat-value">{{ totalStorage }} GB</span>
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
            <span v-if="record.related_contract.amount" class="related-contract-amount">
              {{ formatAmount(record.related_contract.amount) }}
            </span>
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
/* 附加信息 chip */
.line-extra {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
}
.info-chip {
  display: inline-block;
  background: #f0f5ff;
  color: #1a73e8;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
}
.info-chip.info-desc {
  background: #f6ffed;
  color: #389e0d;
}
.info-chip.info-gpu {
  background: #fff7e6;
  color: #d46b08;
  font-weight: 500;
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
.related-contract-amount {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
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
