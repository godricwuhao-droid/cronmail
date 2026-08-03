<script setup lang="ts">
/**
 * 算力服务合同 - 创建 / 编辑（共用页面）
 *
 * 复用规则：
 *  - 路由 /contracts/compute-service/create → 新建模式
 *  - 路由 /contracts/compute-service/:id/edit → 编辑模式
 *
 * ADR-012: 服务内容模型
 *  - 合同基本信息区：合同类型、甲乙方、金额、日期、关联合同
 *  - 服务行编辑器：动态表格，按 category 分组
 *  - 金额自动汇总与对比提示
 */
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Delete, Top, Bottom, MagicStick, Loading } from '@element-plus/icons-vue'
import request from '@/api'
import {
  createServiceContract,
  getServiceContract,
  updateServiceContract,
  listServiceContracts,
  type ServiceContractCreatePayload,
  type ServiceContractDetail,
  type ServiceContractUpdatePayload,
  type ContractType,
  type ServiceLineCreatePayload,
  type ServiceLineItem,
  type ServiceSpecification,
  type ServiceContractItem,
} from '@/api/modules/service-contract'
import { getCustomers, type Customer } from '@/api/modules/customer'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const contractId = computed(() => (route.params.id as string) || '')

// ============================================================
// 合同类型 → 甲乙方 label 联动
// ============================================================
const partyLabels = computed(() => {
  if (form.contract_type === 'sales') {
    return { a: '甲方（客户）', b: '乙方（我方）' }
  }
  return { a: '甲方（我方）', b: '乙方（供应商）' }
})

// ============================================================
// 表单数据
// ============================================================
interface ServiceContractForm {
  customer_id: string
  name: string
  contract_no: string
  contract_type: ContractType
  party_a_name: string
  party_b_name: string
  amount: number | null
  start_date: string
  end_date: string
  related_contract_id: string | null
  remark: string
  project_name: string
  contract_content: string
  delivery_requirements: string
  process_records: string
  sort_order: number
}

const form = reactive<ServiceContractForm>({
  customer_id: '',
  name: '',
  contract_no: '',
  contract_type: 'sales',
  party_a_name: '',
  party_b_name: '',
  amount: null,
  start_date: '',
  end_date: '',
  related_contract_id: null,
  remark: '',
  project_name: '',
  contract_content: '',
  delivery_requirements: '',
  process_records: '',
  sort_order: 0,
})

// ============================================================
// 客户选项
// ============================================================
const customerOptions = ref<Customer[]>([])

async function loadCustomers() {
  try {
    const res = await getCustomers({ business_type: '算力服务', page: 1, page_size: 100 })
    customerOptions.value = res.items.filter((c) => c.status === 'active')
  } catch {
    ElMessage.warning('客户列表加载失败，请刷新页面重试')
  }
}

// ============================================================
// 关联合同选项
// ============================================================
const relatedContractOptions = ref<ServiceContractItem[]>([])

async function loadRelatedContracts() {
  try {
    const res = await listServiceContracts({ page: 1, page_size: 100 })
    // 编辑模式下排除自身
    relatedContractOptions.value = isEdit.value
      ? res.items.filter((c) => c.id !== contractId.value)
      : res.items
  } catch {
    ElMessage.warning('关联合同列表加载失败')
  }
}

// ============================================================
// 服务行编辑器
// ============================================================
interface ServiceLineForm {
  _key: string // 前端本地唯一 key
  category: string
  item_name: string
  spec_kv: { key: string; value: string }[] // 简易 key-value 编辑
  vcpu_count: number | null
  memory_gb: number | null
  storage_gb: number | null
  unit: string
  quantity: number
  period_months: number
  unit_price: number
  sort_order: number
  manual_total: number | null // null = 自动计算，非 null = 手动覆盖
  gpu_count?: number
  gpu_model?: string
  gpu_memory_gb?: number
  gpu_tops?: number
  service_description?: string
}

let lineKeyCounter = 0
function nextLineKey(): string {
  return `line_${Date.now()}_${++lineKeyCounter}`
}

