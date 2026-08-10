<script setup lang="ts">
/**
 * 项目管理合同 - 创建 / 编辑（共用页面）
 *
 * 复用规则：
 *  - 路由 /projects/:company/create → 新建模式
 *  - 路由 /projects/:company/:id/edit → 编辑模式
 *
 * 与算力服务合同 form.vue 差异：
 *  - 没有客户选择（用 company_code 替代，显示当前公司名）
 *  - 关联合同选项来自同公司 project 合同
 *  - 智能解析 contract_type=project，使用 SSE 流式
 */
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Delete, MagicStick, Loading, Document, List, Close, UploadFilled } from '@element-plus/icons-vue'
// 智能解析使用 fetch() 调用 SSE 流，不需要 request 模块
import {
  createProjectContract,
  getProjectContract,
  updateProjectContract,
  listProjectContracts,
  getProjectTypes,
  type ProjectContractCreatePayload,
  type ProjectContractDetail,
  type ProjectContractUpdatePayload,
  type ContractType,
  type ProjectServiceLineCreatePayload,
  type ProjectServiceLine,
  type ProjectSpecification,
  type ProjectContractItem,
  type ProjectTypeResponse,
  COMPANY_MAP,
} from '@/api/modules/project'
import { useGlobalDrop } from '@/composables/useGlobalDrop'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const contractId = computed(() => (route.params.id as string) || '')
const companyCode = computed(() => (route.params.company as string) || 'fengyun')

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
interface ProjectContractForm {
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
  project_type: string
  contract_content: string
  delivery_requirements: string
  process_records: string
  responsible_person: string
  business_person: string
  party_a_contact: string
  party_b_contact: string
  sort_order: number
}

const form = reactive<ProjectContractForm>({
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
  project_type: '',
  contract_content: '',
  delivery_requirements: '',
  process_records: '',
  responsible_person: '',
  business_person: '',
  party_a_contact: '',
  party_b_contact: '',
  sort_order: 0,
})

// ============================================================
// 关联合同选项
// ============================================================
const relatedContractOptions = ref<ProjectContractItem[]>([])

async function loadRelatedContracts() {
  try {
    const res = await listProjectContracts({ company: companyCode.value, page: 1, page_size: 100 })
    // 编辑模式下排除自身
    relatedContractOptions.value = isEdit.value
      ? res.items.filter((c) => c.id !== contractId.value)
      : res.items
  } catch {
    ElMessage.warning('关联合同列表加载失败')
  }
}

// 项目类型下拉选项
const projectTypeOptions = ref<ProjectTypeResponse[]>([])

