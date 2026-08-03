<script setup lang="ts">
/**
 * 合同管理 - 创建 / 编辑（共用页面）
 *
 * 复用规则：
 *  - 路由 /contracts/create → 新建模式
 *  - 路由 /contracts/:id/edit → 编辑模式
 *
 * 表单字段：客户、合同名称、合同编号、起止日期、计费方式、备注、关联设备、关联联系人
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Document, Connection, User, Calendar } from '@element-plus/icons-vue'
import {
  createContract,
  getContract,
  linkContractRentals,
  unlinkContractRentals,
  updateContract,
  type ContractBillingModel,
  type ContractCreatePayload,
  type ContractDetail,
  type ContractUpdatePayload,
  type ContractStatus,
} from '@/api/modules/contract'
import { getCustomers, type Customer } from '@/api/modules/customer'
import { getContacts, type Contact } from '@/api/modules/contact'
import { getRentals, type RentalListItem } from '@/api/modules/rental'
import { CONTRACT_BILLING_MODEL_OPTIONS } from '@/lib/contract'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const contractId = computed(() => (route.params.id as string) || '')

// ============================================================
// 续期模式
// ============================================================
const renewFromId = computed(() => (route.query.renew_from as string) || '')
const isRenewal = computed(() => !!renewFromId.value)

async function loadRenewalSource() {
  if (!renewFromId.value) return
  _loadingDetail.value = true
  try {
    const original = await getContract(renewFromId.value)
    if (!original) {
      ElMessage.warning('续期来源合同不存在')
      return
    }
    // 回填表单
    form.customer_id = original.customer_id
    form.billing_model = (original.billing_model as ContractBillingModel) || 'monthly'
    form.name = original.name + '(续期)'
    form.start_date = original.end_date
    // 建议 end_date：原合同时长
    if (original.start_date && original.end_date) {
      const duration = new Date(original.end_date).getTime() - new Date(original.start_date).getTime()
      const newEnd = new Date(new Date(original.end_date).getTime() + 86400000 + duration)
      form.end_date = newEnd.toISOString().slice(0, 10)
    }
    form.renewed_from_id = original.id
    form.amount = original.amount ?? undefined
    form.remark = original.remark ?? ''
    form.sort_order = original.sort_order ?? 0
    // 预选原合同设备
    if (original.rentals?.length) {
      form.rental_ids = original.rentals.map((r: any) => r.id)
    }
    // 预选原合同联系人
    if (original.contacts?.length) {
      form.contacts = original.contacts.map((c) => ({
        contact_id: c.contact_id,
        recipient_type: c.recipient_type,
      }))
    }
    // 加载客户联系人 & 可用设备，重建设备列表
    await Promise.all([
      loadCustomerContacts(original.customer_id),
      loadAvailableRentals(),
    ])
    buildLinkedDetails()
  } catch {
    ElMessage.warning('加载续期来源合同失败')
  } finally {
    _loadingDetail.value = false
  }
}

// ============================================================
// 表单数据
// ============================================================
interface ContractForm {
  customer_id: string
  name: string
  contract_no: string
  start_date: string
  end_date: string
  billing_model: ContractBillingModel
  amount?: number
  remark: string
  rental_ids: string[]
  contacts: Array<{ contact_id: string; recipient_type: 'to' | 'cc' }>
  renewed_from_id?: string
  status?: string
  sort_order: number
}

const form = reactive<ContractForm>({
  customer_id: '',
  name: '',
  contract_no: '',
  start_date: '',
  end_date: '',
  billing_model: 'monthly',
  amount: undefined,
  remark: '',
  rental_ids: [],
  contacts: [],
  status: undefined,
  sort_order: 0,
})

// ============================================================
// 客户 / 联系人
// ============================================================
const customerOptions = ref<Customer[]>([])
const customerContacts = ref<Contact[]>([])

/** 内部同事列表（全局可选，不限定客户） */
const colleagueOptions = ref<Contact[]>([])

/** 合并客户联系人和内部同事供 to/cc 下拉使用 */
const allContactOptions = computed(() => {
  return [...colleagueOptions.value, ...customerContacts.value]
})