function emptyLine(sortOrder: number): ServiceLineForm {
  const cat = '算力服务'
  return {
    _key: nextLineKey(),
    category: cat,
    item_name: '',
    spec_kv: [],
    vcpu_count: null,
    memory_gb: null,
    storage_gb: null,
    unit: '个/月',
    quantity: 1,
    period_months: 1,
    unit_price: 0,
    sort_order: sortOrder,
    manual_total: null,
    gpu_count: undefined,
    gpu_model: '',
    gpu_memory_gb: undefined,
    gpu_tops: undefined,
    service_description: '',
  }
}

const serviceLines = ref<ServiceLineForm[]>([])

// 单行总价 = quantity × period_months × unit_price
// 模型调优服务周期固定为 1
function lineTotal(line: ServiceLineForm): number {
  const q = line.quantity || 0
  const p = line.category === '模型调优服务' ? 1 : (line.period_months || 0)
  const u = line.unit_price || 0
  return q * p * u
}

// 自动汇总金额（有手动值则用手动值）
const autoCalcAmount = computed(() => {
  return serviceLines.value.reduce((sum, line) => {
    return sum + (line.manual_total ?? lineTotal(line))
  }, 0)
})

// 金额对比
const amountMismatch = computed(() => {
  if (form.amount === null || form.amount === undefined) return null
  return form.amount - autoCalcAmount.value
})

const amountWarning = computed(() => {
  if (amountMismatch.value === null) return null
  if (Math.abs(amountMismatch.value) < 0.01) return null
  return `合同金额与明细汇总不一致（差额：¥${Math.abs(amountMismatch.value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}）`
})

// 按 category 分组
const groupedLines = computed(() => {
  const groups: { category: string; lines: ServiceLineForm[] }[] = []
  for (const line of serviceLines.value) {
    const last = groups.length > 0 ? groups[groups.length - 1] : null
    if (last && last.category === line.category) {
      last.lines.push(line)
    } else {
      groups.push({ category: line.category, lines: [line] })
    }
  }
  return groups
})

// 分类选项
const categoryOptions = ['算力服务', '算力优化服务', '智能体服务', '模型调优服务']

// 规格 key-value 操作
function addSpecKV(line: ServiceLineForm) {
  line.spec_kv.push({ key: '', value: '' })
}

function removeSpecKV(line: ServiceLineForm, idx: number) {
  if (line.spec_kv.length <= 1) return
  line.spec_kv.splice(idx, 1)
}

// 大类切换：仅设置单位、周期，不清空规格参数
function onCategoryChange(line: ServiceLineForm) {
  // 根据大类设置默认单位和周期
  if (line.category === '模型调优服务') {
    line.unit = '套'
    line.period_months = 1
    line.vcpu_count = null
    line.memory_gb = null
    line.storage_gb = null
  } else if (line.category === '算力优化服务' || line.category === '智能体服务') {
    line.unit = '个/月'
    line.vcpu_count = null
    line.memory_gb = null
    line.storage_gb = null
  } else {
    // 算力服务
    line.unit = '个/月'
  }
}

// 服务行操作
function addLine() {
  const maxOrder = serviceLines.value.reduce((m, l) => Math.max(m, l.sort_order), -1)
  serviceLines.value.push(emptyLine(maxOrder + 1))
}

function removeLine(lineKey: string) {
  const idx = serviceLines.value.findIndex((l) => l._key === lineKey)
  if (idx < 0) return
  serviceLines.value.splice(idx, 1)
}

function moveLine(lineKey: string, direction: 'up' | 'down') {
  const idx = serviceLines.value.findIndex((l) => l._key === lineKey)
  if (idx < 0) return
  if (direction === 'up' && idx > 0) {
    const tmp = serviceLines.value[idx]!
    serviceLines.value[idx] = serviceLines.value[idx - 1]!
    serviceLines.value[idx - 1] = tmp
  } else if (direction === 'down' && idx < serviceLines.value.length - 1) {
    const tmp = serviceLines.value[idx]!
    serviceLines.value[idx] = serviceLines.value[idx + 1]!
    serviceLines.value[idx + 1] = tmp
  }
}