async function loadProjectTypes() {
  try {
    projectTypeOptions.value = await getProjectTypes()
  } catch {
    // 静默失败，下拉为空
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
  unit: string
  quantity: number
  period_months: number
  unit_price: number
  sort_order: number
  manual_total: number | null // null = 自动计算，非 null = 手动覆盖
  service_description?: string
}

let lineKeyCounter = 0
function nextLineKey(): string {
  return `line_${Date.now()}_${++lineKeyCounter}`
}

function emptyLine(sortOrder: number): ServiceLineForm {
  const cat = '计算资源'
  return {
    _key: nextLineKey(),
    category: cat,
    item_name: '',
    spec_kv: [],
    unit: '台',
    quantity: 1,
    period_months: 1,
    unit_price: 0,
    sort_order: sortOrder,
    manual_total: null,
    service_description: '',
  }
}

const serviceLines = ref<ServiceLineForm[]>([])

// ============================================================
// 智能解析 - 原始表格 & 资源统计
// ============================================================
const rawTables = ref<any[]>([])
const resourceSummary = ref<any>(null)
// 可编辑的 stats（用户可手动修改 Agent 计算值）
const editableStats = reactive<Record<string, number | null>>({
  vcpu: null,
  memory_gb: null,
  storage_gb: null,
  gpu_count: null,
  gpu_tops: null,
})

const STATS_LABELS: Record<string, string> = {
  vcpu: 'vCPU',
  memory_gb: '内存(GB)',
  storage_gb: '存储(GB)',
  gpu_count: 'GPU(卡)',
  gpu_tops: '算力(TOPS)',
}

const STATS_KEYS = ['vcpu', 'memory_gb', 'storage_gb', 'gpu_count', 'gpu_tops']

const statsDisplay = computed(() => {
  return STATS_KEYS
    .filter(k => editableStats[k] !== null && Number(editableStats[k]) > 0)
    .map(k => ({ key: k, label: STATS_LABELS[k], value: editableStats[k] }))
})

function buildRawTablesJson(): string | undefined {
  const data: any = { tables: rawTables.value }
  const stats: Record<string, number> = {}
  for (const key of STATS_KEYS) {
    if (editableStats[key] !== null) stats[key] = editableStats[key] as number
  }
  if (Object.keys(stats).length > 0) data.resource_summary = { stats }
  return rawTables.value.length > 0 ? JSON.stringify(data) : undefined
}

// ============================================================
// 表格单元格编辑 & 行操作
// ============================================================
function updateTableRow(table: any, rowIndex: number, colIndex: number, value: string) {
  if (!table.rows || !Array.isArray(table.rows)) {
    table.rows = []
  }
  if (!table.rows[rowIndex]) {
    table.rows[rowIndex] = {}
  }
  table.rows[rowIndex][colIndex] = value
  // 触发响应式更新
  table.rows = [...table.rows]
}

function addTableRow(table: any) {
  if (!table.rows) table.rows = []
  const newRow: Record<number, string> = {}
  for (let i = 0; i < (table.headers?.length || 1); i++) {
    newRow[i] = ''
  }
  table.rows = [...table.rows, newRow]
}

function deleteTableRow(table: any) {
  if (!table.rows || table.rows.length === 0) return
  table.rows = [...table.rows.slice(0, -1)]
}

function deleteTableRowAt(table: any, rowIndex: number) {
  if (!table.rows) return
  table.rows = [...table.rows.slice(0, rowIndex), ...table.rows.slice(rowIndex + 1)]
}

// 服务行操作（简化版）
// 服务行操作（简化版：仅备注行）
function addLine() {
  serviceLines.value.push(emptyLine(serviceLines.value.length))
}

function removeLine(lineKey: string) {
  const idx = serviceLines.value.findIndex((l) => l._key === lineKey)
  if (idx < 0) return
  serviceLines.value.splice(idx, 1)
}

// 构建提交用的 service_lines 数据
function buildServiceLinesPayload(): ProjectServiceLineCreatePayload[] {
  return serviceLines.value.map((line, idx) => {
    const spec: ProjectSpecification = {}
    for (const kv of line.spec_kv) {
      if (kv.key.trim()) {
        spec[kv.key.trim()] = kv.value
      }
    }
    return {
      category: line.category,
      item_name: line.item_name,
      specification: Object.keys(spec).length > 0 ? spec : undefined,
      unit: line.unit,
      quantity: line.quantity,
      period_months: line.period_months,
      unit_price: line.unit_price,
      manual_total_price: line.manual_total ?? undefined,
      sort_order: idx,
      service_description: line.service_description || undefined,
    }
  })
}

// 从后端 ProjectServiceLine 回填到 ServiceLineForm
function fillLinesFromDetail(lines: ProjectServiceLine[]) {
  serviceLines.value = lines.map((item, idx) => {
    const specEntries = item.specification && Object.keys(item.specification).length > 0
      ? Object.entries(item.specification).map(([k, v]) => ({ key: k, value: String(v) }))
      : []
    return {
      _key: nextLineKey(),
      category: item.category,
      item_name: item.item_name,
      spec_kv: specEntries,
      unit: item.unit,
      quantity: item.quantity,
      period_months: item.period_months,
      unit_price: item.unit_price,
      sort_order: item.sort_order ?? idx,
      manual_total: item.manual_total_price ?? null,
      service_description: item.service_description ?? '',
    }
  })
}

// ============================================================
// 加载详情（编辑模式）
// ============================================================
const detail = ref<ProjectContractDetail | null>(null)
const loadingDetail = ref(false)

async function loadDetail() {
  if (!contractId.value) return
  loadingDetail.value = true
  try {
    const data = await getProjectContract(contractId.value)
    detail.value = data
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
    form.project_type = data.project_type ?? ''
    form.contract_content = data.contract_content ?? ''
    form.delivery_requirements = data.delivery_requirements ?? ''
    form.process_records = data.process_records ?? ''
    form.responsible_person = (data as any).responsible_person ?? ''
    form.business_person = (data as any).business_person ?? ''
    form.party_a_contact = (data as any).party_a_contact ?? ''
    form.party_b_contact = (data as any).party_b_contact ?? ''
    form.sort_order = data.sort_order ?? 0
    if (data.service_lines && data.service_lines.length > 0) {
      fillLinesFromDetail(data.service_lines)
    }
    // 回填 raw_tables（支持 {tables:[], resource_summary:{}} 结构）
    const detailAny = data as any
    if (detailAny.raw_tables_json) {
      try {
        const parsed = JSON.parse(detailAny.raw_tables_json)
        if (Array.isArray(parsed)) {
          rawTables.value = parsed
        } else {
          rawTables.value = parsed.tables || []
          if (parsed.resource_summary?.stats) {
            for (const key of STATS_KEYS) {
              if (parsed.resource_summary.stats[key] !== undefined) {
                editableStats[key] = Number(parsed.resource_summary.stats[key])
              }
            }
          }
        }
      } catch {}
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
  name: [{ required: true, message: '请输入合同名称', trigger: 'blur' }],
  project_type: [{ required: true, message: '请选择项目类型', trigger: 'change' }],
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
    // 滚动到第一个报错字段
    const firstErrorField = Object.keys(err || {})[0]
    if (firstErrorField) {
      const el = document.querySelector(`.el-form-item__error`)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
    return
  }

  submitting.value = true
  try {
    const serviceLinesPayload = buildServiceLinesPayload()

    if (isEdit.value) {
      const payload: ProjectContractUpdatePayload = {
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
        project_type: form.project_type.trim() || undefined,
        contract_content: form.contract_content.trim() || undefined,
        delivery_requirements: form.delivery_requirements.trim() || undefined,
        process_records: form.process_records.trim() || undefined,
        responsible_person: form.responsible_person.trim() || undefined,
        business_person: form.business_person.trim() || undefined,
        party_a_contact: form.party_a_contact.trim() || undefined,
        party_b_contact: form.party_b_contact.trim() || undefined,
        service_lines: serviceLinesPayload,
        raw_tables_json: buildRawTablesJson(),
        sort_order: form.sort_order,
      }
      await updateProjectContract(contractId.value, payload)
      ElMessage.success('保存成功')
      router.replace({ name: 'ProjectDetail', params: { company: companyCode.value, id: contractId.value } })
    } else {
      const payload: ProjectContractCreatePayload = {
        company_code: companyCode.value,
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
        project_type: form.project_type.trim() || undefined,
        contract_content: form.contract_content.trim() || undefined,
        delivery_requirements: form.delivery_requirements.trim() || undefined,
        process_records: form.process_records.trim() || undefined,
        responsible_person: form.responsible_person.trim() || undefined,
        business_person: form.business_person.trim() || undefined,
        party_a_contact: form.party_a_contact.trim() || undefined,
        party_b_contact: form.party_b_contact.trim() || undefined,
        service_lines: serviceLinesPayload,
        raw_tables_json: buildRawTablesJson(),
        sort_order: form.sort_order,
      }
      const created = await createProjectContract(payload)
      ElMessage.success('创建成功')
      router.replace({ name: 'ProjectDetail', params: { company: companyCode.value, id: created.id } })
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
    router.push({ name: 'ProjectDetail', params: { company: companyCode.value, id: contractId.value } })
  } else {
    router.push({ name: 'ProjectList', params: { company: companyCode.value } })
  }
}

// ============================================================
// Copilot 面板
// ============================================================
const copilotOpen = ref(false)
const copilotBodyRef = ref<HTMLElement | null>(null)
interface CopilotMessage { role: 'system' | 'result'; text?: string; image?: string; time?: string; fields?: string[] }
const copilotMessages = ref<CopilotMessage[]>([
  { role: 'system', text: '👋 你好！我是合同解析助手。拖拽或上传合同文件，我将自动提取关键信息。' }
])

async function addCopilotMsg(role: 'system' | 'result', text: string) {
  copilotMessages.value.push({ role, text, time: new Date().toLocaleTimeString() })
  await nextTick()
  if (copilotBodyRef.value) {
    copilotBodyRef.value.scrollTop = copilotBodyRef.value.scrollHeight
  }
}

// ============================================================
// 智能解析
// ============================================================
const parsing = ref(false)

/** 核心解析逻辑：接收 File 对象，执行 SSE 流式解析并填充表单 */
async function parseContractFile(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'docx' && ext !== 'doc' && ext !== 'pdf') {
    ElMessage.warning('仅支持 .doc / .docx / .pdf 格式的文件')
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 50MB')
    return
  }

  copilotOpen.value = true
  copilotMessages.value = []
  parsing.value = true
  addCopilotMsg('system', `📄 收到文件：${file.name}（${(file.size / 1024).toFixed(1)}KB）`)

  try {
    const formData = new FormData()
    formData.append('file', file)

    // SSE 流式读取
    const response = await fetch('/api/contracts/parse/stream?contract_type=project', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errText = await response.text()
      throw new Error(errText || `HTTP ${response.status}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalFields: any = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      // 按 SSE 事件分隔符 \n\n 分割，避免大 JSON 被切断
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''

      for (const event of events) {
        const lines = event.split('\n')
        let eventType = ''
        let dataStr = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            dataStr = line.slice(6)
          }
        }
        if (!dataStr) continue
        
        let data: any
        try { data = JSON.parse(dataStr) } catch { continue }

        if (eventType === 'progress') {
          if (data.step === 'pdf_to_images') {
            addCopilotMsg('system', `📐 PDF 转图片完成：${data.pages} 页，耗时 ${data.seconds} 秒`)
          } else if (data.step === 'ocr_done') {
            addCopilotMsg('system', `📝 文字识别完成：${data.chars} 字符`)
          } else if (data.step === 'extract_done') {
            addCopilotMsg('system', `🔍 信息提取完成（${data.seconds} 秒）`)
          } else if (data.step === 'final_summary') {
            addCopilotMsg('system', `🔍 最终汇总完成（${data.seconds} 秒）`)
          }
        } else if (eventType === 'batch') {
          const pageRange = data.start_page === data.end_page
            ? `第 ${data.start_page} 页`
            : `第 ${data.start_page}-${data.end_page} 页`
          addCopilotMsg('system', `📖 ${pageRange}（${data.batch}/${data.total_batches} 批，${data.seconds}秒）OCR 文字提取`)
          if (data.image_base64) {
            copilotMessages.value.push({
              role: 'result',
              image: data.image_base64,
              time: new Date().toLocaleTimeString(),
            })
          }
        } else if (eventType === 'done') {
          finalFields = { ...data.fields }
        } else if (eventType === 'error') {
          throw new Error(data.message || '解析失败')
        }
      }
    }

    // 最终填充表单
    if (!finalFields) throw new Error('未收到解析结果')
    await fillFormFromFields(finalFields)

  } catch (err: any) {
    const msg = typeof err === 'string' ? err : (err?.message || '解析失败')
    ElMessage.error(msg)
    addCopilotMsg('result', `❌ ${msg}`)
  } finally {
    parsing.value = false
  }
}

// ============================================================
// 从解析结果填充表单（抽离为独立函数）
// ============================================================
async function fillFormFromFields(fields: any) {
  let filledCount = 0

  // OCR 文字：存入 window 全局变量，可在控制台查看
  if (fields._ocr_text) {
    addCopilotMsg('result', `📝 识别全文（${fields._ocr_text.length} 字符）— 在浏览器控制台输入 __ocr_full_text 查看完整内容`)
    ;(window as any).__ocr_full_text = fields._ocr_text
  }

  // 基础字段映射（已删除 vcpu_count 等 7 个硬编码字段）
  const fieldMap: Record<string, keyof ProjectContractForm> = {
    name: 'name',
    contract_no: 'contract_no',
    contract_type: 'contract_type',
    party_a_name: 'party_a_name',
    party_b_name: 'party_b_name',
    amount: 'amount',
    start_date: 'start_date',
    end_date: 'end_date',
    project_name: 'project_name',
    project_type: 'project_type',
    contract_content: 'contract_content',
    delivery_requirements: 'delivery_requirements',
    remark: 'remark',
    responsible_person: 'responsible_person',
    business_person: 'business_person',
    party_a_contact: 'party_a_contact',
    party_b_contact: 'party_b_contact',
  }

  for (const [key, value] of Object.entries(fields)) {
    if (value === null || value === undefined) continue
    const mappedKey = fieldMap[key]
    if (!mappedKey) continue

    if (mappedKey === 'amount') {
      const num = typeof value === 'string' ? parseFloat(value) : Number(value)
      if (!isNaN(num)) {
        form.amount = num
        filledCount++
      }
    } else if (mappedKey === 'contract_type') {
      if (value === 'sales' || value === 'procurement') {
        form.contract_type = value
        filledCount++
      }
    } else {
      ;(form as any)[mappedKey] = value
      filledCount++
    }
  }

  // 服务清单自动填充：specification 直接整体赋值
  if (Array.isArray(fields.service_lines) && fields.service_lines.length > 0) {
    const lines: any[] = []
    for (const sl of fields.service_lines) {
      const spec = sl.specification || null
      lines.push({
        category: sl.category || '',
        item_name: sl.item_name || '',
        specification: spec,
        unit: sl.unit || '台/月',
        quantity: Number(sl.quantity) || 1,
        period_months: Number(sl.period_months) || 12,
        unit_price: Number(sl.unit_price) || 0,
        manual_total_price: null,
        sort_order: lines.length,
        service_description: sl.service_description || '',
      })
    }
    serviceLines.value = lines.map((item: any, idx: number) => {
      const specEntries = item.specification && Object.keys(item.specification).length > 0
        ? Object.entries(item.specification).map(([k, v]: [string, any]) => ({ key: k, value: String(v) }))
        : []
      return {
        _key: nextLineKey(),
        category: item.category,
        item_name: item.item_name,
        spec_kv: specEntries,
        unit: item.unit,
        quantity: item.quantity,
        period_months: item.period_months,
        unit_price: item.unit_price,
        sort_order: item.sort_order ?? idx,
        manual_total: item.manual_total_price ?? null,
        service_description: item.service_description ?? '',
      }
    })
    filledCount++
  }

  // raw_tables - 原始表格数据（展示用）
  if (Array.isArray(fields.raw_tables) && fields.raw_tables.length > 0) {
    rawTables.value = fields.raw_tables
    // 清空旧 service_lines，避免重复展示
    serviceLines.value = []
  }

  // resource_summary - 资源统计（填入可编辑 stats）
  if (fields.resource_summary) {
    resourceSummary.value = fields.resource_summary
    const stats = fields.resource_summary.stats || {}
    for (const key of STATS_KEYS) {
      if (stats[key] !== undefined && stats[key] !== null) {
        editableStats[key] = Number(stats[key])
      }
    }
    if (fields.resource_summary.summary_text) {
      addCopilotMsg('result', `📊 ${fields.resource_summary.summary_text}`)
    }
  }

  // 结果汇总
  const totalSeconds = fields._processing_info?.elapsed_seconds
  addCopilotMsg('result', `✅ 解析完成！总耗时 ${totalSeconds} 秒`)

  let summaryMsg = `已填充 ${filledCount} 个字段`
  if (fields.resource_summary) {
    const rs = fields.resource_summary
    const parts: string[] = []
    if (rs.total_vcpu) parts.push(`vCPU ${rs.total_vcpu}核`)
    if (rs.total_memory_gb) parts.push(`内存 ${rs.total_memory_gb}GB`)
    if (rs.total_storage_gb) parts.push(`存储 ${rs.total_storage_gb}GB`)
    if (rs.total_gpu_count) parts.push(`GPU ${rs.total_gpu_count}卡`)
    if (parts.length > 0) {
      summaryMsg += `，资源：${parts.join(' / ')}`
    }
  }
  summaryMsg += '，请核对后提交'
  addCopilotMsg('result', summaryMsg)
  ElMessage.success(summaryMsg)
}

/** el-upload 的 http-request 回调，包装 parseContractFile */
async function handleParseUpload(options: any) {
  await parseContractFile(options.file as File)
}

/** 全局拖拽上传（仅新建模式生效） */
const { isDragging: isGlobalDragging } = useGlobalDrop({
  accept: ['pdf', 'doc', 'docx'],
  multiple: false,
  onDrop: (files) => {
    // 编辑模式不触发解析
    if (isEdit.value) return
    parseContractFile(files[0])
  },
})

onMounted(async () => {
  await loadRelatedContracts()
  await loadProjectTypes()
  if (isEdit.value) {
    await loadDetail()
  } else {
    // 新建模式默认给一行空行
    serviceLines.value.push(emptyLine(0))
  }
})
</script>

<template>
  <div class="page-container" v-loading="loadingDetail">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            {{ isEdit ? '编辑项目合同' : '新建项目合同' }}
            <span class="company-badge">{{ COMPANY_MAP[companyCode] || companyCode }}</span>
          </span>
          <div class="card-header-actions">
            <el-button link @click="cancel">返回</el-button>
          </div>
        </div>
      </template>

      <!-- 拖拽上传区（仅新建模式） -->
      <div v-if="!isEdit" class="parse-drop-zone" :class="{ 'is-dragover': isGlobalDragging }">
        <el-upload
          drag
          :show-file-list="false"
          accept=".doc,.docx,.pdf"
          :http-request="handleParseUpload"
          class="parse-upload"
        >
          <el-icon :size="40" v-if="!parsing"><MagicStick /></el-icon>
          <el-icon :size="40" v-else class="is-loading"><Loading /></el-icon>
          <div class="el-upload__text">
            将 .doc / .docx / .pdf 文件<em>拖拽到此处</em>或<em>点击上传</em>
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

        <!-- 公司（只读显示） -->
        <el-form-item label="所属公司">
          <el-input
            :model-value="COMPANY_MAP[companyCode] || companyCode"
            disabled
            style="width: 300px"
          />
        </el-form-item>

        <el-form-item label="合同类型" prop="contract_type">
          <el-radio-group v-model="form.contract_type">
            <el-radio-button value="sales">销售</el-radio-button>
            <el-radio-button value="procurement">采购</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="partyLabels.a" prop="party_a_name">
          <el-input v-model="form.party_a_name" :placeholder="'请输入' + partyLabels.a" maxlength="255" />
        </el-form-item>

        <el-form-item :label="partyLabels.b" prop="party_b_name">
          <el-input v-model="form.party_b_name" :placeholder="'请输入' + partyLabels.b" maxlength="255" />
        </el-form-item>

        <el-form-item label="合同名称" prop="name">
          <el-input v-model="form.name" placeholder="如 项目合同-2026" maxlength="255" show-word-limit />
        </el-form-item>

        <el-form-item label="序号">
          <el-input-number v-model="form.sort_order" :min="0" :step="1" placeholder="序号" />
        </el-form-item>

        <el-form-item label="合同编号" prop="contract_no">
          <el-input v-model="form.contract_no" placeholder="可选，如 PRJ-2026-001" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="所属项目" prop="project_name">
          <el-input v-model="form.project_name" placeholder="可选，如 某项目一期" maxlength="255" show-word-limit />
        </el-form-item>

        <el-form-item label="项目类型" prop="project_type">
          <el-select
            v-model="form.project_type"
            placeholder="请选择项目类型"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="pt in projectTypeOptions"
              :key="pt.id"
              :label="pt.name"
              :value="pt.name"
            />
          </el-select>
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

        <el-form-item label="负责人">
          <el-input v-model="form.responsible_person" placeholder="手动填写" style="width: 240px" maxlength="100" />
        </el-form-item>

        <el-form-item label="商务">
          <el-input v-model="form.business_person" placeholder="手动填写" style="width: 240px" maxlength="100" />
        </el-form-item>

        <el-form-item label="甲方委派人">
          <el-input v-model="form.party_a_contact" placeholder="AI 自动提取，可手动修改" style="width: 100%" maxlength="255" />
        </el-form-item>

        <el-form-item label="乙方委派人">
          <el-input v-model="form.party_b_contact" placeholder="AI 自动提取，可手动修改" style="width: 100%" maxlength="255" />
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
        <!-- ============================================ -->
        <!-- 服务内容明细（原始表格 + 统计 + 简要备注） -->
        <!-- ============================================ -->
        <div class="section-title" style="margin-top: 28px;">
          <el-icon><List /></el-icon>
          服务内容明细
        </div>

        <!-- 文档表格展示区（智能解析结果，支持单元格编辑 + 添加/删除行） -->
        <div v-if="rawTables.length > 0" style="margin-bottom: 16px;">
          <div v-for="(table, ti) in rawTables" :key="table.table_index ?? ti" style="margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
              <span v-if="table.title" style="font-weight: 600;">📋 {{ table.title }}</span>
              <span v-else style="font-weight: 600;">📋 表格 {{ ti + 1 }}</span>
              <div style="display: flex; gap: 4px;">
                <el-button size="small" text type="primary" @click="addTableRow(table)">+ 添加行</el-button>
                <el-button
                  size="small"
                  text
                  type="danger"
                  :disabled="!table.rows || table.rows.length === 0"
                  @click="deleteTableRow(table)"
                >- 删除行</el-button>
              </div>
            </div>
            <el-table :data="table.rows" border size="small" max-height="500">
              <el-table-column v-for="(h, hi) in table.headers" :key="hi" :label="h" :prop="String(hi)" min-width="100">
                <template #default="{ row, $index }">
                  <el-input
                    :model-value="row[hi] || ''"
                    @update:model-value="(v: string) => updateTableRow(table, $index, hi, v)"
                    size="small"
                    placeholder="-"
                    :style="{ minWidth: '80px' }"
                    clearable
                  />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" fixed="right">
                <template #default="{ $index }">
                  <el-button size="small" text type="danger" @click="deleteTableRowAt(table, $index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 资源统计面板（可编辑） -->
        <div v-if="statsDisplay.length > 0" style="margin-bottom: 16px; padding: 12px; background: #f5f7fa; border-radius: 6px;">
          <div style="font-weight: 600; margin-bottom: 8px;">📊 交付资源统计（可手动调整）</div>
          <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
            <div v-for="s in statsDisplay" :key="s.key" style="display: flex; gap: 6px; align-items: center;">
              <span style="color: #909399; white-space: nowrap;">{{ s.label }}：</span>
              <el-input-number
                :model-value="editableStats[s.key]"
                @update:model-value="(v: number | undefined) => { editableStats[s.key] = v ?? null }"
                :min="0"
                :step="1"
                size="small"
                controls-position="right"
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <!-- 服务备注（手动补充） -->
        <div v-if="serviceLines.length > 0 || rawTables.length === 0" style="margin-bottom: 16px;">
          <div v-for="(line, idx) in serviceLines" :key="line._key || idx" style="display: flex; gap: 8px; align-items: flex-start; margin-bottom: 8px;">
            <el-input v-model="line.item_name" placeholder="服务项名称" style="width: 200px;" size="small" />
            <el-input v-model="line.service_description" placeholder="简要描述" style="flex: 1;" size="small" />
            <el-button size="small" text type="danger" @click="removeLine(line._key)"><el-icon><Delete /></el-icon></el-button>
          </div>
          <el-button size="small" text type="primary" @click="addLine" style="margin-top: 4px;">+ 添加备注行</el-button>
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

    <!-- 全页面拖拽遮罩（新建模式 + 全局拖拽） -->
    <Teleport to="body">
      <div v-if="isGlobalDragging && !isEdit" class="global-drop-overlay">
        <div class="global-drop-box">
          <el-icon :size="48"><UploadFilled /></el-icon>
          <p>释放文件以开始智能解析</p>
        </div>
      </div>
    </Teleport>

    <!-- Copilot 助手面板 -->
    <Teleport to="body">
      <div class="copilot-wrapper" :class="{ open: copilotOpen }">
        <div class="copilot-toggle" @click="copilotOpen = !copilotOpen">
          <el-icon :size="22"><MagicStick /></el-icon>
          <span v-if="!copilotOpen" class="toggle-label">AI 助手</span>
        </div>
        <div class="copilot-panel">
          <div class="copilot-header">
            <span>🤖 合同解析助手</span>
            <el-button link @click="copilotOpen = false">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <div class="copilot-body" ref="copilotBodyRef">
            <div v-for="(msg, i) in copilotMessages" :key="i" class="copilot-msg" :class="`msg-${msg.role}`">
              <div class="msg-bubble">
                <img v-if="msg.image" :src="'data:image/jpeg;base64,' + msg.image" 
                     style="max-width: 200px; border-radius: 4px; margin-bottom: 4px;" />
                <span v-if="msg.text">{{ msg.text }}</span>
              </div>
              <div class="msg-time" v-if="msg.time">{{ msg.time }}</div>
            </div>
            <div v-if="parsing" class="copilot-msg msg-system">
              <div class="msg-bubble thinking">
                <span class="dot-pulse"></span> AI 正在分析合同内容...
              </div>
            </div>
          </div>
        </div>
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
.company-badge {
  display: inline-block;
  margin-left: 10px;
  padding: 2px 10px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
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

/* 全局拖拽遮罩 */
.global-drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}
.global-drop-box {
  background: #fff;
  border: 3px dashed #409eff;
  border-radius: 12px;
  padding: 48px 64px;
  text-align: center;
  color: #409eff;
  font-size: 16px;
}

/* ============================================
   Copilot 助手面板
   ============================================ */
.copilot-wrapper {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 9998;
  display: flex;
  align-items: stretch;
}
.copilot-toggle {
  width: 36px;
  background: linear-gradient(180deg, #1a3270, #1a5cb0);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 8px 0 0 8px;
  writing-mode: vertical-lr;
  font-size: 13px;
  letter-spacing: 2px;
  padding: 12px 6px;
  gap: 6px;
  transition: all 0.3s;
  user-select: none;
}
.copilot-toggle:hover {
  background: linear-gradient(180deg, #1e3a7a, #2068c0);
}
.copilot-toggle .toggle-label {
  writing-mode: vertical-lr;
}
.copilot-panel {
  width: 0;
  overflow: hidden;
  transition: width 0.3s ease;
  background: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: -2px 0 12px rgba(0,0,0,0.1);
}
.copilot-wrapper.open .copilot-panel {
  width: 360px;
}
.copilot-header {
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
}
.copilot-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 500px;
}
.copilot-msg {
  display: flex;
  flex-direction: column;
  max-width: 90%;
}
.msg-system {
  align-self: flex-start;
}
.msg-result {
  align-self: flex-start;
}
.msg-system .msg-bubble {
  background: #f0f2f5;
  color: #303133;
  border-radius: 4px 12px 12px 12px;
}
.msg-result .msg-bubble {
  background: #ecf5ff;
  color: #1a3270;
  border-radius: 4px 12px 12px 12px;
}
.msg-bubble {
  padding: 8px 14px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
.msg-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
  padding-left: 4px;
}
.msg-bubble.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dot-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1a5cb0;
  animation: dotPulse 1.2s infinite ease-in-out;
}
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}
</style>
