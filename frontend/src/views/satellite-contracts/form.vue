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
}

const form = reactive<SatelliteContractForm>({
  customer_id: '',
  name: '',
  contract_no: '',
  remark: '',
})

// ============================================================
// 客户选项
// ============================================================
const customerOptions = ref<Customer[]>([])

async function loadCustomers() {
  try {
    const res = await getCustomers({ page: 1, page_size: 100 })
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
