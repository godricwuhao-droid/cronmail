<script setup lang="ts">
/**
 * 卫星数据合同 - 详情页
 *
 * 展示合同基本信息 + 附件状态汇总
 */
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Document, Paperclip } from '@element-plus/icons-vue'
import {
  deleteSatelliteContract,
  getSatelliteContract,
  type SatelliteContractItem,
} from '@/api/modules/satellite-contract'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const route = useRoute()
const router = useRouter()

const record = ref<SatelliteContractItem | null>(null)
const loading = ref(false)
const summary = ref<AttachmentSummary | null>(null)

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

async function fetchRecord() {
  loading.value = true
  try {
    const res = await getSatelliteContract(route.params.id as string)
    record.value = res
    // 加载附件状态
    try {
      summary.value = await getAttachmentSummary('satellite_data', res.id)
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
  router.push({ name: 'SatelliteContractList' })
}

function handleEdit() {
  router.push({ name: 'SatelliteContractEdit', params: { id: route.params.id as string } })
}

function goAttachments() {
  router.push({ name: 'SatelliteDataAttachments', params: { id: route.params.id as string } })
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
    await deleteSatelliteContract(record.value.id)
    ElMessage.success('合同已删除')
    router.replace({ name: 'SatelliteContractList' })
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

    <!-- 基本信息 -->
    <section class="detail-section">
      <h3 class="section-title">合同信息</h3>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="合同名称">{{ record?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ record?.customer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同编号">
          {{ record?.contract_no || '-' }}
        </el-descriptions-item>
        <!-- ADR-013 新增字段 -->
        <el-descriptions-item label="合同类型">
          {{ record?.contract_type || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="项目名称">
          {{ record?.project_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">
          <span v-if="record?.amount != null">¥{{ record.amount.toFixed(2) }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="开始日期">
          {{ record?.start_date || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="结束日期">
          {{ record?.end_date || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="甲方名称">
          {{ record?.party_a_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="乙方名称">
          {{ record?.party_b_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(record?.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDateTime(record?.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="合同内容" :span="3">
          <span v-if="record?.contract_content">{{ record.contract_content }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="交付要求" :span="3">
          <span v-if="record?.delivery_requirements">{{ record.delivery_requirements }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="过程记录" :span="3">
          <span v-if="record?.process_records">{{ record.process_records }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">
          <span v-if="record?.remark">{{ record.remark }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
      </el-descriptions>
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
</style>