async function loadCustomers() {
  try {
    const res = await getCustomers({ business_type: '算力租赁', page: 1, page_size: 100 })
    customerOptions.value = res.items.filter((c) => c.status === 'active')
  } catch {
    // 错误已统一处理
  }
}

async function loadCustomerContacts(customerId: string) {
  if (!customerId) {
    customerContacts.value = []
    return
  }
  try {
    const res = await getContacts({
      type: 'customer',
      customer_id: customerId,
      page: 1,
      page_size: 100,
    })
    customerContacts.value = res.items.filter((c) => c.is_active)
  } catch {
    customerContacts.value = []
  }
}

async function loadColleagues() {
  try {
    const res = await getContacts({ type: 'colleague', page: 1, page_size: 100 })
    colleagueOptions.value = res.items.filter((c) => c.is_active)
  } catch {
    colleagueOptions.value = []
  }
}

// 切换客户时：清空已选设备（设备只属于一个客户） + 重载联系人
// 使用 _loadingDetail 标志防止 loadDetail 触发本 watch
const _loadingDetail = ref(false)

watch(
  () => form.customer_id,
  async (newId, oldId) => {
    if (_loadingDetail.value) return
    if (newId !== oldId) {
      form.rental_ids = []
      linkedRentalDetails.value = []
      loadCustomerContacts(newId)
    } else {
      loadCustomerContacts(newId)
    }
    await loadAvailableRentals()
    buildLinkedDetails()
  },
)

// ============================================================
// 关联设备（参照 detail.vue 风格）
// ============================================================
const linkDialogVisible = ref(false)
const linkForm = reactive<{ selected: string[] }>({ selected: [] })
const linkSubmitting = ref(false)
const availableRentals = ref<RentalListItem[]>([])

/** 已关联设备的详情（表格展示用，直接从 detail 或表单推导） */
const linkedRentalDetails = ref<(RentalListItem & { isNew?: boolean })[]>([])

function rentalLabel(row: RentalListItem) {
  const rack = row.rack_location ? ` · ${row.rack_location}` : ' · -'
  return `${row.machine_model}${rack}`
}

/** 弹窗「可选设备」：未关联的设备（排除 form.rental_ids） */
const candidateRentals = computed<RentalListItem[]>(() => {
  const selected = new Set(form.rental_ids)
  return availableRentals.value.filter((r) => !selected.has(r.id))
})

/** 从 detail 重建设备列表 */
function buildLinkedDetails() {
  const result: typeof linkedRentalDetails.value = []

  if (detail.value) {
    const ids = new Set(form.rental_ids)
    // 先加入已关联的旧设备
    for (const r of detail.value.rentals || []) {
      if (ids.has(r.id)) {
        result.push({
          id: r.id,
          customer: { id: form.customer_id, name: '' },
          machine_model: r.machine_model,
          rack_location: r.rack_location || null,
          private_ip: r.private_ip || '',
          start_date: '',
          end_date: '',
          status: '空闲中' as const,
          created_at: '',
        })
        ids.delete(r.id)
      }
    }
    // 再加入新选的设备（从 availableRentals 匹配）
    for (const id of ids) {
      const found = availableRentals.value.find((r) => r.id === id)
      if (found) {
        result.push({ ...found, isNew: true })
      }
    }
  } else {
    // 新建模式：直接从 availableRentals 匹配 form.rental_ids
    for (const id of form.rental_ids) {
      const found = availableRentals.value.find((r) => r.id === id)
      if (found) {
        result.push({ ...found, isNew: true })
      }
    }
  }

  linkedRentalDetails.value = result
}

/** 加载可选设备（仅未关联的，不注入已关联） */
async function loadAvailableRentals() {
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
}

async function openLinkDialog() {
  linkForm.selected = []
  if (availableRentals.value.length === 0) {
    await loadAvailableRentals()
  }
  linkDialogVisible.value = true
}

