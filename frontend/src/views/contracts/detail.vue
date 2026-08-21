<script setup lang="ts">
/**
 * 合同管理 - 详情页
 *
 * 设计要点：
 *  - 顶部 header：合同名称 + 客户 + 状态 tag + 操作按钮（编辑 / 删除）
 *  - 基本信息卡片：合同名 / 客户 / 合同编号 / 起止日期 / 计费方式 / 状态 / 设备数 / 联系人 / 备注
 *  - 关联设备卡片：表格 + 「关联设备」按钮；行内「取消关联」
 *  - 关联联系人卡片：表格
 *  - 「关联设备」弹窗：从客户下的可用设备中多选
 */
import { onMounted, reactive, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Connection, Document, Paperclip, InfoFilled } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
import {
  deleteContract,
  getContract,
  linkContractRentals,
  unlinkContractRentals,
  listChangeLogs,
  createChangeLog,
  type ContractDetail,
  type ContractRentalItem,
  type ContractContactItem,
  type ChangeLogEntry,
} from '@/api/modules/contract'
import {
  getRentals,
  sendProvisionEmail,
  sendExpiryReminder,
  reclaimRental,
  type RentalListItem,
} from '@/api/modules/rental'
import {
  CONTRACT_BILLING_MODEL_LABEL,
  CONTRACT_STATUS_LABEL,
} from '@/lib/contract'
import { safeStatusLabel as rentalStatusLabel, safeStatusTagType as rentalStatusTagType } from '@/lib/rental'
import {
  getAttachmentSummary,
  type AttachmentSummary,
} from '@/api/modules/attachment'

const route = useRoute()
const router = useRouter()

const record = ref<ContractDetail | null>(null)
const loading = ref(false)
const acting = ref(false)