// 构建提交用的 service_lines 数据
function buildServiceLinesPayload(): ServiceLineCreatePayload[] {
  return serviceLines.value.map((line, idx) => {
    const spec: ServiceSpecification = {}
    for (const kv of line.spec_kv) {
      if (kv.key.trim()) {
        spec[kv.key.trim()] = kv.value
      }
    }
    return {
      category: line.category,
      item_name: line.item_name,
      specification: Object.keys(spec).length > 0 ? spec : undefined,
      vcpu_count: line.vcpu_count ?? undefined,
      memory_gb: line.memory_gb ?? undefined,
      storage_gb: line.storage_gb ?? undefined,
      unit: line.unit,
      quantity: line.quantity,
      period_months: line.period_months,
      unit_price: line.unit_price,
      manual_total_price: line.manual_total ?? undefined,
      sort_order: idx,
      service_description: line.service_description || undefined,
      gpu_count: line.gpu_count ?? undefined,
      gpu_model: line.gpu_model || undefined,
      gpu_memory_gb: line.gpu_memory_gb ?? undefined,
      gpu_tops: line.gpu_tops ?? undefined,
    }
  })
}

// 从后端 ServiceLineItem 回填到 ServiceLineForm
function fillLinesFromDetail(lines: ServiceLineItem[]) {
  serviceLines.value = lines.map((item, idx) => {
    // 如果后端有 specification 就用它，否则初始化为空
    const specEntries = item.specification && Object.keys(item.specification).length > 0
      ? Object.entries(item.specification).map(([k, v]) => ({ key: k, value: String(v) }))
      : []
    return {
      _key: nextLineKey(),
      category: item.category,
      item_name: item.item_name,
      spec_kv: specEntries,
      vcpu_count: item.vcpu_count ?? null,
      memory_gb: item.memory_gb ?? null,
      storage_gb: item.storage_gb ?? null,
      unit: item.unit,
      quantity: item.quantity,
      period_months: item.period_months,
      unit_price: item.unit_price,
      sort_order: item.sort_order ?? idx,
      manual_total: null,
      gpu_count: item.gpu_count ?? undefined,
      gpu_model: item.gpu_model ?? '',
      gpu_memory_gb: item.gpu_memory_gb ?? undefined,
      gpu_tops: item.gpu_tops ?? undefined,
      service_description: item.service_description ?? '',
    }
  })
}

// ============================================================
// 加载详情（编辑模式）
// ============================================================
const detail = ref<ServiceContractDetail | null>(null)
const loadingDetail = ref(false)

