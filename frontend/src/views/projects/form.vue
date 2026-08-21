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
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Delete, Document, InfoFilled, MagicStick, Loading, Close, UploadFilled } from '@element-plus/icons-vue'
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
const copilotFabRef = ref<HTMLElement | null>(null)
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
// Copilot 悬浮球拖拽
// ============================================================
const FAB_BALL = 56
const FAB_W = 118
const FAB_H = 48
const FAB_MARGIN = 8
const fabPos = reactive({ right: 24, bottom: 24 })
const viewport = reactive({ w: typeof window !== 'undefined' ? window.innerWidth : 1280, h: typeof window !== 'undefined' ? window.innerHeight : 800 })
const fabDragging = ref(false)
let fabDragMoved = false
let fabStartX = 0
let fabStartY = 0
let fabOriginRight = 24
let fabOriginBottom = 24
let fabActivePointerId: number | null = null

const fabStyle = computed(() => ({
  right: `${fabPos.right}px`,
  bottom: `${fabPos.bottom}px`,
}))

/** 根据悬浮球位置决定卡片展开方向：偏左则向右开，偏下则向上开 */
const fabPlacement = computed(() => {
  const w = copilotOpen.value ? FAB_BALL : FAB_W
  const h = FAB_H
  const cx = viewport.w - fabPos.right - w / 2
  const cy = viewport.h - fabPos.bottom - h / 2
  return {
    openRight: cx < viewport.w / 2,
    openAbove: cy >= viewport.h / 2,
  }
})

function clampFabInset(right: number, bottom: number) {
  const w = copilotOpen.value ? FAB_BALL : FAB_W
  const h = FAB_H
  const maxRight = Math.max(FAB_MARGIN, viewport.w - w - FAB_MARGIN)
  const maxBottom = Math.max(FAB_MARGIN, viewport.h - h - FAB_MARGIN)
  return {
    right: Math.min(Math.max(FAB_MARGIN, right), maxRight),
    bottom: Math.min(Math.max(FAB_MARGIN, bottom), maxBottom),
  }
}

function onFabPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  const fab = copilotFabRef.value
  if (!fab) return
  const rect = fab.getBoundingClientRect()
  fabStartX = e.clientX
  fabStartY = e.clientY
  fabOriginRight = window.innerWidth - rect.right
  fabOriginBottom = window.innerHeight - rect.bottom
  fabPos.right = fabOriginRight
  fabPos.bottom = fabOriginBottom
  fabDragMoved = false
  fabDragging.value = true
  fabActivePointerId = e.pointerId
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  e.preventDefault()
}

function onFabPointerMove(e: PointerEvent) {
  if (!fabDragging.value || e.pointerId !== fabActivePointerId) return
  const dx = e.clientX - fabStartX
  const dy = e.clientY - fabStartY
  if (Math.abs(dx) > 4 || Math.abs(dy) > 4) fabDragMoved = true
  const next = clampFabInset(fabOriginRight - dx, fabOriginBottom - dy)
  fabPos.right = next.right
  fabPos.bottom = next.bottom
}

function onFabPointerUp(e: PointerEvent) {
  if (!fabDragging.value || e.pointerId !== fabActivePointerId) return
  fabDragging.value = false
  fabActivePointerId = null
  try {
    ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
  } catch {
    /* ignore */
  }
  if (!fabDragMoved) {
    copilotOpen.value = !copilotOpen.value
  }
}

function onFabWindowResize() {
  viewport.w = window.innerWidth
  viewport.h = window.innerHeight
  const next = clampFabInset(fabPos.right, fabPos.bottom)
  fabPos.right = next.right
  fabPos.bottom = next.bottom
}

watch(copilotOpen, async () => {
  await nextTick()
  onFabWindowResize()
})

