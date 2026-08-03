<script setup lang="ts">
/**
 * 卫星数据合同 - 创建 / 编辑（共用页面）
 *
 * 复用规则：
 *  - 路由 /contracts/satellite-data/create → 新建模式
 *  - 路由 /contracts/satellite-data/:id/edit → 编辑模式
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import {
  createSatelliteContract,
  getSatelliteContract,
  updateSatelliteContract,
  type SatelliteContractCreatePayload,
  type SatelliteContractItem,
  type SatelliteContractUpdatePayload,
} from '@/api/modules/satellite-contract'
import { getCustomers, type Customer } from '@/api/modules/customer'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const contractId = computed(() => (route.params.id as string) || '')

// ============================================================
// 表单数据
// ============================================================
interface SatelliteContractForm {
  customer_id: string
  name: string
  contract_no: string
  remark: string
  sort_order: number
  // ADR-013 新增字段
  contract_type: string
  project_name: string
  party_a_name: string
  party_b_name: string
  start_date: string
  end_date: string
  amount: number | null
  contract_content: string
  delivery_requirements: string
  process_records: string
}

const form = reactive<SatelliteContractForm>({
  customer_id: '',
  name: '',
  contract_no: '',
  remark: '',
  sort_order: 0,
  contract_type: '',
  project_name: '',
  party_a_name: '',
  party_b_name: '',
  start_date: '',
  end_date: '',
  amount: null,
  contract_content: '',
  delivery_requirements: '',
  process_records: '',
})

// ============================================================
// 客户选项
// ============================================================
const customerOptions = ref<Customer[]>([])

async function loadCustomers() {
  try {
    const res = await getCustomers({ business_type: '卫星数据', page: 1, page_size: 100 })
    customerOptions.value = res.items.filter((c) => c.status === 'active')
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 加载详情（编辑模式）
// ============================================================
const detail = ref<SatelliteContractItem | null>(null)
const loadingDetail = ref(false)

async function loadDetail() {
  if (!contractId.value) return
  loadingDetail.value = true
  try {
    const data = await getSatelliteContract(contractId.value)
    detail.value = data
    form.customer_id = data.customer_id
    form.name = data.name
    form.contract_no = data.contract_no ?? ''
    form.remark = data.remark ?? ''
    form.sort_order = data.sort_order ?? 0
    // ADR-013 新增字段回填
    form.contract_type = data.contract_type ?? ''
    form.project_name = data.project_name ?? ''
    form.party_a_name = data.party_a_name ?? ''
    form.party_b_name = data.party_b_name ?? ''
    form.start_date = data.start_date ?? ''
    form.end_date = data.end_date ?? ''
    form.amount = data.amount ?? null
    form.contract_content = data.contract_content ?? ''
    form.delivery_requirements = data.delivery_requirements ?? ''
    form.process_records = data.process_records ?? ''
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
}

// ============================================================
// 提交
// ============================================================
const submitting = ref(false)

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.error('请检查表单填写')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      const payload: SatelliteContractUpdatePayload = {
        name: form.name.trim(),
        contract_no: form.contract_no.trim() || undefined,
        remark: form.remark.trim() || undefined,
        sort_order: form.sort_order,
        contract_type: form.contract_type.trim() || undefined,
        project_name: form.project_name.trim() || undefined,
        party_a_name: form.party_a_name.trim() || undefined,
        party_b_name: form.party_b_name.trim() || undefined,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
        amount: form.amount ?? undefined,
        contract_content: form.contract_content.trim() || undefined,
        delivery_requirements: form.delivery_requirements.trim() || undefined,
        process_records: form.process_records.trim() || undefined,
      }
      await updateSatelliteContract(contractId.value, payload)
      ElMessage.success('保存成功')
      router.replace({ name: 'SatelliteContractDetail', params: { id: contractId.value } })
    } else {
      const payload: SatelliteContractCreatePayload = {
        customer_id: form.customer_id,
        name: form.name.trim(),
        contract_no: form.contract_no.trim() || undefined,
        remark: form.remark.trim() || undefined,
        sort_order: form.sort_order,
        contract_type: form.contract_type.trim() || undefined,
        project_name: form.project_name.trim() || undefined,
        party_a_name: form.party_a_name.trim() || undefined,
        party_b_name: form.party_b_name.trim() || undefined,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
        amount: form.amount ?? undefined,
        contract_content: form.contract_content.trim() || undefined,
        delivery_requirements: form.delivery_requirements.trim() || undefined,
        process_records: form.process_records.trim() || undefined,
      }
      const created = await createSatelliteContract(payload)
      ElMessage.success('创建成功')
      router.replace({ name: 'SatelliteContractDetail', params: { id: created.id } })
    }
  } catch {
    // 错误已统一处理
  } finally {
    submitting.value = false
  }
}

function cancel() {
  if (isEdit.value && contractId.value) {
    router.push({ name: 'SatelliteContractDetail', params: { id: contractId.value } })
  } else {
    router.push({ name: 'SatelliteContractList' })
  }
}

onMounted(async () => {
  await loadCustomers()
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
            {{ isEdit ? '编辑卫星数据合同' : '新建卫星数据合同' }}
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
          <el-input v-model="form.name" placeholder="如 卫星数据合同-2026" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="合同编号" prop="contract_no">
          <el-input v-model="form.contract_no" placeholder="可选，如 WX-2026-001" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="序号">
          <el-input-number v-model="form.sort_order" :min="0" :step="1" placeholder="序号" />
        </el-form-item>

        <!-- ADR-013 新增：基本信息扩展 -->
        <el-divider />
        <div class="section-title">
          <el-icon><Document /></el-icon>
          合同扩展信息
        </div>
        <el-form-item label="合同类型">
          <el-input v-model="form.contract_type" placeholder="如 销售合同、采购合同" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="form.project_name" placeholder="项目名称" maxlength="255" show-word-limit />
        </el-form-item>

        <!-- ADR-013 新增：日期与金额 -->
        <el-divider />
        <div class="section-title">
          <el-icon><Document /></el-icon>
          日期与金额
        </div>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            placeholder="选择开始日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            placeholder="选择结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="合同金额">
          <el-input-number
            v-model="form.amount"
            :min="0"
            :precision="2"
            placeholder="合同金额"
            :controls="false"
            style="width: 100%"
          />
        </el-form-item>

        <!-- ADR-013 新增：甲乙方 -->
        <el-divider />
        <div class="section-title">
          <el-icon><Document /></el-icon>
          签约方信息
        </div>
        <el-form-item label="甲方名称">
          <el-input v-model="form.party_a_name" placeholder="甲方名称" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="乙方名称">
          <el-input v-model="form.party_b_name" placeholder="乙方名称" maxlength="255" show-word-limit />
        </el-form-item>

        <!-- ADR-013 新增：长文本区 -->
        <el-divider />
        <div class="section-title">
          <el-icon><Document /></el-icon>
          合同内容与要求
        </div>
        <el-form-item label="合同内容">
          <el-input
            v-model="form.contract_content"
            type="textarea"
            :rows="4"
            placeholder="合同主要内容"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="交付要求">
          <el-input
            v-model="form.delivery_requirements"
            type="textarea"
            :rows="4"
            placeholder="交付要求"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="过程记录">
          <el-input
            v-model="form.process_records"
            type="textarea"
            :rows="4"
            placeholder="过程记录"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>

        <!-- 备注 -->
        <el-divider />
        <el-form-item label="备注">
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
