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
  updateContract,
  type ContractBillingModel,
  type ContractCreatePayload,
  type ContractDetail,
  type ContractUpdatePayload,
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
// 表单数据
// ============================================================
interface ContractForm {
  customer_id: string
  name: string
  contract_no: string
  start_date: string
  end_date: string
  billing_model: ContractBillingModel
  remark: string
  rental_ids: string[]
  contacts: Array<{ contact_id: string; recipient_type: 'to' | 'cc' }>
}

const form = reactive<ContractForm>({
  customer_id: '',
  name: '',
  contract_no: '',
  start_date: '',
  end_date: '',
  billing_model: 'monthly',
  remark: '',
  rental_ids: [],
  contacts: [],
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
    const res = await getCustomers({ page: 1, page_size: 100 })
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
watch(
  () => form.customer_id,
  (newId, oldId) => {
    if (newId !== oldId) {
      form.rental_ids = []
      loadCustomerContacts(newId)
    } else {
      loadCustomerContacts(newId)
    }
  },
)

// ============================================================
// 设备选择（两步加载：已关联 + 未关联）
// ============================================================
const rentalOptions = ref<RentalListItem[]>([])

async function loadCustomerRentals(customerId: string) {
  // 1. 收集当前合同已关联的设备 id（编辑模式）
  let linkedIds: string[] = []
  if (isEdit.value && detail.value) {
    linkedIds = (detail.value.rentals || []).map((r) => r.id)
  }

  // 2. 加载所有未关联合同的设备
  try {
    const res = await getRentals({ unlinked_only: true, page: 1, page_size: 200 })
    rentalOptions.value = res.items
  } catch {
    rentalOptions.value = []
  }

  // 3. 已关联设备也加入选项（如果不在返回结果中）
  if (linkedIds.length > 0 && detail.value) {
    for (const r of detail.value.rentals || []) {
      if (!rentalOptions.value.find((opt) => opt.id === r.id)) {
        rentalOptions.value.push({
          id: r.id,
          customer: { id: customerId, name: '' },
          machine_model: r.machine_model,
          rack_location: r.rack_location || null,
          private_ip: r.private_ip || '',
          start_date: '',
          end_date: '',
          status: '空闲中' as const,
          created_at: '',
        })
      }
    }
  }
}

watch(
  () => form.customer_id,
  (newId) => {
    loadCustomerRentals(newId)
  },
)

function rentalLabel(row: RentalListItem) {
  const rack = row.rack_location ? ` · ${row.rack_location}` : ' · -'
  return `${row.machine_model}${rack}`
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
    form.remark = data.remark ?? ''
    // 已关联设备 id 列表
    form.rental_ids = (data.rentals || []).map((r) => r.id)
    // 已关联联系人
    form.contacts = (data.contacts || []).map((c) => ({
      contact_id: c.contact_id,
      recipient_type: c.recipient_type,
    }))

    // 编辑时把关联客户/同事联系人列表都拉好（同时回填已选）
    await Promise.all([
      loadCustomerContacts(data.customer_id),
      loadCustomerRentals(data.customer_id),
    ])
  } catch {
    // 错误已统一处理
  } finally {
    loadingDetail.value = false
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
    remark: form.remark.trim() || undefined,
    rental_ids: form.rental_ids.length ? form.rental_ids : undefined,
    contacts: form.contacts.length ? form.contacts : undefined,
  }
}

function buildUpdatePayload(): ContractUpdatePayload {
  const payload: ContractUpdatePayload = {}
  payload.name = form.name.trim()
  payload.contract_no = form.contract_no.trim() || undefined
  payload.start_date = form.start_date
  payload.end_date = form.end_date
  payload.billing_model = form.billing_model
  payload.remark = form.remark.trim() || undefined
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
      // 同步关联设备：已选但未关联的 → 关联
      const existingIds = new Set((detail.value?.rentals || []).map(r => r.id))
      const toLink = form.rental_ids.filter(id => !existingIds.has(id))
      if (toLink.length > 0) {
        await linkContractRentals(contractId.value, toLink)
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
  await Promise.all([loadCustomers(), loadColleagues()])
  if (isEdit.value) {
    await loadDetail()
  }
})
</script>

<template>
  <div class="page-container" v-loading="loadingDetail">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            {{ isEdit ? '编辑合同' : '新建合同' }}
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
        <el-row :gutter="16">
          <el-col :span="12">
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
                  :label="`${c.name} (${c.code})`"
                  :value="c.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同名称" prop="name">
              <el-input v-model="form.name" placeholder="如 主合同-2026" maxlength="255" show-word-limit />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同编号" prop="contract_no">
              <el-input v-model="form.contract_no" placeholder="可选，如 CT-2026-001" maxlength="100" show-word-limit />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 服务周期 -->
        <div class="section-title">
          <el-icon><Calendar /></el-icon>
          服务周期
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker
                v-model="form.start_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择开始日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="到期日期" prop="end_date">
              <el-date-picker
                v-model="form.end_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择到期日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
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
          </el-col>
        </el-row>

        <!-- 关联设备 -->
        <div class="section-title">
          <el-icon><Connection /></el-icon>
          关联设备
        </div>
        <el-form-item label="设备列表">
          <div v-if="rentalOptions.length === 0" class="hint">
            暂无可关联设备，请先到设备管理创建设备
          </div>
          <el-select
            v-else-if="rentalOptions.length > 0"
            v-model="form.rental_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            placeholder="选择要关联到合同的设备"
            style="width: 100%"
          >
            <el-option
              v-for="r in rentalOptions"
              :key="r.id"
              :label="rentalLabel(r)"
              :value="r.id"
            />
          </el-select>
          <div class="hint" style="margin-top: 4px;">
            {{ form.rental_ids.length ? `已选 ${form.rental_ids.length} 台` : '未选' }}
          </div>
        </el-form-item>

        <!-- 关联联系人 -->
        <div class="section-title">
          <el-icon><User /></el-icon>
          关联联系人
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
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
          </el-col>
          <el-col :span="12">
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
          </el-col>
        </el-row>

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
</style>