onUnmounted(() => {
  window.removeEventListener('resize', onFabWindowResize)
})

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
  window.addEventListener('resize', onFabWindowResize)
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
    <div class="top-bar">
      <el-button @click="cancel">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><Document /></el-icon>
          {{ isEdit ? '编辑项目合同' : '新建项目合同' }}
          <span class="company-badge">{{ COMPANY_MAP[companyCode] || companyCode }}</span>
        </span>
      </div>

      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>
          <template v-if="isEdit">
            可更新合同信息与服务明细；所属公司不可修改。新建后可在详情页管理附件与回款。
          </template>
          <template v-else>
            填写合同基础信息与服务内容明细；支持拖拽 Word/PDF 合同智能填充，创建后可在详情页管理附件。
          </template>
        </span>
      </div>

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
        label-position="top"
        class="contract-form"
        @submit.prevent
      >
        <!-- 基础信息 -->
        <div class="dialog-section">
          <div class="dialog-section-title">基础信息</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="所属公司">
                <el-input
                  :model-value="COMPANY_MAP[companyCode] || companyCode"
                  disabled
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="合同类型" prop="contract_type">
                <el-radio-group v-model="form.contract_type">
                  <el-radio-button value="sales">销售</el-radio-button>
                  <el-radio-button value="procurement">采购</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item :label="partyLabels.a" prop="party_a_name">
                <el-input v-model="form.party_a_name" :placeholder="'请输入' + partyLabels.a" maxlength="255" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item :label="partyLabels.b" prop="party_b_name">
                <el-input v-model="form.party_b_name" :placeholder="'请输入' + partyLabels.b" maxlength="255" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="合同名称" prop="name">
                <el-input v-model="form.name" placeholder="如 项目合同-2026" maxlength="255" show-word-limit />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="序号">
                <el-input-number v-model="form.sort_order" :min="0" :step="1" placeholder="序号" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="合同编号" prop="contract_no">
                <el-input v-model="form.contract_no" placeholder="可选，如 PRJ-2026-001" maxlength="100" show-word-limit />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="所属项目" prop="project_name">
                <el-input v-model="form.project_name" placeholder="可选，如 某项目一期" maxlength="255" show-word-limit />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
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
            </el-col>
            <el-col :xs="24" :sm="12">
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
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="负责人">
                <el-input v-model="form.responsible_person" placeholder="手动填写" maxlength="100" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="商务">
                <el-input v-model="form.business_person" placeholder="手动填写" maxlength="100" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="甲方委派人">
                <el-input v-model="form.party_a_contact" placeholder="AI 自动提取，可手动修改" maxlength="255" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="乙方委派人">
                <el-input v-model="form.party_b_contact" placeholder="AI 自动提取，可手动修改" maxlength="255" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 日期与金额 -->
        <div class="dialog-section">
          <div class="dialog-section-title">日期与金额</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="form.start_date"
                  type="date"
                  placeholder="选择开始日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="form.end_date"
                  type="date"
                  placeholder="选择结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="合同金额">
                <el-input-number
                  v-model="form.amount"
                  :min="0"
                  :precision="2"
                  :controls="false"
                  placeholder="留空则自动计算"
                  style="width: 100%"
                />
                <div class="form-hint">留空则根据服务行自动汇总</div>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 合同内容与要求 -->
        <div class="dialog-section">
          <div class="dialog-section-title">合同内容与要求</div>
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
        </div>

        <!-- 备注 -->
        <div class="dialog-section">
          <div class="dialog-section-title">备注</div>
          <el-form-item>
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="3"
              placeholder="可选"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </div>

        <!-- 服务内容明细 -->
        <div class="dialog-section">
          <div class="dialog-section-title">服务内容明细</div>

          <!-- 文档表格展示区（智能解析结果，支持单元格编辑 + 添加/删除行） -->
          <div v-if="rawTables.length > 0" class="raw-tables">
            <div v-for="(table, ti) in rawTables" :key="table.table_index ?? ti" class="raw-table-block">
              <div class="raw-table-header">
                <span class="raw-table-title">{{ table.title || `表格 ${ti + 1}` }}</span>
                <div class="raw-table-actions">
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
              <el-table :data="table.rows" stripe size="small" max-height="500" class="raw-edit-table">
                <el-table-column v-for="(h, hi) in table.headers" :key="hi" :label="h" :prop="String(hi)" min-width="120">
                  <template #default="{ row, $index }">
                    <el-input
                      :model-value="row[hi] || ''"
                      @update:model-value="(v: string) => updateTableRow(table, $index, hi, v)"
                      placeholder="-"
                      clearable
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="72" fixed="right" align="center">
                  <template #default="{ $index }">
                    <el-button text type="danger" @click="deleteTableRowAt(table, $index)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- 资源统计面板（可编辑） -->
          <div v-if="statsDisplay.length > 0" class="stats-panel">
            <div class="stats-panel-title">交付资源统计（可手动调整）</div>
            <div class="stats-panel-body">
              <div v-for="s in statsDisplay" :key="s.key" class="stats-item">
                <span class="stats-label">{{ s.label }}：</span>
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
          <div v-if="serviceLines.length > 0 || rawTables.length === 0" class="service-notes">
            <div class="service-notes-header">
              <div class="service-notes-title">服务备注</div>
              <div class="service-notes-hint">可手动补充服务项名称与简要描述</div>
            </div>

            <div v-if="serviceLines.length === 0" class="service-notes-empty">
              暂无备注行，点击下方按钮添加。
            </div>

            <div
              v-for="(line, idx) in serviceLines"
              :key="line._key || idx"
              class="service-note-card"
            >
              <el-input
                v-model="line.item_name"
                placeholder="服务项名称"
                class="service-note-name"
              />
              <el-input
                v-model="line.service_description"
                placeholder="简要描述"
                class="service-note-desc"
              />
              <el-button text type="danger" class="service-note-remove" @click="removeLine(line._key)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>

            <div class="service-notes-actions">
              <el-button size="small" @click="addLine">+ 添加备注行</el-button>
            </div>
          </div>
        </div>
      </el-form>

      <div class="form-actions">
        <el-button @click="cancel">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </div>

    <!-- 全页面拖拽遮罩（新建模式 + 全局拖拽） -->
    <Teleport to="body">
      <div v-if="isGlobalDragging && !isEdit" class="global-drop-overlay">
        <div class="global-drop-box">
          <el-icon :size="48"><UploadFilled /></el-icon>
          <p>释放文件以开始智能解析</p>
        </div>
      </div>
    </Teleport>

    <!-- Copilot 助手：右下角悬浮球 + 气泡卡片（可拖拽） -->
    <Teleport to="body">
      <div
        ref="copilotFabRef"
        class="copilot-fab"
        :class="{
          dragging: fabDragging,
          'place-right': fabPlacement.openRight,
          'place-left': !fabPlacement.openRight,
          'place-above': fabPlacement.openAbove,
          'place-below': !fabPlacement.openAbove,
        }"
        :style="fabStyle"
      >
        <button
          type="button"
          class="copilot-ball"
          :class="{ active: copilotOpen, parsing }"
          :aria-expanded="copilotOpen"
          :aria-label="copilotOpen ? '关闭 AI 助手' : '打开 AI 助手'"
          title="AI 助手"
          @pointerdown="onFabPointerDown"
          @pointermove="onFabPointerMove"
          @pointerup="onFabPointerUp"
          @pointercancel="onFabPointerUp"
        >
          <template v-if="copilotOpen">
            <el-icon :size="20"><Close /></el-icon>
          </template>
          <template v-else>
            <span class="copilot-ball-icon-wrap">
              <el-icon :size="18"><MagicStick /></el-icon>
            </span>
            <span class="copilot-ball-label">AI 助手</span>
          </template>
          <span v-if="parsing && !copilotOpen" class="copilot-ball-dot" />
        </button>

        <Transition name="copilot-pop">
          <div v-if="copilotOpen" class="copilot-card">
            <div class="copilot-header">
              <div class="copilot-header-title">
                <el-icon class="copilot-header-icon"><MagicStick /></el-icon>
                <div class="copilot-header-text">
                  <span class="copilot-header-name">合同解析助手</span>
                  <span class="copilot-header-sub">上传合同后自动提取关键信息</span>
                </div>
              </div>
              <el-button link class="copilot-close" @click="copilotOpen = false">
                <el-icon :size="16"><Close /></el-icon>
              </el-button>
            </div>
            <div class="copilot-body" ref="copilotBodyRef">
              <div
                v-for="(msg, i) in copilotMessages"
                :key="i"
                class="copilot-msg"
                :class="`msg-${msg.role}`"
              >
                <div class="msg-role">{{ msg.role === 'result' ? '解析结果' : '助手' }}</div>
                <div class="msg-bubble">
                  <img
                    v-if="msg.image"
                    :src="'data:image/jpeg;base64,' + msg.image"
                    class="msg-image"
                  />
                  <span v-if="msg.text">{{ msg.text }}</span>
                </div>
                <div v-if="msg.time" class="msg-time">{{ msg.time }}</div>
              </div>
              <div v-if="parsing" class="copilot-msg msg-system">
                <div class="msg-role">助手</div>
                <div class="msg-bubble thinking">
                  <span class="dot-pulse" />
                  <span>AI 正在分析合同内容...</span>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.top-bar {
  margin-bottom: 0;
}
.company-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 10px;
  background: rgba(37, 99, 235, 0.08);
  color: var(--primary-color);
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}
.contract-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
}
.contract-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
.form-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.raw-tables {
  margin-bottom: 16px;
}
.raw-table-block {
  margin-bottom: 16px;
}
.raw-table-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.raw-table-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
}
.raw-table-actions {
  display: flex;
  gap: 4px;
}
.raw-edit-table :deep(.el-table__cell) {
  padding: 8px 8px;
  vertical-align: middle;
}
.raw-edit-table :deep(.el-input__wrapper) {
  background-color: #fff;
  box-shadow: 0 0 0 1px #e5e7eb inset;
}
.raw-edit-table :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #cbd5e1 inset;
}
.raw-edit-table :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) inset;
}