async function loadDetail() {
  if (!contractId.value) return
  loadingDetail.value = true
  try {
    const data = await getServiceContract(contractId.value)
    detail.value = data
    form.customer_id = data.customer_id
    form.name = data.name
    form.contract_no = data.contract_no ?? ''
    form.contract_type = data.contract_type
    form.party_a_name = data.party_a_name ?? ''
    form.party_b_name = data.party_b_name ?? ''
    form.amount = data.amount ? parseFloat(data.amount) : null
    form.start_date = data.start_date ?? ''
    form.end_date = data.end_date ?? ''
    form.related_contract_id = data.related_contract_id ?? null
    form.remark = data.remark ?? ''
    form.project_name = data.project_name ?? ''
    form.contract_content = data.contract_content ?? ''
    form.delivery_requirements = data.delivery_requirements ?? ''
    form.process_records = data.process_records ?? ''
    form.sort_order = data.sort_order ?? 0
    if (data.service_lines && data.service_lines.length > 0) {
      fillLinesFromDetail(data.service_lines)
    }
  } catch {
    ElMessage.error('合同详情加载失败，请返回重试')
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
  if (!formRef.value) {
    ElMessage.error('表单初始化异常，请刷新页面后重试')
    return
  }
  try {
    await formRef.value.validate()
  } catch (err: any) {
    const firstErrorField = Object.keys(err || {})[0]
    if (firstErrorField) {
      const el = document.querySelector('.el-form-item__error')
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
    return
  }

  submitting.value = true
  try {
    const serviceLinesPayload = buildServiceLinesPayload()

    if (isEdit.value) {
      const payload: ServiceContractUpdatePayload = {
        name: form.name.trim(),
        contract_no: form.contract_no.trim() || undefined,
        contract_type: form.contract_type,
        party_a_name: form.party_a_name.trim() || undefined,
        party_b_name: form.party_b_name.trim() || undefined,
        amount: form.amount,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
        related_contract_id: form.related_contract_id || undefined,
        remark: form.remark.trim() || undefined,
        project_name: form.project_name.trim() || undefined,
        contract_content: form.contract_content.trim() || undefined,
        delivery_requirements: form.delivery_requirements.trim() || undefined,
        process_records: form.process_records.trim() || undefined,
        service_lines: serviceLinesPayload,
        sort_order: form.sort_order,
      }
      await updateServiceContract(contractId.value, payload)
      ElMessage.success('保存成功')
      router.replace({ name: 'ServiceContractDetail', params: { id: contractId.value } })
    } else {
      const payload: ServiceContractCreatePayload = {
        customer_id: form.customer_id,
        name: form.name.trim(),
        contract_no: form.contract_no.trim() || undefined,
        contract_type: form.contract_type,
        party_a_name: form.party_a_name.trim() || undefined,
        party_b_name: form.party_b_name.trim() || undefined,
        amount: form.amount,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
        related_contract_id: form.related_contract_id || undefined,
        remark: form.remark.trim() || undefined,
        project_name: form.project_name.trim() || undefined,
        contract_content: form.contract_content.trim() || undefined,
        delivery_requirements: form.delivery_requirements.trim() || undefined,
        process_records: form.process_records.trim() || undefined,
        service_lines: serviceLinesPayload,
        sort_order: form.sort_order,
      }
      const created = await createServiceContract(payload)
      ElMessage.success('创建成功')
      router.replace({ name: 'ServiceContractDetail', params: { id: created.id } })
    }
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    const message = typeof detail === 'string' ? detail : (err?.message || '提交失败，请稍后重试')
    ElMessage.error(message)
  } finally {
    submitting.value = false
  }
}

function cancel() {
  if (isEdit.value && contractId.value) {
    router.push({ name: 'ServiceContractDetail', params: { id: contractId.value } })
  } else {
    router.push({ name: 'ServiceContractList' })
  }
}

// ============================================================
// 智能解析
// ============================================================
const parsing = ref(false)
const isDragOver = ref(false)
let dragCounter = 0

function onDragEnter(e: DragEvent) {
  e.preventDefault()
  dragCounter++
  if (dragCounter === 1) isDragOver.value = true
}
function onDragLeave(e: DragEvent) {
  e.preventDefault()
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragOver.value = false
  }
}
function onDragOver(e: DragEvent) {
  e.preventDefault()
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  dragCounter = 0
  isDragOver.value = false
}

const handleParseUpload = async (options: any) => {
  // 拖拽完成后立即隐藏遮罩
  isDragOver.value = false
  dragCounter = 0
  const file = options.file as File
  if (!file.name.endsWith('.docx')) {
    ElMessage.warning('仅支持 .docx 格式的 Word 文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 10MB')
    return
  }

  parsing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)

    const res: any = await request.post('/contracts/parse', formData, {
      params: { contract_type: 'compute_service' },
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    const fields = res.fields
    if (!fields) {
      ElMessage.warning('解析返回数据异常，请手动填写')
      return
    }

    // 自动填充表单（只填非 null 字段）
    let filledCount = 0
    const fieldMap: Record<string, keyof ServiceContractForm> = {
      name: 'name',
      contract_no: 'contract_no',
      contract_type: 'contract_type',
      party_a_name: 'party_a_name',
      party_b_name: 'party_b_name',
      amount: 'amount',
      start_date: 'start_date',
      end_date: 'end_date',
      project_name: 'project_name',
      contract_content: 'contract_content',
      delivery_requirements: 'delivery_requirements',
      remark: 'remark',
    }

    for (const [key, value] of Object.entries(fields)) {
      if (value === null || value === undefined) continue
      const mappedKey = fieldMap[key]
      if (!mappedKey) continue

      if (mappedKey === 'amount') {
        // amount 可能是字符串，需要转为数字
        const num = typeof value === 'string' ? parseFloat(value) : Number(value)
        if (!isNaN(num)) {
          form.amount = num
          filledCount++
        }
      } else if (mappedKey === 'contract_type') {
        // 校验 contract_type 是有效值
        if (value === 'sales' || value === 'procurement') {
          form.contract_type = value
          filledCount++
        }
      } else {
        ;(form as any)[mappedKey] = value
        filledCount++
      }
    }

    ElMessage.success(`智能解析完成，已填充 ${filledCount} 个字段，请核对后提交`)
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || err?.response?.data
    const message = typeof detail === 'string' ? detail : '解析失败，请稍后重试'
    ElMessage.error(message)
  } finally {
    parsing.value = false
  }
}

onMounted(async () => {
  document.addEventListener('dragenter', onDragEnter)
  document.addEventListener('dragleave', onDragLeave)
  document.addEventListener('dragover', onDragOver)
  document.addEventListener('drop', onDrop)

  await Promise.all([loadCustomers(), loadRelatedContracts()])
  if (isEdit.value) {
    await loadDetail()
  } else {
    // 新建模式默认给一行空行
    serviceLines.value.push(emptyLine(0))
  }
})

onUnmounted(() => {
  document.removeEventListener('dragenter', onDragEnter)
  document.removeEventListener('dragleave', onDragLeave)
  document.removeEventListener('dragover', onDragOver)
  document.removeEventListener('drop', onDrop)
})
</script>

<template>
  <div class="page-container" v-loading="loadingDetail">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            {{ isEdit ? '编辑算力服务合同' : '新建算力服务合同' }}
          </span>
          <div class="card-header-actions">
            <el-button link @click="cancel">返回</el-button>
          </div>
        </div>
      </template>

      <!-- 拖拽上传区（仅新建模式） -->
      <div v-if="!isEdit" class="parse-drop-zone" :class="{ 'is-dragover': isDragOver }">
        <el-upload
          drag
          :show-file-list="false"
          accept=".docx"
          :http-request="handleParseUpload"
          class="parse-upload"
        >
          <el-icon :size="40" v-if="!parsing"><MagicStick /></el-icon>
          <el-icon :size="40" v-else class="is-loading"><Loading /></el-icon>
          <div class="el-upload__text">
            将 .docx 合同文件<em>拖拽到此处</em>或<em>点击上传</em>
          </div>
          <div class="el-upload__tip">AI 自动识别合同关键字段并填充表单</div>
        </el-upload>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="140px"
        @submit.prevent
      >
        <!-- ============================================ -->
        <!-- 合同基本信息区 -->
        <!-- ============================================ -->
        <div class="section-title">
          <el-icon><Document /></el-icon>
          合同基本信息
        </div>

        <el-form-item label="合同类型" prop="contract_type">
          <el-radio-group v-model="form.contract_type">
            <el-radio-button value="sales">销售</el-radio-button>
            <el-radio-button value="procurement">采购</el-radio-button>
          </el-radio-group>
        </el-form-item>

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

        <el-form-item :label="partyLabels.a" prop="party_a_name">
          <el-input v-model="form.party_a_name" :placeholder="'请输入' + partyLabels.a" maxlength="255" />
        </el-form-item>

        <el-form-item :label="partyLabels.b" prop="party_b_name">
          <el-input v-model="form.party_b_name" :placeholder="'请输入' + partyLabels.b" maxlength="255" />
        </el-form-item>

        <el-form-item label="合同名称" prop="name">
          <el-input v-model="form.name" placeholder="如 算力服务合同-2026" maxlength="255" show-word-limit />
        </el-form-item>

        <el-form-item label="序号">
          <el-input-number v-model="form.sort_order" :min="0" :step="1" placeholder="序号" />
        </el-form-item>

        <el-form-item label="合同编号" prop="contract_no">
          <el-input v-model="form.contract_no" placeholder="可选，如 FW-2026-001" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="所属项目" prop="project_name">
          <el-input v-model="form.project_name" placeholder="可选，如 某项目一期" maxlength="255" show-word-limit />
        </el-form-item>

        <el-form-item label="合同金额">
          <el-input-number
            v-model="form.amount"
            :min="0"
            :precision="2"
            :controls="false"
            placeholder="留空则自动计算"
            style="width: 300px"
          />
          <span class="form-hint">留空则根据服务行自动汇总</span>
        </el-form-item>

        <el-form-item label="开始日期">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            placeholder="选择开始日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>

        <el-form-item label="结束日期">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            placeholder="选择结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>

        <el-form-item label="关联合同">
          <el-select
            v-model="form.related_contract_id"
            placeholder="可选，关联背靠背合同"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="c in relatedContractOptions"
              :key="c.id"
              :label="`${c.name} (${c.contract_no || '无编号'})`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>

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

        <el-divider content-position="left">合同详细内容</el-divider>

        <el-form-item label="合同内容">
          <el-input
            v-model="form.contract_content"
            type="textarea"
            :rows="4"
            placeholder="可选，合同主要内容概述或长文本描述"
            maxlength="5000"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="交付要求">
          <el-input
            v-model="form.delivery_requirements"
            type="textarea"
            :rows="4"
            placeholder="可选，合同交付标准/要求"
            maxlength="5000"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="过程记录">
          <el-input
            v-model="form.process_records"
            type="textarea"
            :rows="4"
            placeholder="可选，合同执行过程中的记录，如问题、变更说明等"
            maxlength="5000"
            show-word-limit
          />
        </el-form-item>

        <!-- ============================================ -->
        <!-- 服务行编辑器 -->
        <!-- ============================================ -->
        <div class="section-title" style="margin-top: 28px;">
          <el-icon><List /></el-icon>
          服务内容明细
        </div>

        <!-- 空状态 -->
        <div v-if="serviceLines.length === 0" class="lines-empty">
          <p>暂未添加服务行，点击下方按钮添加。</p>
        </div>

        <!-- 按 category 分组显示 -->
        <template v-for="group in groupedLines" :key="group.category">
          <div class="line-category-header">
            <span class="line-category-tag">{{ group.category }}</span>
            <span class="line-category-count">{{ group.lines.length }} 项</span>
          </div>

          <div
            v-for="line in group.lines"
            :key="line._key"
            class="line-card"
          >
            <!-- 行操作按钮 -->
            <div class="line-actions">
              <el-button size="small" text @click="moveLine(line._key, 'up')">
                <el-icon><Top /></el-icon>
              </el-button>
              <el-button size="small" text @click="moveLine(line._key, 'down')">
                <el-icon><Bottom /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click="removeLine(line._key)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>

            <!-- 行字段 -->
            <div class="line-fields">
              <div class="line-field">
                <label>服务大类</label>
                <el-select v-model="line.category" style="width: 180px" @change="onCategoryChange(line)">
                  <el-option
                    v-for="cat in categoryOptions"
                    :key="cat"
                    :label="cat"
                    :value="cat"
                  />
                </el-select>
              </div>

              <div class="line-field">
                <label>服务项名称</label>
                <el-input v-model="line.item_name" placeholder="如 通用CPU容器实例" style="width: 220px" />
              </div>

              <!-- 服务描述：所有大类都显示 -->
              <div class="line-field line-field-wide">
                <label>服务描述</label>
                <el-input
                  v-model="line.service_description"
                  type="textarea"
                  :rows="3"
                  placeholder="服务描述，如参数/服务描述详情"
                  maxlength="2000"
                  show-word-limit
                />
              </div>

              <div v-if="line.category === '算力服务'" class="line-field">
                <label>vCPU核数</label>
                <el-input-number v-model="line.vcpu_count" :min="0" :controls="false" style="width: 100px" />
              </div>

              <div v-if="line.category === '算力服务'" class="line-field">
                <label>内存(GB)</label>
                <el-input-number v-model="line.memory_gb" :min="0" :controls="false" style="width: 100px" />
              </div>

              <div v-if="line.category === '算力服务'" class="line-field">
                <label>存储(GB)</label>
                <el-input-number v-model="line.storage_gb" :min="0" :controls="false" style="width: 100px" />
              </div>

              <div class="line-field">
                <label>单位</label>
                <el-input v-model="line.unit" placeholder="如 个/月" style="width: 120px" />
              </div>

              <div class="line-field">
                <label>数量</label>
                <el-input-number v-model="line.quantity" :min="0" :controls="false" style="width: 100px" />
              </div>

              <div v-if="line.category !== '模型调优服务'" class="line-field">
                <label>周期(月)</label>
                <el-input-number v-model="line.period_months" :min="0" :controls="false" style="width: 100px" />
              </div>

              <div v-if="line.category === '模型调优服务'" class="line-field">
                <label>周期</label>
                <span class="line-period-hint">按套（不涉及服务周期）</span>
              </div>

              <div class="line-field">
                <label>单价(元)</label>
                <el-input-number v-model="line.unit_price" :min="0" :precision="2" :controls="false" style="width: 140px" />
              </div>

              <div class="line-field" style="min-width: 180px;">
                <label>总价(元)</label>
                <el-input-number
                  v-model="line.manual_total"
                  :min="0"
                  :precision="2"
                  :controls="false"
                  :placeholder="lineTotal(line).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })"
                  style="width: 180px"
                />
                <span v-if="line.manual_total !== null && line.manual_total !== undefined" class="line-total-hint manual">
                  已手动覆盖（自动值：¥{{ lineTotal(line).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}）
                </span>
                <span v-else class="line-total-hint auto">自动计算（可点击手动修改）</span>
              </div>
            </div>

            <!-- 规格 key-value 编辑器 -->
            <div class="spec-section">
              <label class="spec-label">规格参数</label>
              <div class="spec-kv-list">
                <div v-for="(kv, ki) in line.spec_kv" :key="ki" class="spec-kv-row">
                  <el-input
                    v-model="kv.key"
                    placeholder="key"
                    style="width: 140px"
                    size="small"
                  />
                  <span class="spec-kv-colon">:</span>
                  <el-input
                    v-model="kv.value"
                    placeholder="value"
                    style="width: 180px"
                    size="small"
                  />
                  <el-button
                    v-if="line.spec_kv.length > 1"
                    size="small"
                    text
                    type="danger"
                    @click="removeSpecKV(line, ki)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <el-button size="small" text type="primary" @click="addSpecKV(line)">
                + 添加参数
              </el-button>
            </div>

            <!-- GPU 配置：仅「算力服务」大类显示 -->
            <div v-if="line.category === '算力服务'" class="gpu-section">
              <el-divider content-position="left">GPU 配置（选填）</el-divider>
              <div class="line-fields">
                <div class="line-field">
                  <label class="line-label">GPU卡数</label>
                  <el-input-number v-model="line.gpu_count" :min="0" :step="1" placeholder="每台几张卡" controls-position="right" style="width: 100%" />
                </div>
                <div class="line-field">
                  <label class="line-label">GPU型号</label>
                  <el-input v-model="line.gpu_model" placeholder="如 A100-80G / H800" maxlength="100" />
                </div>
                <div class="line-field">
                  <label class="line-label">单卡显存(GB)</label>
                  <el-input-number v-model="line.gpu_memory_gb" :min="0" :precision="1" placeholder="如 80" controls-position="right" style="width: 100%" />
                </div>
                <div class="line-field">
                  <label class="line-label">单卡算力(TOPS)</label>
                  <el-input-number v-model="line.gpu_tops" :min="0" :precision="0" placeholder="如 989" controls-position="right" style="width: 100%" />
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 新增行按钮 -->
        <div class="add-line-bar">
          <el-button type="dashed" @click="addLine">
            + 添加服务行
          </el-button>
        </div>

        <!-- 自动汇总金额 -->
        <div class="amount-summary">
          <div class="amount-summary-row">
            <span class="amount-summary-label">明细汇总金额：</span>
            <span class="amount-summary-value">
              ¥{{ autoCalcAmount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
          </div>
          <div v-if="form.amount !== null" class="amount-summary-row">
            <span class="amount-summary-label">合同金额：</span>
            <span class="amount-summary-value">
              ¥{{ form.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
          </div>
          <div v-if="amountWarning" class="amount-warning">
            <el-icon><WarningFilled /></el-icon>
            {{ amountWarning }}
          </div>
        </div>
      </el-form>

      <div class="form-actions">
        <el-button @click="cancel">取消</el-button>
        <div class="spacer" />
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </el-card>

    <!-- 全页面拖拽遮罩 -->
    <Teleport to="body">
      <div v-if="isDragOver && !isEdit" class="page-drag-overlay">
        <el-icon class="overlay-icon"><MagicStick /></el-icon>
        <div class="overlay-text">释放文件以智能解析合同</div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.card-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

/* 服务行编辑器 */
.lines-empty {
  text-align: center;
  padding: 24px;
  color: #909399;
}

.line-category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0 8px 0;
  padding: 6px 12px;
  background: #f0f5ff;
  border-radius: 6px;
}
.line-category-tag {
  font-weight: 600;
  font-size: 14px;
  color: #1a73e8;
}
.line-category-count {
  font-size: 12px;
  color: #909399;
}

.line-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  position: relative;
  background: #fcfdff;
}
.line-card:hover {
  border-color: #c0c4cc;
}
.line-actions {
  position: absolute;
  top: 8px;
  right: 12px;
  display: flex;
  gap: 2px;
}

.line-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: center;
  padding-right: 100px;
}
.line-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.line-field-wide {
  flex: 1 1 100%;
  min-width: 200px;
}
.line-field label {
  font-size: 12px;
  color: #909399;
}
.line-total-price {
  font-weight: 700;
  font-size: 15px;
  color: #1a73e8;
  white-space: nowrap;
}
.line-total-hint {
  font-size: 11px;
  margin-top: 2px;
  display: block;
}
.line-total-hint.auto {
  color: #909399;
}
.line-total-hint.manual {
  color: #409eff;
}
.line-period-hint {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

/* 规格编辑器 */
.spec-section {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e4e7ed;
}
.spec-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
  display: block;
}
.spec-kv-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 4px;
}
.spec-kv-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.spec-kv-colon {
  color: #909399;
  font-weight: 600;
}

/* GPU 配置区域 */
.gpu-section {
  margin-top: 12px;
}
.gpu-section .line-fields {
  padding-right: 0;
}

.add-line-bar {
  text-align: center;
  padding: 12px 0;
}

/* 金额汇总 */
.amount-summary {
  margin-top: 20px;
  padding: 16px;
  background: #fafbfc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.amount-summary-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}
.amount-summary-label {
  font-size: 14px;
  color: #606266;
  min-width: 120px;
}
.amount-summary-value {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}
.amount-warning {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef3c7;
  border: 1px solid #f0c94a;
  border-radius: 6px;
  color: #92400e;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
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

/* ============================================
   智能解析拖拽区
   ============================================ */
.parse-drop-zone {
  margin-bottom: 16px;
  transition: opacity 0.2s;
}
.parse-upload :deep(.el-upload-dragger) {
  border: 2px dashed #c0c4cc;
  border-radius: 8px;
  padding: 24px 16px;
  background: #fafafa;
  transition: all 0.3s;
}
.parse-upload :deep(.el-upload-dragger:hover) {
  border-color: #e6a23c;
  background: #fdf6ec;
}
.parse-drop-zone.is-dragover :deep(.el-upload-dragger) {
  border-color: #e6a23c;
  background: #fdf6ec;
  transform: scale(1.02);
}

/* 全页面拖拽遮罩 */
.page-drag-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(230, 162, 60, 0.08);
  border: 3px dashed #e6a23c;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.page-drag-overlay .overlay-icon {
  font-size: 64px;
  color: #e6a23c;
  margin-bottom: 16px;
}
.page-drag-overlay .overlay-text {
  font-size: 24px;
  color: #e6a23c;
  font-weight: 600;
}
</style>