async function handleConfirmLink() {
  if (linkForm.selected.length === 0) {
    ElMessage.warning('请至少选择一台设备')
    return
  }
  linkSubmitting.value = true
  try {
    const newSet = new Set(form.rental_ids)
    linkForm.selected.forEach((id) => newSet.add(id))
    form.rental_ids = [...newSet]
    ElMessage.success(`已选择 ${linkForm.selected.length} 台设备`)
    linkDialogVisible.value = false
    buildLinkedDetails()
  } finally {
    linkSubmitting.value = false
  }
}

// 勾选取消关联
const selectedRentalIds = ref<string[]>([])

function handleRentalSelect(selection: any[]) {
  selectedRentalIds.value = selection.map((r: any) => r.id)
}

async function handleUnlinkRental() {
  if (selectedRentalIds.value.length === 0) {
    ElMessage.warning('请先勾选要取消关联的设备')
    return
  }
  const ids = selectedRentalIds.value
  form.rental_ids = form.rental_ids.filter((id) => !ids.includes(id))
  selectedRentalIds.value = []
  buildLinkedDetails()
  ElMessage.success(`已取消选择 ${ids.length} 台设备`)
}

// ============================================================
// 联系人 to/cc 双向同步（独立数组，允许重叠）
// ============================================================
const toContactIds = computed<string[]>({
  get: () =>
    form.contacts.filter((c) => c.recipient_type === 'to').map((c) => c.contact_id),
  set: (ids: string[]) => {
    const ccContacts = form.contacts.filter((c) => c.recipient_type === 'cc')
    form.contacts = [
      ...ccContacts,
      ...ids.map((id) => ({ contact_id: id, recipient_type: 'to' as const })),
    ]
  },
})

const ccContactIds = computed<string[]>({
  get: () =>
    form.contacts.filter((c) => c.recipient_type === 'cc').map((c) => c.contact_id),
  set: (ids: string[]) => {
    const toContacts = form.contacts.filter((c) => c.recipient_type === 'to')
    form.contacts = [
      ...toContacts,
      ...ids.map((id) => ({ contact_id: id, recipient_type: 'cc' as const })),
    ]
  },
})

// ============================================================
// 加载详情（编辑模式）
// ============================================================
const detail = ref<ContractDetail | null>(null)
const loadingDetail = ref(false)

async function loadDetail() {
  if (!contractId.value) return
  _loadingDetail.value = true
  loadingDetail.value = true
  try {
    const data = await getContract(contractId.value)
    detail.value = data
    form.customer_id = data.customer_id
    form.name = data.name
    form.contract_no = data.contract_no ?? ''
    form.start_date = data.start_date
    form.end_date = data.end_date
    form.billing_model = (data.billing_model as ContractBillingModel) || 'monthly'
    form.amount = data.amount ?? undefined
    form.remark = data.remark ?? ''
    form.status = data.status ?? undefined
    form.sort_order = data.sort_order ?? 0
    form.rental_ids = (data.rentals || []).map((r) => r.id)
    form.contacts = (data.contacts || []).map((c) => ({
      contact_id: c.contact_id,
      recipient_type: c.recipient_type,
    }))

    await Promise.all([
      loadCustomerContacts(data.customer_id),
      loadAvailableRentals(),
    ])
    buildLinkedDetails()
  } catch {
    // 错误已统一处理
  } finally {
    loadingDetail.value = false
    _loadingDetail.value = false
  }
}