.stats-panel {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.stats-panel-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 10px;
}
.stats-panel-body {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.stats-item {
  display: flex;
  gap: 6px;
  align-items: center;
}
.stats-label {
  color: var(--text-secondary);
  white-space: nowrap;
  font-size: 13px;
}

.service-notes {
  margin-top: 4px;
  margin-bottom: 8px;
}
.service-notes-header {
  margin-bottom: 10px;
}
.service-notes-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}
.service-notes-hint {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-secondary);
}
.service-notes-empty {
  text-align: center;
  padding: 20px 16px;
  margin-bottom: 10px;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
}
.service-note-card {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.service-note-name {
  width: 200px;
  flex-shrink: 0;
}
.service-note-desc {
  flex: 1;
}
.service-note-card :deep(.el-input__wrapper) {
  background-color: #fff;
  box-shadow: 0 0 0 1px #e5e7eb inset;
}
.service-note-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #cbd5e1 inset;
}
.service-note-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) inset;
}
.service-note-remove {
  margin-top: 4px;
  flex-shrink: 0;
}
.service-notes-actions {
  margin-top: 4px;
}

/* 智能解析拖拽区 */
.parse-drop-zone {
  margin-bottom: 16px;
  transition: opacity 0.2s;
}
.parse-upload :deep(.el-upload-dragger) {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 24px 16px;
  background: #f8fafc;
  transition: all 0.3s;
}
.parse-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background: rgba(37, 99, 235, 0.04);
}
.parse-drop-zone.is-dragover :deep(.el-upload-dragger) {
  border-color: var(--primary-color);
  background: rgba(37, 99, 235, 0.06);
}

