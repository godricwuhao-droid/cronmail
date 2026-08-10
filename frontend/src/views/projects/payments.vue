<script setup lang="ts">
/**
 * 回款管理 - 独立页面（重写版 v2）
 *
 * 功能：
 *  - 合同回款汇总卡片（合同金额 / 已回款 / 进度条）
 *  - 回款列表：日期 | 金额 | 回执单 | 发票 | 备注 | 操作
 *  - 新增回款 → 弹窗上传回执单 + 发票 → AI 双文件匹配解析
 *  - 匹配失败 → 金额确认弹窗
 *  - 附件预览弹窗（PDF / 图片 / 其他）
 *  - Copilot AI 助手面板（右侧抽屉）
 *  - 全局拖拽触发 AI 识别
 */
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  UploadFilled,
  MagicStick,
  Close,
  Plus,
  Download,
  View,
  Document,
} from '@element-plus/icons-vue'
import {
  getProjectContract,
  getPayments,
  getPaymentSummary,
  createPayment,
  updatePayment,
  deletePayment,
  parsePaymentFiles,
  confirmPaymentParse,
  type ProjectContractDetail,
  type PaymentRecord,
  type PaymentSummary,
  type ParseResult,
} from '@/api/modules/project'
import { getDownloadUrl } from '@/api/modules/attachment'
import { useGlobalDrop } from '@/composables/useGlobalDrop'

// 文件预览相关依赖
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
GlobalWorkerOptions.workerSrc = pdfjsWorker

const route = useRoute()
const router = useRouter()

// ============================================================
// 合同信息
// ============================================================
const contractId = computed(() => route.params.id as string)
const company = computed(() => route.params.company as string)
const contract = ref<ProjectContractDetail | null>(null)

async function fetchContract() {
  try {
    contract.value = await getProjectContract(contractId.value)
  } catch {
    ElMessage.error('获取合同信息失败')
  }
}

// ============================================================
// 回款汇总
// ============================================================
const paymentSummary = ref<PaymentSummary>({
  total_paid: '0.00',
  contract_amount: '0.00',
  progress: 0,
})

async function fetchSummary() {
  try {
    paymentSummary.value = await getPaymentSummary(contractId.value)
  } catch {
    // ignore
  }
}

// ============================================================
// 回款列表
// ============================================================
const paymentList = ref<PaymentRecord[]>([])

async function fetchPayments() {
  try {
    paymentList.value = await getPayments(contractId.value)
  } catch {
    // ignore
  }
}

async function refreshAll() {
  await Promise.all([fetchPayments(), fetchSummary()])
}

// ============================================================
// 新增/编辑回款弹窗（手动模式）
// ============================================================
const paymentFormVisible = ref(false)
const editingPayment = ref<PaymentRecord | null>(null)
const paymentForm = reactive({
  amount: 0,
  payment_date: '',
  remark: '',
})

function showAddPaymentForm() {
  editingPayment.value = null
  paymentForm.amount = 0
  paymentForm.payment_date = ''
  paymentForm.remark = ''
  // 同时重置 AI 上传状态
  pendingReceipt.value = null
  pendingInvoice.value = null
  parsingReceipt.value = false
  parsingInvoice.value = false
  paymentFormVisible.value = true
}

function editPayment(row: PaymentRecord) {
  editingPayment.value = row
  paymentForm.amount = Number(row.amount)
  paymentForm.payment_date = row.payment_date || ''
  paymentForm.remark = row.remark || ''
  paymentFormVisible.value = true
}

async function submitPayment() {
  try {
    if (editingPayment.value) {
      await updatePayment(editingPayment.value.id, {
        amount: paymentForm.amount,
        payment_date: paymentForm.payment_date || undefined,
        remark: paymentForm.remark || undefined,
      })
      ElMessage.success('回款已更新')
    } else {
      await createPayment(contractId.value, {
        amount: paymentForm.amount,
        payment_date: paymentForm.payment_date || undefined,
        remark: paymentForm.remark || undefined,
      })
      ElMessage.success('回款已添加')
    }
    paymentFormVisible.value = false
    await refreshAll()
  } catch {
    // 错误已统一处理
  }
}