function statusTagType(s?: string) {
  const m: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    active: 'success',
    expiring: 'warning',
    expired: 'danger',
    reclaimed: 'info',
  }
  return m[s || ''] || 'info'
}
function statusLabel(s?: string) {
  return s ? (CONTRACT_STATUS_LABEL[s as keyof typeof CONTRACT_STATUS_LABEL] ?? s) : '-'
}
function billingLabel(s?: string) {
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

async function fetchRecord() {
  loading.value = true
  try {
    const res = await getContract(route.params.id as string)
    record.value = res
    // 加载附件状态
    try {
      attachmentSummary.value = await getAttachmentSummary('compute_leasing', res.id)
    } catch {
      attachmentSummary.value = null
    }
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// 附件状态
// ============================================================
const attachmentSummary = ref<AttachmentSummary | null>(null)

function goAttachments() {
  router.push({ name: 'ComputeLeasingAttachments', params: { id: route.params.id as string } })
}

function attStatusTagType(confirmed: boolean, fileCount: number): 'success' | 'danger' | 'info' {
  if (fileCount === 0) return 'info'
  return confirmed ? 'success' : 'danger'
}

function attStatusText(confirmed: boolean, fileCount: number): string {
  if (fileCount === 0) return '未上传'
  return confirmed ? '已确认' : '未确认'
}

const attCategoryLabels: Record<string, string> = {
  contract_agreement: '合同协议',
  acceptance_material: '交付材料',
  process_material: '过程材料',
}

// ============================================================
// 顶部操作
// ============================================================
function goBack() {
  router.push({ name: 'ContractList' })
}
function handleEdit() {
  router.push({ name: 'ContractEdit', params: { id: route.params.id as string } })
}
async function handleDelete() {
  if (!record.value?.id) return
  if (!(await confirmDelete('确认删除该合同？关联的设备不会被删除，仅解除合同关联'))) return
  acting.value = true
  try {
    await deleteContract(record.value.id)
    ElMessage.success('合同已删除')
    router.replace({ name: 'ContractList' })
  } catch {
    // 错误已统一处理
  } finally {
    acting.value = false
  }
}

// ============================================================
// 邮件操作（使用第一台关联设备 ID 作为锚点触发 Celery 异步发送）
// ============================================================
async function handleSendProvision() {
  const rentals = record.value?.rentals || []
  if (rentals.length === 0) { ElMessage.warning('没有关联设备'); return }
  acting.value = true
  try {
    await sendProvisionEmail(rentals[0].id)
    ElMessage.success('已提交开通邮件发送任务')
  } catch { /* 忽略 */ }
  finally { acting.value = false }
}

async function handleSendExpiry() {
  const rentals = record.value?.rentals || []
  if (rentals.length === 0) { ElMessage.warning('没有关联设备'); return }
  acting.value = true
  try {
    await sendExpiryReminder(rentals[0].id)
    ElMessage.success('已提交临期提醒发送任务')
  } catch { /* 忽略 */ }
  finally { acting.value = false }
}

async function handleReclaim() {
  const rentals = record.value?.rentals || []
  if (rentals.length === 0) { ElMessage.warning('没有关联设备'); return }
  acting.value = true
  try {
    await reclaimRental(rentals[0].id)
    ElMessage.success('已提交回收任务')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '回收失败，请检查合同状态')
  }
  finally { acting.value = false }
}

// ============================================================
// 续期
// ============================================================
function handleRenew() {
  if (!record.value) return
  router.push({
    name: 'ContractCreate',
    query: { renew_from: record.value.id },
  })
}

function goContractDetail(id: string) {
  router.push({ name: 'ContractDetail', params: { id } })
}

function goRental(id: string) {
  router.push({ name: 'RentalDetail', params: { id } })
}

function renewalRowClass({ row }: { row: { is_current?: boolean } }) {
  return row.is_current ? 'renewal-row-current' : 'renewal-row-clickable'
}

function handleRenewalRowClick(row: { id: string; is_current?: boolean }) {
  if (!row.is_current) {
    goContractDetail(row.id)
  }
}

// ============================================================
// 关联设备弹窗
// ============================================================
const linkDialogVisible = ref(false)
const linkForm = reactive<{ selected: string[] }>({ selected: [] })
const linkSubmitting = ref(false)
const availableRentals = ref<RentalListItem[]>([])

const linkedIds = computed<string[]>(() => (record.value?.rentals || []).map((r) => r.id))

/** 弹窗内「可选设备」= 客户下所有设备 - 已关联设备 */
const candidateRentals = computed<RentalListItem[]>(() => {
  const linked = new Set(linkedIds.value)
  return availableRentals.value.filter((r) => !linked.has(r.id))
})

function rentalLabel(row: RentalListItem) {
  const rack = row.rack_location ? ` · ${row.rack_location}` : ' · -'
  return `${row.machine_model}${rack}`
}

async function openLinkDialog() {
  linkForm.selected = []
  try {
    const res = await getRentals({
      unlinked_only: true,
      page: 1,
      page_size: 100,
    })
    availableRentals.value = res.items
  } catch {
    availableRentals.value = []
  }
  linkDialogVisible.value = true
}

async function handleConfirmLink() {
  if (!record.value?.id) return
  if (linkForm.selected.length === 0) {
    ElMessage.warning('请至少选择一台设备')
    return
  }
  linkSubmitting.value = true
  try {
    await linkContractRentals(record.value.id, linkForm.selected)
    ElMessage.success(`已关联 ${linkForm.selected.length} 台设备`)
    linkDialogVisible.value = false
    fetchRecord()
  } catch {
    // 错误已统一处理
  } finally {
    linkSubmitting.value = false
  }
}

// ============================================================
// 取消关联设备（表格行内操作）
// ============================================================
async function handleUnlink(row: ContractRentalItem) {
  if (!record.value?.id) return
  try {
    await ElMessageBox.confirm(
      `确认取消关联设备「${row.machine_model || row.id}」？`,
      '取消关联确认',
      {
        type: 'warning',
        confirmButtonText: '取消关联',
        cancelButtonText: '再想想',
      },
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await unlinkContractRentals(record.value.id, [row.id])
    ElMessage.success('已取消关联')
    fetchRecord()
  } catch {
    // 错误已统一处理
  } finally {
    acting.value = false
  }
}

// ============================================================
// 变更记录（页面底部预览表）
// ============================================================
const changeLogs = ref<ChangeLogEntry[]>([])
const newChangeContent = ref('')
const changeSubmitting = ref(false)

async function loadChangeLogs() {
  if (!record.value?.id) return
  try {
    const res = await listChangeLogs('contract', record.value.id)
    changeLogs.value = Array.isArray(res) ? res : []
  } catch {
    changeLogs.value = []
  }
}

async function handleAddChangeLog() {
  if (!newChangeContent.value.trim() || !record.value?.id) return
  changeSubmitting.value = true
  try {
    await createChangeLog({
      target_type: 'contract',
      target_id: record.value.id,
      content: newChangeContent.value.trim(),
    })
    newChangeContent.value = ''
    await loadChangeLogs()
    ElMessage.success('已添加')
  } catch {
    // 错误已统一处理
  } finally {
    changeSubmitting.value = false
  }
}

/** 滚动锚点到页面底部变更记录区域 */
function scrollToChangeLogs() {
  const el = document.getElementById('changelog-section')
  if (el) el.scrollIntoView({ behavior: 'smooth' })
}

function formatChangelogTime(s?: string | null) {
  if (!s) return '-'
  return s.slice(0, 16).replace('T', ' ')
}

onMounted(() => {
  fetchRecord().then(() => loadChangeLogs())
})

// 监听路由参数变化，同一组件内切换合同时重新加载
watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      fetchRecord().then(() => loadChangeLogs())
    }
  },
)
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
          <span class="header-customer">{{ record?.customer_name || '-' }}</span>
          <el-tag
            v-if="record?.status"
            :type="statusTagType(record.status)"
            size="small"
          >{{ statusLabel(record.status) }}</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <template v-if="record?.status !== 'reclaimed'">
          <el-button :icon="Document" @click="handleEdit">编辑</el-button>
          <el-button type="danger" :loading="acting" @click="handleDelete">删除</el-button>
          <el-button type="success" :disabled="acting" @click="handleSendProvision">发送开通邮件</el-button>
          <el-button type="warning" :disabled="acting" @click="handleSendExpiry">发送临期提醒</el-button>
          <el-button type="danger" :disabled="acting" @click="handleReclaim">标记回收</el-button>
        </template>
        <el-button type="success" :disabled="acting || record?.has_renewal" @click="handleRenew">续期</el-button>
        <el-button @click="scrollToChangeLogs">变更记录</el-button>
        <el-button type="primary" @click="goAttachments">
          <el-icon class="btn-icon"><Paperclip /></el-icon>附件管理
        </el-button>
      </div>
    </div>

    <!-- 基本信息 -->
    <section class="detail-section">
      <div class="dialog-section-title">合同信息</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="合同名称">{{ record?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ record?.customer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同编号">
          {{ record?.contract_no || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ formatDate(record?.start_date) }}</el-descriptions-item>
        <el-descriptions-item label="到期日期">{{ formatDate(record?.end_date) }}</el-descriptions-item>
        <el-descriptions-item label="计费方式">{{ billingLabel(record?.billing_model) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag
            v-if="record?.status"
            :type="statusTagType(record.status)"
            size="small"
          >{{ statusLabel(record.status) }}</el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">
          {{ record?.amount != null ? `¥${record.amount.toFixed(2)}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="设备数">{{ record?.rental_count ?? 0 }} 台</el-descriptions-item>
        <el-descriptions-item label="联系人数">{{ record?.contact_count ?? 0 }} 人</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="3">
          {{ formatDateTime(record?.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间" :span="3">
          {{ formatDateTime(record?.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">
          <span v-if="record?.remark">{{ record.remark }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 续期链路 -->
    <section v-if="record?.renewal_chain && record.renewal_chain.length > 1" class="detail-section">
      <div class="dialog-section-title">续期链路</div>
      <el-table
        :data="record.renewal_chain"
        :show-header="false"
        size="small"
        style="width: 100%"
        :row-class-name="renewalRowClass"
        @row-click="handleRenewalRowClick"
      >
        <el-table-column width="120">
          <template #default="{ row }">
            <el-tag
              :type="row.is_current ? 'primary' : 'info'"
              effect="plain"
              size="small"
            >
              <template v-if="row.renewal_seq === 0">📄 原合同</template>
              <template v-else>🔄 续期{{ row.renewal_seq }}</template>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column min-width="200">
          <template #default="{ row }">
            <span :class="{ 'renewal-name-current': row.is_current }">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column width="220">
          <template #default="{ row }">
            <span class="renewal-date">{{ formatDate(row.start_date) }} ~ {{ formatDate(row.end_date) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 关联设备 -->
    <section class="detail-section">
      <div class="section-toolbar">
        <div class="dialog-section-title">
          关联设备
          <span class="muted">（共 {{ record?.rentals?.length || 0 }} 台）</span>
        </div>
        <div v-if="record?.status !== 'reclaimed'" class="section-actions">
          <el-button
            type="primary"
            :icon="Connection"
            @click="openLinkDialog"
          >关联设备</el-button>
        </div>
      </div>
      <el-table
        :data="record?.rentals || []"
        row-key="id"
        stripe
        style="width: 100%;"
      >
        <template #empty>
          <div class="table-empty table-empty--compact">
            <el-empty description="尚未关联设备" :image-size="64" />
          </div>
        </template>
        <el-table-column prop="machine_model" label="机器型号" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span
              v-if="row.machine_model"
              class="col-name-link"
              @click="goRental(row.id)"
            >{{ row.machine_model }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="机架位置" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.rack_location">{{ row.rack_location }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="公网 IP" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span
              v-if="Array.isArray(row.public_ips) && row.public_ips.length"
              class="col-ip"
            >{{ row.public_ips.join(', ') }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作系统" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.os_version" class="col-secondary">{{ row.os_version }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="rentalStatusTagType(row.status)">
              {{ rentalStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="record?.status !== 'reclaimed'"
          label="操作"
          width="110"
          fixed="right"
          align="center"
        >
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                link
                type="danger"
                :loading="acting"
                @click="handleUnlink(row)"
              >取消关联</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 关联联系人 -->
    <section class="detail-section">
      <div class="dialog-section-title">
        关联联系人
        <span class="muted">（共 {{ record?.contacts?.length || 0 }} 人）</span>
      </div>
      <el-table
        :data="record?.contacts || []"
        row-key="contact_id"
        stripe
        style="width: 100%;"
      >
        <template #empty>
          <div class="table-empty table-empty--compact">
            <el-empty description="尚未关联联系人" :image-size="64" />
          </div>
        </template>
        <el-table-column prop="name" label="姓名" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.name" class="col-name">{{ row.name }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.email" class="col-secondary">{{ row.email }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }: { row: ContractContactItem }">
            <el-tag
              :type="row.recipient_type === 'to' ? 'primary' : 'info'"
              size="small"
            >
              {{ row.recipient_type === 'to' ? '收件人' : '抄送' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 关联设备弹窗 -->
    <el-dialog
      v-model="linkDialogVisible"
      title="关联设备到合同"
      width="560px"
      destroy-on-close
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>从可用设备中多选关联到本合同；已关联设备不会出现在列表中。</span>
      </div>
      <div class="dialog-section">
        <div class="dialog-section-title">选择设备</div>
        <div v-if="candidateRentals.length === 0" class="table-empty table-empty--compact">
          <el-empty description="暂无可关联设备" :image-size="64" />
        </div>
        <el-form v-else label-position="top" @submit.prevent>
          <el-form-item label="可用设备">
            <el-select
              v-model="linkForm.selected"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择要关联的设备"
              style="width: 100%"
            >
              <el-option
                v-for="r in candidateRentals"
                :key="r.id"
                :label="rentalLabel(r)"
                :value="r.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="linkDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="linkSubmitting"
            :disabled="linkForm.selected.length === 0"
            @click="handleConfirmLink"
          >
            关联（{{ linkForm.selected.length }}）
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 附件状态 -->
    <section class="detail-section">
      <div class="section-toolbar">
        <div class="dialog-section-title">附件状态</div>
        <div class="section-actions">
          <el-button type="primary" size="small" @click="goAttachments">
            <el-icon class="btn-icon"><Paperclip /></el-icon>附件管理
          </el-button>
        </div>
      </div>
      <div class="attachment-status-grid">
        <div
          v-for="(label, code) in attCategoryLabels"
          :key="code"
          class="status-card"
        >
          <div class="status-card-header">
            <span>{{ label }}</span>
            <el-tag
              :type="attStatusTagType(
                attachmentSummary?.items?.[code]?.confirmed ?? false,
                attachmentSummary?.items?.[code]?.file_count ?? 0
              )"
              size="small"
            >
              {{ attStatusText(
                attachmentSummary?.items?.[code]?.confirmed ?? false,
                attachmentSummary?.items?.[code]?.file_count ?? 0
              ) }}
            </el-tag>
          </div>
          <div class="status-card-body">
            <span class="status-stat">
              <strong>{{ attachmentSummary?.items?.[code]?.file_count ?? 0 }}</strong> 个文件
            </span>
          </div>
        </div>
      </div>
      <div class="attachment-summary">
        <span class="muted">
          总计：{{ attachmentSummary?.confirmed_items ?? 0 }} / {{ attachmentSummary?.total_items ?? 0 }} 项已确认
        </span>
        <el-tag
          v-if="attachmentSummary?.all_confirmed"
          type="success"
          size="small"
        >
          全部完成
        </el-tag>
      </div>
    </section>

    <!-- 变更记录（页面底部） -->
    <section id="changelog-section" class="detail-section">
      <div class="dialog-section-title">
        变更记录
        <span class="muted">（共 {{ changeLogs.length }} 条）</span>
      </div>
      <el-table :data="changeLogs" stripe style="width:100%">
        <template #empty>
          <div class="table-empty table-empty--compact">
            <el-empty description="暂无变更记录" :image-size="64" />
          </div>
        </template>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            <span class="col-secondary">{{ formatChangelogTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
      </el-table>
      <div class="changelog-add">
        <el-input
          v-model="newChangeContent"
          placeholder="输入变更内容"
          maxlength="500"
          show-word-limit
          class="changelog-input"
        />
        <el-button
          type="primary"
          :disabled="!newChangeContent.trim()"
          :loading="changeSubmitting"
          @click="handleAddChangeLog"
        >
          添加变更记录
        </el-button>
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
.header-customer {
  margin-right: 0;
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

.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}
.section-toolbar .dialog-section-title {
  margin: 0;
  padding-top: 0;
  padding-right: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.section-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-section > .dialog-section-title {
  margin-bottom: 12px;
}

.hint {
  color: var(--text-secondary);
  font-size: 13px;
  padding: 4px 0;
  line-height: 1.5;
}
.muted {
  color: var(--text-secondary);
  font-size: 12px;
  margin-left: 4px;
  font-weight: 400;
  opacity: 0.85;
}

.attachment-status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}
.status-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px 16px;
}
.status-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.status-card-body {
  padding: 0;
}
.status-stat {
  font-size: 13px;
  color: var(--text-secondary);
}
.status-stat strong {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.attachment-summary {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.changelog-add {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.changelog-input {
  flex: 1;
  min-width: 0;
}

.renewal-row-current {
  background-color: rgba(37, 99, 235, 0.06);
}
.renewal-row-clickable {
  cursor: pointer;
}
.renewal-row-clickable:hover > td {
  background-color: rgba(37, 99, 235, 0.04) !important;
}
.renewal-name-current {
  font-weight: 600;
  color: var(--text-primary);
}
.renewal-date {
  font-size: 13px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.col-muted {
  color: #c0c4cc;
}
.col-name {
  color: var(--text-primary);
  font-weight: 600;
}
.col-name-link {
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
.col-ip {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: var(--text-primary);
}
.col-secondary {
  color: var(--text-secondary);
}
.action-buttons {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
</style>