// ============================================================
// 校验
// ============================================================
const formRef = ref<FormInstance>()
const rules: FormRules = {
  customer_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
  name: [{ required: true, message: '请输入合同名称', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择到期日期', trigger: 'change' }],
}

// ============================================================
// 提交
// ============================================================
const submitting = ref(false)

function buildCreatePayload(): ContractCreatePayload {
  return {
    customer_id: form.customer_id,
    name: form.name.trim(),
    contract_no: form.contract_no.trim() || undefined,
    start_date: form.start_date,
    end_date: form.end_date,
    billing_model: form.billing_model,
    amount: form.amount,
    remark: form.remark.trim() || undefined,
    rental_ids: form.rental_ids.length ? form.rental_ids : undefined,
    contacts: form.contacts.length ? form.contacts : undefined,
    renewed_from_id: form.renewed_from_id || undefined,
    sort_order: form.sort_order,
  }
}

function buildUpdatePayload(): ContractUpdatePayload {
  const payload: ContractUpdatePayload = {}
  payload.name = form.name.trim()
  payload.contract_no = form.contract_no.trim() || undefined
  payload.start_date = form.start_date
  payload.end_date = form.end_date
  payload.billing_model = form.billing_model
  payload.amount = form.amount
  payload.remark = form.remark.trim() || undefined
  payload.status = form.status as ContractStatus | undefined
  payload.sort_order = form.sort_order
  // contacts 全量替换（后端约定：传则替换，不传则保留）
  payload.contacts = form.contacts
  return payload
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.error('请检查表单填写')
    return
  }
  // 简易业务校验：end_date >= start_date
  if (form.start_date && form.end_date && form.end_date < form.start_date) {
    ElMessage.error('到期日期不能早于开始日期')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateContract(contractId.value, buildUpdatePayload())
      // 同步关联设备
      const existingIds = new Set((detail.value?.rentals || []).map(r => r.id))
      const currentIds = new Set(form.rental_ids)
      const toLink = form.rental_ids.filter(id => !existingIds.has(id))
      const toUnlink = [...existingIds].filter(id => !currentIds.has(id))
      if (toLink.length > 0) {
        await linkContractRentals(contractId.value, toLink)
      }
      if (toUnlink.length > 0) {
        await unlinkContractRentals(contractId.value, toUnlink)
      }
      ElMessage.success('保存成功')
      router.replace({ name: 'ContractDetail', params: { id: contractId.value } })
    } else {
      const created = await createContract(buildCreatePayload())
      ElMessage.success('创建成功')
      router.replace({ name: 'ContractDetail', params: { id: created.id } })
    }
  } catch {
    // 错误已统一处理
  } finally {
    submitting.value = false
  }
}

function cancel() {
  if (isEdit.value && contractId.value) {
    router.push({ name: 'ContractDetail', params: { id: contractId.value } })
  } else {
    router.push({ name: 'ContractList' })
  }
}

onMounted(async () => {
  await loadCustomers()
  if (isRenewal.value) {
    await loadColleagues()
    await loadRenewalSource()
  } else if (isEdit.value) {
    await loadColleagues()
    await loadDetail()
  } else {
    await loadColleagues()
  }
})
</script>