async function handleDeletePayment(id: string) {
  try {
    await deletePayment(id)
    ElMessage.success('回款已删除')
    await refreshAll()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// AI 识别上传 + Copilot 面板
// ============================================================

// --- Copilot 面板 ---
const copilotOpen = ref(false)
const copilotBodyRef = ref<HTMLElement | null>(null)

interface CopilotMessage {
  role: 'system' | 'result'
  text?: string
  time?: string
}
const copilotMessages = ref<CopilotMessage[]>([
  {
    role: 'system',
    text: '👋 你好！我是回款解析助手。上传回执单和发票文件，我将自动提取金额和日期信息。',
  },
])

async function addCopilotMsg(role: 'system' | 'result', text: string) {
  copilotMessages.value.push({ role, text, time: new Date().toLocaleTimeString() })
  await nextTick()
  if (copilotBodyRef.value) {
    copilotBodyRef.value.scrollTop = copilotBodyRef.value.scrollHeight
  }
}

// --- AI 识别状态 ---
const parsingReceipt = ref(false)
const parsingInvoice = ref(false)
const pendingReceipt = ref<File | null>(null)
const pendingInvoice = ref<File | null>(null)
const parsing = ref(false) // 综合解析中状态

// --- 拖拽区域状态 ---
const dragOverZone = ref<'receipt' | 'invoice' | null>(null)
const receiptInputRef = ref<HTMLInputElement | null>(null)
const invoiceInputRef = ref<HTMLInputElement | null>(null)

/** 文件大小格式化 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** 点击拖拽区触发文件选择 */
function triggerFileInput(type: 'receipt' | 'invoice') {
  if (type === 'receipt' && receiptInputRef.value) {
    receiptInputRef.value.click()
  } else if (type === 'invoice' && invoiceInputRef.value) {
    invoiceInputRef.value.click()
  }
}

/** 拖拽文件到指定区域 */
function onZoneDrop(event: DragEvent, type: 'receipt' | 'invoice') {
  dragOverZone.value = null
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    setFile(type, files[0])
  }
}

/** 文件选择框回调 */
function onZoneFileChange(event: Event, type: 'receipt' | 'invoice') {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (files && files.length > 0) {
    setFile(type, files[0])
  }
  // 重置 input 以便重复选择同一文件
  input.value = ''
}

/** 设置文件 */
function setFile(type: 'receipt' | 'invoice', file: File) {
  if (type === 'receipt') {
    pendingReceipt.value = file
    parsingReceipt.value = true
  } else {
    pendingInvoice.value = file
    parsingInvoice.value = true
  }
}

/** 清除文件 */
function clearFile(type: 'receipt' | 'invoice') {
  if (type === 'receipt') {
    pendingReceipt.value = null
    parsingReceipt.value = false
  } else {
    pendingInvoice.value = null
    parsingInvoice.value = false
  }
}

/**
 * 提交 AI 识别
 */
async function processPayment() {
  if (!pendingReceipt.value || !pendingInvoice.value) {
    ElMessage.warning('请先选择回执单和发票文件')
    return
  }

  const receipt = pendingReceipt.value
  const invoice = pendingInvoice.value

  // 打开 Copilot 面板并清空消息
  copilotOpen.value = true
  copilotMessages.value = []
  parsing.value = true

  addCopilotMsg('system', `📄 收到回执单：${receipt.name}（${formatFileSize(receipt.size)}）`)
  addCopilotMsg('system', `🧾 收到电子发票：${invoice.name}（${formatFileSize(invoice.size)}）`)
  addCopilotMsg('system', '🔍 正在解析回执单文件...')
  addCopilotMsg('system', '⏳ 正在提取金额和日期信息...')

  try {
    const result: ParseResult = await parsePaymentFiles(
      contractId.value,
      receipt,
      invoice,
    )

    parsing.value = false
    addCopilotMsg('system', '✅ 回执单解析完成')
    addCopilotMsg('system', '🔍 正在解析电子发票...')
    addCopilotMsg('system', '✅ 发票解析完成')

    if (result.matched) {
      // 匹配成功 → 自动创建回款
      addCopilotMsg('system', '🔗 正在比对回执单与发票金额...')
      addCopilotMsg(
        'result',
        `💰 回执单金额：¥${formatAmount(result.receipt_amount)}\n` +
        `🧾 发票金额：¥${formatAmount(result.invoice_amount)}\n` +
        `✅ 最终金额：¥${formatAmount(result.final_amount)}\n` +
        `📅 日期：${result.payment_date || '-'}`,
      )
      addCopilotMsg('system', '✅ 金额匹配成功，回款记录已自动创建')

      ElMessage.success('AI 识别成功，已创建回款记录')

      // 关闭新增弹窗（如果是弹窗模式）
      if (paymentFormVisible.value) {
        paymentFormVisible.value = false
      }
    } else {
      // 匹配失败 → 弹确认框
      addCopilotMsg('system', '🔗 正在比对回执单与发票金额...')
      addCopilotMsg('system', '⚠️ 金额不匹配，需要人工确认')
      addCopilotMsg(
        'result',
        `💰 回执单金额：¥${formatAmount(result.receipt_amount)}\n` +
        `🧾 发票金额：¥${formatAmount(result.invoice_amount)}\n` +
        `📅 日期：${result.payment_date || '-'}`,
      )
      addCopilotMsg('system', '⏳ 等待用户确认金额...')

      // 弹出确认对话框
      const receiptAmt = result.receipt_amount || '0'
      const invoiceAmt = result.invoice_amount || '0'
      const receiptFileId = result.receipt_file_id || ''
      const invoiceFileId = result.invoice_file_id || null

      await showAmountConfirmDialog(receiptAmt, invoiceAmt, result.payment_date, receiptFileId, invoiceFileId)
    }

    // 重置 pending 状态
    pendingReceipt.value = null
    pendingInvoice.value = null
    parsingReceipt.value = false
    parsingInvoice.value = false

    await refreshAll()
  } catch (err: any) {
    parsing.value = false
    const msg = err?.response?.data?.detail || err?.message || '解析失败，请检查文件格式或重试'
    addCopilotMsg('result', `❌ ${msg}`)
    parsingReceipt.value = false
    parsingInvoice.value = false
  }
}

// ============================================================
// 金额确认弹窗
// ============================================================
const confirmDialogVisible = ref(false)
const confirmDialogData = reactive({
  receiptAmount: '',
  invoiceAmount: '',
  paymentDate: '',
  receiptFileId: '',
  invoiceFileId: '' as string | null,
  selectedAmount: '' as string,
})

function showAmountConfirmDialog(
  receiptAmt: string,
  invoiceAmt: string,
  paymentDate: string | null | undefined,
  receiptFileId: string,
  invoiceFileId: string | null,
): Promise<void> {
  return new Promise((resolve, reject) => {
    confirmDialogData.receiptAmount = receiptAmt
    confirmDialogData.invoiceAmount = invoiceAmt
    confirmDialogData.paymentDate = paymentDate || ''
    confirmDialogData.receiptFileId = receiptFileId
    confirmDialogData.invoiceFileId = invoiceFileId
    confirmDialogData.selectedAmount = receiptAmt // 默认选回执单金额
    confirmDialogVisible.value = true
    // 将 resolve/reject 暂存
    ;(confirmDialogData as any)._resolve = resolve
    ;(confirmDialogData as any)._reject = reject
  })
}

async function onConfirmDialogConfirm() {
  const selectedAmount = confirmDialogData.selectedAmount
  if (!selectedAmount || parseFloat(selectedAmount) <= 0) {
    ElMessage.warning('请选择一个有效的金额')
    return
  }

  confirmDialogVisible.value = false

  try {
    await confirmPaymentParse(contractId.value, {
      receipt_file_id: confirmDialogData.receiptFileId,
      invoice_file_id: confirmDialogData.invoiceFileId || undefined,
      amount: selectedAmount,
      payment_date: confirmDialogData.paymentDate || undefined,
    })

    addCopilotMsg('system', `✅ 已确认金额 ¥${formatAmount(selectedAmount)}，回款记录已创建`)
    ElMessage.success('回款记录已创建')
    ;(confirmDialogData as any)._resolve?.()
  } catch {
    addCopilotMsg('result', '❌ 确认失败')
    ;(confirmDialogData as any)._reject?.()
  }
}

function onConfirmDialogCancel() {
  confirmDialogVisible.value = false
  addCopilotMsg('system', '❌ 用户取消了金额确认')
  ;(confirmDialogData as any)._reject?.()
}

// ============================================================
// 附件预览弹窗
// ============================================================
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewFile = ref<{ id: string; filename: string; mimeType?: string } | null>(null)
let pdfPreviewObserver: IntersectionObserver | null = null

/**
 * 判断预览类型：优先用扩展名和 mime_type，blob.type 兜底
 */
function getPreviewType(filename: string, mimeType?: string, blobType?: string): 'pdf' | 'image' | 'unknown' {
  const ext = (filename || '').split('.').pop()?.toLowerCase()
  const mime = (mimeType || '').toLowerCase()
  const btype = (blobType || '').toLowerCase()

  if (ext === 'pdf' || mime.includes('pdf') || btype.includes('pdf')) return 'pdf'
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext!) || mime.includes('image') || btype.startsWith('image/')) return 'image'
  return 'unknown'
}