/* 全局拖拽遮罩 */
.global-drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}
.global-drop-box {
  background: #fff;
  border: 2px dashed var(--primary-color);
  border-radius: 12px;
  padding: 48px 64px;
  text-align: center;
  color: var(--primary-color);
  font-size: 16px;
}

/* Copilot：悬浮球锚点 + 卡片按方位展开 */
.copilot-fab {
  position: fixed;
  z-index: 9998;
  width: auto;
  height: auto;
}
.copilot-fab.dragging {
  user-select: none;
}
.copilot-ball {
  position: relative;
  z-index: 2;
  height: 48px;
  min-width: 48px;
  padding: 0 14px 0 8px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: var(--primary-color);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: grab;
  touch-action: none;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.38), 0 0 0 1px rgba(37, 99, 235, 0.12);
  transition: background 0.2s, transform 0.2s, box-shadow 0.2s, padding 0.2s, border-radius 0.2s;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.copilot-ball-icon-wrap {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.copilot-ball-label {
  padding-right: 2px;
  line-height: 1;
}
.copilot-ball:hover {
  background: var(--primary-hover);
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.45), 0 0 0 1px rgba(37, 99, 235, 0.16);
}
.copilot-fab.dragging .copilot-ball,
.copilot-fab.dragging .copilot-ball:hover {
  cursor: grabbing;
  transform: none;
  transition: background 0.2s;
}
.copilot-ball.active {
  width: 48px;
  padding: 0;
  border-radius: 50%;
  background: #334155;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);
}
.copilot-ball.parsing:not(.active) {
  animation: ballPulse 1.6s ease-in-out infinite;
}
.copilot-ball-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #f59e0b;
  border: 2px solid #fff;
}
.copilot-card {
  position: absolute;
  z-index: 1;
  width: min(380px, calc(100vw - 32px));
  height: min(520px, calc(100vh - 120px));
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.16);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 球在右侧 → 卡片向左；球在左侧 → 卡片向右 */
.copilot-fab.place-left.place-above .copilot-card {
  right: 0;
  bottom: calc(48px + 12px);
  transform-origin: bottom right;
}
.copilot-fab.place-right.place-above .copilot-card {
  left: 0;
  bottom: calc(48px + 12px);
  transform-origin: bottom left;
}
.copilot-fab.place-left.place-below .copilot-card {
  right: 0;
  top: calc(48px + 12px);
  transform-origin: top right;
}
.copilot-fab.place-right.place-below .copilot-card {
  left: 0;
  top: calc(48px + 12px);
  transform-origin: top left;
}
.copilot-header {
  flex-shrink: 0;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  background: #f8fafc;
}
.copilot-header-title {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.copilot-header-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.1);
  color: var(--primary-color);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;
}
.copilot-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.copilot-header-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.3;
}
.copilot-header-sub {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 400;
  line-height: 1.3;
}
.copilot-close {
  color: var(--text-secondary) !important;
  padding: 4px !important;
  margin-top: -2px;
}
.copilot-close:hover {
  color: var(--text-primary) !important;
}
.copilot-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fff;
  min-height: 0;
}
.copilot-msg {
  display: flex;
  flex-direction: column;
  max-width: 100%;
  gap: 4px;
}
.msg-system,
.msg-result {
  align-self: stretch;
}
.msg-role {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  padding-left: 2px;
}
.msg-system .msg-bubble {
  background: #f1f5f9;
  color: var(--text-primary);
  border: 1px solid #e2e8f0;
  border-radius: 2px 10px 10px 10px;
}
.msg-result .msg-bubble {
  background: rgba(37, 99, 235, 0.06);
  color: var(--text-primary);
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 2px 10px 10px 10px;
}
.msg-bubble {
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-image {
  display: block;
  max-width: 100%;
  border-radius: 6px;
  margin-bottom: 6px;
  border: 1px solid #e5e7eb;
}
.msg-time {
  font-size: 11px;
  color: #94a3b8;
  padding-left: 2px;
  font-variant-numeric: tabular-nums;
}
.msg-bubble.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}
.dot-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary-color);
  flex-shrink: 0;
  animation: dotPulse 1.2s infinite ease-in-out;
}
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}
@keyframes ballPulse {
  0%, 100% { box-shadow: 0 8px 24px rgba(37, 99, 235, 0.35); }
  50% { box-shadow: 0 8px 28px rgba(37, 99, 235, 0.55), 0 0 0 8px rgba(37, 99, 235, 0.12); }
}
.copilot-pop-enter-active,
.copilot-pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.copilot-pop-enter-from,
.copilot-pop-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.96);
}

@media (max-width: 640px) {
  .service-note-card {
    flex-wrap: wrap;
  }
  .service-note-name {
    width: 100%;
  }
}
</style>