<template>
  <div class="page-container" v-loading="loadingDetail">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            {{ isRenewal ? '续期合同' : (isEdit ? '编辑合同' : '新建合同') }}
          </span>
          <el-button link @click="cancel">返回</el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        @submit.prevent
      >
        <!-- 基础信息 -->
        <div class="section-title">
          <el-icon><Document /></el-icon>
          基础信息
        </div>
        <el-form-item label="客户" prop="customer_id">
          <el-select
            v-model="form.customer_id"
            placeholder="请选择客户"
            filterable
            style="width: 100%"
            :disabled="isEdit"
          >
            <el-option
              v-for="c in customerOptions"
              :key="c.id"
              :label="c.name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="合同名称" prop="name">
          <el-input v-model="form.name" placeholder="如 主合同-2026" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="合同编号" prop="contract_no">
          <el-input v-model="form.contract_no" placeholder="可选，如 CT-2026-001" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="序号">
          <el-input-number v-model="form.sort_order" :min="0" :step="1" placeholder="序号" />
        </el-form-item>

        <!-- 状态（仅编辑模式） -->
        <el-form-item v-if="isEdit" label="合同状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 200px">
            <el-option label="生效中" value="active" />
            <el-option label="临期" value="expiring" />
            <el-option label="已到期" value="expired" />
            <el-option label="已回收" value="reclaimed" />
          </el-select>
        </el-form-item>

        <!-- 服务周期 -->
        <div class="section-title">
          <el-icon><Calendar /></el-icon>
          服务周期
        </div>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择开始日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="到期日期" prop="end_date">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择到期日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="计费方式">
          <el-radio-group v-model="form.billing_model">
            <el-radio-button
              v-for="opt in CONTRACT_BILLING_MODEL_OPTIONS"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="合同金额">
          <el-input-number
            v-model="form.amount"
            :precision="2"
            :min="0"
            :controls="false"
            placeholder="可选，单位元"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 关联设备 -->
        <div class="section-title">
          <el-icon><Connection /></el-icon>
          关联设备
        </div>
        <div class="rental-section">
          <div class="rental-toolbar">
            <span class="rental-count">已选 {{ form.rental_ids.length }} 台</span>
            <div class="rental-actions">
              <el-button
                type="primary"
                :icon="Connection"
                :disabled="!form.customer_id"
                @click="openLinkDialog"
              >关联设备</el-button>
              <el-button
                type="danger"
                plain
                :disabled="selectedRentalIds.length === 0"
                @click="handleUnlinkRental"
              >
                取消关联 ({{ selectedRentalIds.length }})
              </el-button>
            </div>
          </div>
          <el-table
            :data="linkedRentalDetails"
            size="small"
            stripe
            border
            empty-text="尚未关联设备"
            style="width: 100%;"
            @selection-change="handleRentalSelect"
          >
            <el-table-column type="selection" width="50" />
            <el-table-column prop="machine_model" label="机器型号" min-width="180" show-overflow-tooltip />
            <el-table-column label="机架位置" min-width="140">
              <template #default="{ row }">
                {{ row.rack_location || '-' }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 关联设备弹窗 -->
        <el-dialog
          v-model="linkDialogVisible"
          title="关联设备到合同"
          width="560px"
          :close-on-click-modal="false"
        >
          <div v-if="candidateRentals.length === 0" class="hint">
            暂无可关联的设备（所有设备已关联到此合同或无可用设备）
          </div>
          <el-select
            v-else
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
          <template #footer>
            <el-button @click="linkDialogVisible = false">取消</el-button>
            <el-button
              type="primary"
              :loading="linkSubmitting"
              :disabled="linkForm.selected.length === 0"
              @click="handleConfirmLink"
            >
              关联（{{ linkForm.selected.length }}）
            </el-button>
          </template>
        </el-dialog>

        <!-- 关联联系人 -->
        <div class="section-title">
          <el-icon><User /></el-icon>
          关联联系人
        </div>
        <el-form-item label="收件人 (TO)">
          <div v-if="!form.customer_id" class="hint">请先选择客户</div>
          <div v-else-if="allContactOptions.length === 0" class="hint">
            暂无可用联系人，请先到【客户管理 → 联系人】或【系统配置 → 内部同事】添加
          </div>
          <el-select
            v-else
            v-model="toContactIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            placeholder="选择收件人（含内部同事）"
            style="width: 100%"
          >
            <el-option
              v-for="c in allContactOptions"
              :key="c.id"
              :label="`${c.name} (${c.email})${c.customer_id ? '' : ' · 内部'}`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="抄送人 (CC)">
          <div v-if="!form.customer_id" class="hint">请先选择客户</div>
          <div v-else-if="allContactOptions.length === 0" class="hint">
            暂无可用联系人
          </div>
          <el-select
            v-else
            v-model="ccContactIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            placeholder="选择抄送人（含内部同事）"
            style="width: 100%"
          >
            <el-option
              v-for="c in allContactOptions"
              :key="c.id"
              :label="`${c.name} (${c.email})${c.customer_id ? '' : ' · 内部'}`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>

        <!-- 备注 -->
        <el-form-item label="备注" style="margin-top: 8px;">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="3"
            placeholder="可选"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <div class="form-actions">
        <el-button @click="cancel">取消</el-button>
        <div class="spacer" />
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 18px 0 12px;
  padding-left: 10px;
  border-left: 3px solid var(--primary-color);
  display: flex;
  align-items: center;
  gap: 6px;
}
.section-title .el-icon {
  color: var(--primary-color);
  font-size: 16px;
}
.hint {
  color: #909399;
  font-size: 13px;
  padding: 8px 0;
}
.form-actions {
  display: flex;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
.spacer {
  flex: 1;
}
.rental-section {
  margin-bottom: 12px;
}
.rental-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 8px;
}
.rental-count {
  font-size: 13px;
  color: #909399;
}
.rental-actions {
  display: flex;
  gap: 8px;
}
</style>