async function openPreview(fileId: string | null, filename: string, mimeType?: string) {
  if (!fileId) return
  previewFile.value = { id: fileId, filename, mimeType }
  previewVisible.value = true
  previewLoading.value = true

  const downloadUrl = getDownloadUrl(fileId)

  try {
    const response = await fetch(downloadUrl)
    if (!response.ok) throw new Error(`文件获取失败 (${response.status})`)
    const blob = await response.blob()
    if (!blob || blob.size === 0) throw new Error('文件内容为空')

    await nextTick()
    const container = document.getElementById('preview-container')
    if (!container) return
    container.innerHTML = ''

    const previewType = getPreviewType(filename, previewFile.value?.mimeType, blob.type)

    if (previewType === 'pdf') {
      // PDF 预览
      const arrayBuffer = await blob.arrayBuffer()
      const pdf = await getDocument({ data: arrayBuffer }).promise
      const numPages = pdf.numPages

      if (pdfPreviewObserver) {
        pdfPreviewObserver.disconnect()
        pdfPreviewObserver = null
      }

      const renderedSet = new Set<number>()

      pdfPreviewObserver = new IntersectionObserver((entries) => {
        entries.forEach(async (entry) => {
          if (!entry.isIntersecting) return
          const pageNum = Number((entry.target as HTMLElement).dataset.pageNum)
          if (renderedSet.has(pageNum)) return
          renderedSet.add(pageNum)
          pdfPreviewObserver!.unobserve(entry.target)
          try {
            const page = await pdf.getPage(pageNum)
            const viewport = page.getViewport({ scale: 1.5 })
            const canvas = entry.target as HTMLCanvasElement
            canvas.width = viewport.width
            canvas.height = viewport.height
            const ctx = canvas.getContext('2d')!
            await page.render({ canvasContext: ctx, viewport, canvas }).promise
          } catch { /* ignore */ }
        })
      }, { rootMargin: '200px' })

      for (let i = 1; i <= numPages; i++) {
        const canvas = document.createElement('canvas')
        canvas.dataset.pageNum = String(i)
        canvas.style.maxWidth = '100%'
        canvas.style.margin = '0 auto 12px'
        canvas.style.display = 'block'
        canvas.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)'
        canvas.width = 800
        canvas.height = 1130
        container.appendChild(canvas)
        pdfPreviewObserver.observe(canvas)
      }
    } else if (previewType === 'image') {
      // 图片预览
      const url = URL.createObjectURL(blob)
      const img = document.createElement('img')
      img.src = url
      img.style.maxWidth = '100%'
      img.style.maxHeight = '70vh'
      img.style.objectFit = 'contain'
      img.style.display = 'block'
      img.style.margin = '0 auto'
      container.appendChild(img)
    } else {
      // 其他文件
      container.innerHTML = `<div style="text-align:center;padding:40px;color:#909399;">
        <p style="font-size:48px;">📄</p>
        <p>该文件类型暂不支持预览</p>
        <p style="margin-top:12px;">文件名：${escapeHtml(filename)}</p>
        <a href="${downloadUrl}" target="_blank" style="display:inline-block;margin-top:12px;color:#409eff;text-decoration:none;">
          点击下载
        </a>
      </div>`
    }
  } catch (err: any) {
    const container = document.getElementById('preview-container')
    if (container) {
      container.innerHTML = `<div style="text-align:center;padding:40px;color:#f56c6c;">
        <p style="font-size:48px;">⚠️</p>
        <p>预览失败：${escapeHtml(err.message || '未知错误')}</p>
      </div>`
    }
  } finally {
    previewLoading.value = false
  }
}

function onPreviewClosed() {
  if (pdfPreviewObserver) {
    pdfPreviewObserver.disconnect()
    pdfPreviewObserver = null
  }
  const container = document.getElementById('preview-container')
  if (container) {
    const imgs = container.querySelectorAll('img[src^="blob:"]')
    imgs.forEach((img) => {
      URL.revokeObjectURL((img as HTMLImageElement).src)
    })
    container.innerHTML = ''
  }
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// ============================================================
// 全局拖拽 → 智能分发气泡
// ============================================================
const dropFile = ref<File | null>(null)
const dropFileName = ref('')

const { isDragging } = useGlobalDrop({
  accept: ['pdf', 'png', 'jpg', 'jpeg'],
  multiple: false,
  onDrop: (files) => {
    if (files.length > 0) {
      dropFile.value = files[0]
      dropFileName.value = files[0].name
      // 不自动分配，等用户选择
    }
  },
})

function assignDropAs(type: 'receipt' | 'invoice') {
  const file = dropFile.value
  if (!file) return
  if (type === 'receipt') {
    pendingReceipt.value = file
    parsingReceipt.value = true
  } else {
    pendingInvoice.value = file
    parsingInvoice.value = true
  }
  dropFile.value = null
  dropFileName.value = ''

  // 打开 Copilot 提示
  copilotOpen.value = true
  if (copilotMessages.value.length === 0) {
    copilotMessages.value = []
  }
  const label = type === 'receipt' ? '回执单' : '发票'
  addCopilotMsg('system', `📄 已添加${label}：${file.name}`)
  const otherReady = type === 'receipt' ? pendingInvoice.value : pendingReceipt.value
  if (otherReady) {
    addCopilotMsg('system', '✅ 两个文件已就绪，请点击「开始 AI 识别」')
  } else {
    const otherLabel = type === 'receipt' ? '发票' : '回执单'
    addCopilotMsg('system', `💡 请继续拖入${otherLabel}文件，或点击上方「${otherLabel}」拖拽区上传`)
  }
}

// ============================================================
// 返回
// ============================================================
function goBack() {
  router.push({ name: 'ProjectList', params: { company: company.value } })
}

// ============================================================
// 格式化
// ============================================================
function formatDate(s?: string | null) {
  if (!s) return '-'
  return s.length >= 10 ? s.slice(0, 10) : s
}

function formatAmount(s?: string | null) {
  if (!s) return '-'
  const n = parseFloat(s)
  if (isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ============================================================
// 初始化
// ============================================================
onMounted(async () => {
  await Promise.all([fetchContract(), fetchPayments(), fetchSummary()])
})
</script>

<template>
  <div class="payments-page">
    <!-- ============================================================ -->
    <!-- 顶部：返回 + 合同标题 -->
    <!-- ============================================================ -->
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="goBack" size="default">返回</el-button>
      <span class="page-title">
        {{ contract?.name || '回款管理' }}
        <span v-if="contract" class="contract-meta">
          {{ contract.party_a_name || '甲方' }} vs {{ contract.party_b_name || '乙方' }}
        </span>
      </span>
    </div>

    <!-- ============================================================ -->
    <!-- 左右分栏主体 -->
    <!-- ============================================================ -->
    <div class="main-layout">
      <!-- 左侧：主内容区 -->
      <div class="left-panel">
        <!-- 汇总卡片 -->
        <el-card shadow="never" class="summary-card">
          <div class="summary-row">
            <div class="summary-item">
              <div class="summary-icon contract-icon">
                <span>📋</span>
              </div>
              <div class="summary-info">
                <span class="summary-label">合同金额</span>
                <span class="summary-value">
                  ¥{{ formatAmount(contract?.amount || paymentSummary.contract_amount) }}
                </span>
              </div>
            </div>
            <div class="summary-divider" />
            <div class="summary-item">
              <div class="summary-icon paid-icon">
                <span>💰</span>
              </div>
              <div class="summary-info">
                <span class="summary-label">已回款</span>
                <span class="summary-value highlight">¥{{ formatAmount(paymentSummary.total_paid) }}</span>
              </div>
            </div>
            <div class="summary-divider" />
            <div class="summary-item">
              <div class="summary-icon progress-icon">
                <span>📊</span>
              </div>
              <div class="summary-info">
                <span class="summary-label">回款进度</span>
                <span class="summary-value">{{ paymentSummary.progress }}%</span>
              </div>
            </div>
          </div>
          <el-progress
            :percentage="paymentSummary.progress"
            :stroke-width="12"
            :status="paymentSummary.progress >= 100 ? 'success' : ''"
            class="summary-progress"
          />
        </el-card>

        <!-- 操作栏 -->
        <el-card shadow="never" class="actions-card">
          <div class="actions-row">
            <el-button type="primary" :icon="Plus" @click="showAddPaymentForm">
              新增回款
            </el-button>

            <!-- AI 智能识别：双拖拽区 -->
            <div class="ai-recognition-section">
              <div class="ai-section-title">AI 智能识别</div>
              <div class="ai-drop-zones">
                <!-- 回执单拖拽区 -->
                <div
                  class="ai-drop-zone"
                  :class="{ 'has-file': pendingReceipt, 'is-dragover': dragOverZone === 'receipt' }"
                  @dragover.prevent="dragOverZone = 'receipt'"
                  @dragleave="dragOverZone = null"
                  @drop.prevent="onZoneDrop($event, 'receipt')"
                  @click="triggerFileInput('receipt')"
                >
                  <input
                    type="file"
                    ref="receiptInputRef"
                    accept=".pdf,.png,.jpg,.jpeg"
                    style="display:none"
                    @change="onZoneFileChange($event, 'receipt')"
                  />
                  <template v-if="!pendingReceipt">
                    <el-icon :size="28"><UploadFilled /></el-icon>
                    <span class="zone-label">回执单</span>
                    <span class="zone-hint">拖拽或点击上传</span>
                  </template>
                  <template v-else>
                    <el-icon :size="20"><Document /></el-icon>
                    <span class="zone-filename">{{ pendingReceipt.name }}</span>
                    <span class="zone-size">{{ formatFileSize(pendingReceipt.size) }}</span>
                    <el-button
                      link
                      type="danger"
                      size="small"
                      @click.stop="clearFile('receipt')"
                    >移除</el-button>
                  </template>
                </div>

                <!-- 发票拖拽区 -->
                <div
                  class="ai-drop-zone"
                  :class="{ 'has-file': pendingInvoice, 'is-dragover': dragOverZone === 'invoice' }"
                  @dragover.prevent="dragOverZone = 'invoice'"
                  @dragleave="dragOverZone = null"
                  @drop.prevent="onZoneDrop($event, 'invoice')"
                  @click="triggerFileInput('invoice')"
                >
                  <input
                    type="file"
                    ref="invoiceInputRef"
                    accept=".pdf,.png,.jpg,.jpeg"
                    style="display:none"
                    @change="onZoneFileChange($event, 'invoice')"
                  />
                  <template v-if="!pendingInvoice">
                    <el-icon :size="28"><UploadFilled /></el-icon>
                    <span class="zone-label">电子发票</span>
                    <span class="zone-hint">拖拽或点击上传</span>
                  </template>
                  <template v-else>
                    <el-icon :size="20"><Document /></el-icon>
                    <span class="zone-filename">{{ pendingInvoice.name }}</span>
                    <span class="zone-size">{{ formatFileSize(pendingInvoice.size) }}</span>
                    <el-button
                      link
                      type="danger"
                      size="small"
                      @click.stop="clearFile('invoice')"
                    >移除</el-button>
                  </template>
                </div>
              </div>

              <!-- 开始识别按钮 -->
              <div class="ai-actions">
                <el-button
                  type="primary"
                  :loading="parsing"
                  :disabled="!pendingReceipt || !pendingInvoice"
                  :icon="MagicStick"
                  @click="processPayment"
                >
                  {{ parsing ? 'AI 正在识别...' : '开始 AI 识别' }}
                </el-button>
                <span class="drop-hint">或拖拽文件到上方对应区域</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 回款列表 -->
        <el-card shadow="never" class="list-card">
          <el-table
            :data="paymentList"
            border
            stripe
            style="width: 100%"
            empty-text="暂无回款记录"
            size="default"
          >
            <el-table-column prop="payment_date" label="日期" width="120" align="center">
              <template #default="{ row }">{{ formatDate(row.payment_date) }}</template>
            </el-table-column>
            <el-table-column label="金额" width="160" align="right">
              <template #default="{ row }">
                <span class="amount-cell">¥{{ formatAmount(row.amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="回执单" width="140" align="center">
              <template #default="{ row }">
                <template v-if="row.receipt_file_id">
                  <el-link
                    type="primary"
                    :underline="false"
                    @click="openPreview(row.receipt_file_id, row.receipt_filename || '回执单', row.receipt_mime_type)"
                  >
                    <el-icon style="margin-right:2px;"><View /></el-icon>
                    查看
                  </el-link>
                </template>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="发票" width="140" align="center">
              <template #default="{ row }">
                <template v-if="row.invoice_file_id">
                  <el-link
                    type="primary"
                    :underline="false"
                    @click="openPreview(row.invoice_file_id, row.invoice_filename || '发票', row.invoice_mime_type)"
                  >
                    <el-icon style="margin-right:2px;"><View /></el-icon>
                    查看
                  </el-link>
                </template>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="140" align="center" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="editPayment(row)">编辑</el-button>
                <el-popconfirm title="确定删除？" @confirm="handleDeletePayment(row.id)">
                  <template #reference>
                    <el-button size="small" text type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
      <!-- 右侧留空（Copilot 通过 Teleport 渲染到 body） -->
    </div>

    <!-- ============================================================ -->
    <!-- 新增/编辑回款弹窗（手动模式 + AI 上传） -->
    <!-- ============================================================ -->
    <el-dialog
      v-model="paymentFormVisible"
      :title="editingPayment ? '编辑回款' : '新增回款'"
      width="520px"
      destroy-on-close
    >
      <!-- AI 上传区（仅新增模式显示） -->
      <div v-if="!editingPayment" class="dialog-ai-upload">
        <div class="dialog-ai-title">AI 智能识别（推荐）</div>
        <div class="dialog-ai-drop-zones">
          <!-- 回执单拖拽区 -->
          <div
            class="dialog-ai-drop-zone"
            :class="{ 'has-file': pendingReceipt }"
            @click="triggerFileInput('receipt')"
          >
            <template v-if="!pendingReceipt">
              <el-icon :size="24"><UploadFilled /></el-icon>
              <span class="dialog-zone-label">回执单</span>
              <span class="dialog-zone-hint">拖拽或点击上传</span>
            </template>
            <template v-else>
              <el-icon :size="18"><Document /></el-icon>
              <span class="dialog-zone-filename">{{ pendingReceipt.name }}</span>
              <el-button link type="danger" size="small" @click.stop="clearFile('receipt')">移除</el-button>
            </template>
          </div>
          <!-- 发票拖拽区 -->
          <div
            class="dialog-ai-drop-zone"
            :class="{ 'has-file': pendingInvoice }"
            @click="triggerFileInput('invoice')"
          >
            <template v-if="!pendingInvoice">
              <el-icon :size="24"><UploadFilled /></el-icon>
              <span class="dialog-zone-label">电子发票</span>
              <span class="dialog-zone-hint">拖拽或点击上传</span>
            </template>
            <template v-else>
              <el-icon :size="18"><Document /></el-icon>
              <span class="dialog-zone-filename">{{ pendingInvoice.name }}</span>
              <el-button link type="danger" size="small" @click.stop="clearFile('invoice')">移除</el-button>
            </template>
          </div>
        </div>
        <div class="dialog-ai-actions">
          <el-button
            type="primary"
            :loading="parsing"
            :disabled="!pendingReceipt || !pendingInvoice"
            :icon="MagicStick"
            size="small"
            @click="processPayment"
          >
            {{ parsing ? 'AI 正在识别...' : '开始 AI 识别' }}
          </el-button>
        </div>
        <el-divider />
        <div class="dialog-manual-title">或手动填写</div>
      </div>

      <el-form :model="paymentForm" label-width="100px">
        <el-form-item label="回款金额" required>
          <el-input-number
            v-model="paymentForm.amount"
            :min="0"
            :precision="2"
            :step="10000"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="回款日期">
          <el-date-picker
            v-model="paymentForm.payment_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="paymentForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paymentFormVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPayment">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============================================================ -->
    <!-- 金额确认弹窗 -->
    <!-- ============================================================ -->
    <el-dialog
      v-model="confirmDialogVisible"
      title="金额确认"
      width="480px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <div class="confirm-dialog-content">
        <p class="confirm-dialog-desc">
          AI 解析的两个金额不一致，请选择最终回款金额：
        </p>
        <div class="confirm-dialog-options">
          <el-radio-group v-model="confirmDialogData.selectedAmount" class="confirm-radio-group">
            <el-radio :value="confirmDialogData.receiptAmount" class="confirm-radio-item">
              <span class="confirm-radio-label">回执单金额</span>
              <span class="confirm-radio-value">¥{{ formatAmount(confirmDialogData.receiptAmount) }}</span>
            </el-radio>
            <el-radio :value="confirmDialogData.invoiceAmount" class="confirm-radio-item">
              <span class="confirm-radio-label">发票金额</span>
              <span class="confirm-radio-value">¥{{ formatAmount(confirmDialogData.invoiceAmount) }}</span>
            </el-radio>
          </el-radio-group>
        </div>
        <div v-if="confirmDialogData.paymentDate" class="confirm-dialog-date">
          识别日期：{{ confirmDialogData.paymentDate }}
        </div>
      </div>
      <template #footer>
        <el-button @click="onConfirmDialogCancel">取消</el-button>
        <el-button type="primary" @click="onConfirmDialogConfirm">
          确认并创建回款
        </el-button>
      </template>
    </el-dialog>

    <!-- ============================================================ -->
    <!-- 附件预览弹窗 -->
    <!-- ============================================================ -->
    <el-dialog
      v-model="previewVisible"
      :title="previewFile?.filename || '文件预览'"
      width="80%"
      top="3vh"
      destroy-on-close
      :close-on-click-modal="false"
      class="preview-dialog"
      @closed="onPreviewClosed"
    >
      <div v-if="previewFile" style="text-align:right;margin-bottom:12px;">
        <a :href="getDownloadUrl(previewFile.id)" target="_blank">
          <el-button size="small" type="primary">
            <el-icon><Download /></el-icon> 下载
          </el-button>
        </a>
      </div>
      <div v-loading="previewLoading" style="min-height:300px;">
        <div id="preview-container" style="overflow:auto;max-height:70vh;"></div>
      </div>
    </el-dialog>

    <!-- ============================================================ -->
    <!-- 全局拖拽遮罩 -->
    <!-- ============================================================ -->
    <Teleport to="body">
      <div v-if="isDragging || dropFile" class="global-drop-overlay">
        <div class="global-drop-box">
          <template v-if="!dropFile">
            <el-icon :size="48"><UploadFilled /></el-icon>
            <p>释放文件以 AI 识别</p>
            <p class="drop-sub-hint">支持 PDF、PNG、JPG 格式</p>
          </template>
          <template v-else>
            <el-icon :size="32"><Document /></el-icon>
            <p class="drop-file-name">{{ dropFileName }}</p>
            <p class="drop-sub-hint">请选择文件用途：</p>
            <div class="drop-actions">
              <el-button type="primary" size="large" @click="assignDropAs('receipt')">
                <el-icon><UploadFilled /></el-icon> 作为回执单
              </el-button>
              <el-button type="warning" size="large" @click="assignDropAs('invoice')">
                <el-icon><UploadFilled /></el-icon> 作为电子发票
              </el-button>
            </div>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- ============================================================ -->
    <!-- Copilot AI 助手面板（Teleport 到 body） -->
    <!-- ============================================================ -->
    <Teleport to="body">
      <div class="copilot-wrapper" :class="{ open: copilotOpen }">
        <div class="copilot-toggle" @click="copilotOpen = !copilotOpen">
          <el-icon :size="22"><MagicStick /></el-icon>
          <span v-if="!copilotOpen" class="toggle-label">AI 助手</span>
        </div>
        <div class="copilot-panel">
          <div class="copilot-header">
            <span>🤖 回款解析助手</span>
            <el-button link @click="copilotOpen = false">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <div class="copilot-body" ref="copilotBodyRef">
            <div
              v-for="(msg, i) in copilotMessages"
              :key="i"
              class="copilot-msg"
              :class="`msg-${msg.role}`"
            >
              <div class="msg-bubble">
                <span v-if="msg.text">{{ msg.text }}</span>
              </div>
              <div class="msg-time" v-if="msg.time">{{ msg.time }}</div>
            </div>
            <div v-if="parsing" class="copilot-msg msg-system">
              <div class="msg-bubble thinking">
                <span class="dot-pulse"></span> AI 正在分析回执单...
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ============================================================
   页面整体
   ============================================================ */
.payments-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* ============================================================
   顶部
   ============================================================ */
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a3270;
  display: flex;
  align-items: center;
  gap: 12px;
}

.contract-meta {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
  padding: 2px 10px;
  background: #ecf5ff;
  border-radius: 4px;
}

/* ============================================================
   左右分栏
   ============================================================ */
.main-layout {
  display: flex;
  gap: 0;
}

.left-panel {
  flex: 1;
  min-width: 0;
}

/* ============================================================
   汇总卡片
   ============================================================ */
.summary-card {
  margin-bottom: 16px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  background: #fff;
}

.summary-row {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  padding: 4px 0;
}

.summary-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.contract-icon {
  background: #ecf5ff;
}

.paid-icon {
  background: #e8f5e9;
}

.progress-icon {
  background: #fff3e0;
}

.summary-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-size: 13px;
  color: #909399;
}

.summary-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
}

.summary-value.highlight {
  color: #1a3270;
}

.summary-divider {
  width: 1px;
  height: 48px;
  background: #e4e7ed;
  margin: 0 20px;
}

.summary-progress {
  margin-top: 4px;
}

/* ============================================================
   操作栏
   ============================================================ */
.actions-card {
  margin-bottom: 16px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  background: #fff;
}

.actions-row {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ============================================================
   AI 智能识别区域 - 双拖拽区
   ============================================================ */
.ai-recognition-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a3270;
}

.ai-drop-zones {
  display: flex;
  gap: 16px;
}

.ai-drop-zone {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 20px 16px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  background: #fafafa;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  text-align: center;
  user-select: none;
}

.ai-drop-zone:hover {
  border-color: #1a5cb0;
  background: #ecf5ff;
}

.ai-drop-zone.is-dragover {
  border-color: #1a3270;
  background: #e8edf5;
  border-style: solid;
}

.ai-drop-zone.has-file {
  border-color: #67c23a;
  border-style: solid;
  background: #f0f9eb;
  flex-direction: row;
  gap: 8px;
  padding: 12px 16px;
}

.zone-label {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.zone-required {
  font-size: 12px;
  color: #f56c6c;
  font-weight: 500;
}

.zone-hint {
  font-size: 12px;
  color: #c0c4cc;
}

.zone-filename {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.zone-size {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.ai-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drop-hint {
  font-size: 12px;
  color: #c0c4cc;
}

/* ============================================================
   列表卡片
   ============================================================ */
.list-card {
  margin-bottom: 16px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  background: #fff;
}

.amount-cell {
  font-weight: 600;
  font-size: 14px;
  color: #1a3270;
}

.muted {
  color: #c0c4cc;
}

/* ============================================================
   新增回款弹窗 - AI 上传区
   ============================================================ */
.dialog-ai-upload {
  margin-bottom: 8px;
}

.dialog-ai-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a3270;
  margin-bottom: 12px;
}

.dialog-ai-drop-zones {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.dialog-ai-drop-zone {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 16px 12px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  background: #fafafa;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  text-align: center;
  user-select: none;
}

.dialog-ai-drop-zone:hover {
  border-color: #1a5cb0;
  background: #ecf5ff;
}

.dialog-ai-drop-zone.has-file {
  border-color: #67c23a;
  border-style: solid;
  background: #f0f9eb;
  flex-direction: row;
  gap: 8px;
  padding: 10px 12px;
}

.dialog-zone-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.dialog-zone-required {
  font-size: 11px;
  color: #f56c6c;
  font-weight: 500;
}

.dialog-zone-hint {
  font-size: 11px;
  color: #c0c4cc;
}

.dialog-zone-filename {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.dialog-ai-actions {
  display: flex;
  justify-content: center;
}

.dialog-manual-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

/* ============================================================
   金额确认弹窗
   ============================================================ */
.confirm-dialog-content {
  padding: 0;
}

.confirm-dialog-desc {
  font-size: 14px;
  color: #303133;
  margin-bottom: 20px;
  line-height: 1.6;
}

.confirm-dialog-options {
  margin-bottom: 16px;
}

.confirm-radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.confirm-radio-item {
  display: flex !important;
  align-items: center;
  width: 100%;
  padding: 14px 16px !important;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin: 0 !important;
  transition: border-color 0.2s, background 0.2s;
}

.confirm-radio-item:hover {
  border-color: #1a5cb0;
  background: #f0f5ff;
}

.confirm-radio-label {
  font-size: 14px;
  color: #606266;
  margin-right: 12px;
}

.confirm-radio-value {
  font-size: 18px;
  font-weight: 700;
  color: #1a3270;
}

.confirm-dialog-date {
  font-size: 13px;
  color: #909399;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

/* ============================================================
   预览弹窗
   ============================================================ */
.preview-dialog :deep(.el-dialog__body) {
  padding: 12px 24px 24px;
}

/* ============================================================
   全局拖拽遮罩
   ============================================================ */
.global-drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}

.global-drop-box {
  background: #fff;
  border: 3px dashed #1a3270;
  border-radius: 12px;
  padding: 48px 64px;
  text-align: center;
  color: #1a3270;
  font-size: 16px;
}

.drop-sub-hint {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.drop-file-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a3270;
  margin: 8px 0 4px;
  word-break: break-all;
}

.drop-actions {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

/* ============================================================
   Copilot 助手面板
   ============================================================ */
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
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.1);
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
  color: #1a3270;
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
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1.2);
  }
}
</style>
