<script setup lang="ts">
/**
 * 附件管理页 — 双栏文件管理器布局
 *
 * 路由：/contracts/compute-leasing/:id/attachments
 * contract_type 固定为 compute_leasing（资产平台仅保留算力租赁合同附件）。
 */
import { computed, onMounted, ref, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { CheckboxValueType } from 'element-plus'
import { confirmDelete } from '@/lib/confirm'
import {
  ArrowDown,
  ArrowLeft,
  Download,
  Delete,
  Plus,
  Loading,
  Document,
  Folder,
  WarningFilled,
} from '@element-plus/icons-vue'
import {
  getAttachments,
  deleteAttachment,
  confirmAttachmentItem,
  unconfirmAttachmentItem,
  type AttachmentCategory,
  type AttachmentFile,
  type AttachmentItem,
  type ContractType,
} from '@/api/modules/attachment'
import { CONTRACT_TYPE_LABEL } from '@/lib/contract'

// 文件预览相关依赖
import { renderAsync as renderDocx } from 'docx-preview'
import * as XLSX from 'xlsx'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import { init as initPptxPreview } from 'pptx-preview'

// 配置 pdfjs worker（本地 npm 包导入，Vite ?url 后缀确保 worker 被正确打包）
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
GlobalWorkerOptions.workerSrc = pdfjsWorker
// 兜底：如果 worker 加载失败（如浏览器缓存问题），使用 blob URL
// 不适用于本场景，?url 导入已由 Vite 正确处理路径和 MIME 类型

const route = useRoute()
const router = useRouter()

// ============================================================
// 合同类型与 ID
// ============================================================
const contractType: ContractType = 'compute_leasing'

const contractId = computed(() => route.params.id as string)

// ============================================================
// 数据状态
// ============================================================
const loading = ref(false)
const categories = ref<AttachmentCategory[]>([])
const expandedCategories = ref<string[]>([])

/** 当前选中的子项 ID（默认第一个） */
const selectedItemId = ref<string>('')

/** 计算当前选中的子项对象 */
const selectedItem = computed(() => {
  if (!selectedItemId.value) return null
  for (const cat of categories.value) {
    for (const item of cat.items) {
      if (item.item_id === selectedItemId.value) return item
    }
  }
  return null
})

// 上传中状态：{ item_id: boolean }
const uploadingMap = ref<Record<string, boolean>>({})

async function fetchAttachments() {
  loading.value = true
  const previousSelectedId = selectedItemId.value
  try {
    const res = await getAttachments(contractType, contractId.value)
    categories.value = res.categories
    // 默认展开所有分类
    expandedCategories.value = res.categories.map((c) => c.category_id)
    // 保持之前选中的子项，找不到时才默认第一个
    const stillExists = res.categories.some(cat =>
      cat.items.some(item => item.item_id === previousSelectedId)
    )
    if (previousSelectedId && stillExists) {
      selectedItemId.value = previousSelectedId
    } else if (categories.value.length > 0 && categories.value[0].items.length > 0) {
      selectedItemId.value = categories.value[0].items[0].item_id
    }
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// 导航
// ============================================================
function goBack() {
  const prefix = getListRoute()
  router.push(prefix)
}

function getListRoute() {
  return { name: 'ContractList' }
}

// ============================================================
// 折叠/展开
// ============================================================
function toggleCategory(categoryId: string) {
  const idx = expandedCategories.value.indexOf(categoryId)
  if (idx >= 0) {
    expandedCategories.value.splice(idx, 1)
  } else {
    expandedCategories.value.push(categoryId)
  }
}

function isExpanded(categoryId: string): boolean {
  return expandedCategories.value.includes(categoryId)
}

// ============================================================
// 确认 / 取消确认
// ============================================================
async function handleConfirm(item: AttachmentItem) {
  try {
    await confirmAttachmentItem(contractType, contractId.value, item.item_id)
    ElMessage.success('已确认')
    fetchAttachments()
  } catch {
    // 错误已统一处理
  }
}

async function handleUnconfirm(item: AttachmentItem) {
  try {
    await unconfirmAttachmentItem(contractType, contractId.value, item.item_id)
    ElMessage.success('已取消确认')
    fetchAttachments()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 上传
// ============================================================
const uploadRefs = ref<Record<string, any>>({})
const uploadProgressMap = ref<Record<string, number>>({}) // itemId → 百分比
const uploadErrorMap = ref<Record<string, string>>({})     // itemId → 错误信息

function handleBeforeUpload(file: File, itemId: string) {
  // 自动上传
  handleUpload(file, itemId)
  return false // 阻止 el-upload 默认上传
}

async function handleUpload(file: File, itemId: string) {
  uploadingMap.value[itemId] = true
  uploadProgressMap.value[itemId] = 0
  uploadErrorMap.value[itemId] = ''

  try {
    const formData = new FormData()
    formData.append('files', file)
    const url = `/attachments/upload?contract_type=${contractType}&contract_id=${contractId.value}&item_id=${itemId}`
    const { default: request } = await import('@/api')
    await request.post(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600_000, // 10 分钟超时（大文件）
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          uploadProgressMap.value[itemId] = pct
        }
      },
    })
    ElMessage.success(`文件 "${file.name}" 上传成功`)
    uploadProgressMap.value[itemId] = 100
    fetchAttachments()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '上传失败'
    uploadErrorMap.value[itemId] = msg
    ElMessage.error(`上传失败：${msg}`)
  } finally {
    uploadingMap.value[itemId] = false
    // 3 秒后清除进度和错误（让用户看到最终状态）
    setTimeout(() => {
      delete uploadProgressMap.value[itemId]
      delete uploadErrorMap.value[itemId]
    }, 3000)
  }
}

// ============================================================
// 下载
// ============================================================
function handleDownload(file: AttachmentFile) {
  window.open(`/api/attachments/${file.id}/download`, '_blank')
}

// ============================================================
// 一键导出附件 ZIP
// ============================================================
function handleExportAllAttachments() {
  window.open(
    `/api/attachments/export?contract_type=${contractType}&contract_id=${contractId.value}`,
    '_blank',
  )
}

// ============================================================
// 删除
// ============================================================
async function handleDeleteFile(file: AttachmentFile) {
  if (!(await confirmDelete(`确定删除文件「${file.filename}」？`))) return
  try {
    await deleteAttachment(file.id)
    ElMessage.success('文件已删除')
    fetchAttachments()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 文件大小格式化
// ============================================================
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ============================================================
// 状态辅助
// ============================================================
function itemStatusTagType(item: AttachmentItem): 'success' | 'danger' | 'info' {
  if (item.file_count === 0) return 'info'
  return item.confirmed ? 'success' : 'danger'
}

function itemStatusText(item: AttachmentItem): string {
  if (item.file_count === 0) return '未上传'
  return item.confirmed ? '已确认' : '未确认'
}

function formatUploadTime(s?: string) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

// ============================================================
// 文件预览
// ============================================================
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewFile = ref<AttachmentFile | null>(null)
const previewType = ref<'pdf' | 'docx' | 'xlsx' | 'pptx' | 'image' | 'text' | 'unknown'>('unknown')

const previewTypeLabel = computed(() => {
  const map: Record<typeof previewType.value, string> = {
    pdf: 'PDF',
    docx: 'Word',
    xlsx: 'Excel',
    pptx: 'PPT',
    image: '图片',
    text: '文本',
    unknown: '文件',
  }
  return map[previewType.value]
})

/** PDF 预览的 IntersectionObserver，弹窗关闭时清理 */
let pdfPreviewObserver: IntersectionObserver | null = null

function getPreviewType(file: AttachmentFile): typeof previewType.value {
  const ext = (file.filename || '').split('.').pop()?.toLowerCase()
  const mime = (file.mime_type || '').toLowerCase()
  if (ext === 'pdf' || mime.includes('pdf')) return 'pdf'
  // xlsx/pptx 必须在 docx 之前判断，因为 office MIME 都包含 "document" 子串
  if (ext === 'xlsx' || ext === 'xls' || mime.includes('spreadsheet')) return 'xlsx'
  if (ext === 'pptx' || ext === 'ppt' || mime.includes('presentation')) return 'pptx'
  if (ext === 'docx' || ext === 'doc' || (mime.includes('word') && !mime.includes('spreadsheet') && !mime.includes('presentation'))) return 'docx'
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext!) || mime.includes('image')) return 'image'
  if (['txt', 'csv', 'log', 'json', 'xml', 'md', 'yaml', 'yml'].includes(ext!) || mime.includes('text')) return 'text'
  return 'unknown'
}

async function handlePreview(file: AttachmentFile) {
  previewFile.value = file
  previewVisible.value = true
  previewLoading.value = true
  previewType.value = getPreviewType(file)

  const downloadUrl = `/api/attachments/${file.id}/download`

  try {
    const response = await fetch(downloadUrl)
    if (!response.ok) throw new Error(`文件获取失败 (${response.status})`)
    const blob = await response.blob()
    if (!blob || blob.size === 0) throw new Error('文件内容为空')

    // 等待 DOM 更新后再操作 container
    await nextTick()
    const container = document.getElementById('preview-container')
    if (!container) return

    // 清空旧内容
    container.innerHTML = ''

    switch (previewType.value) {
      case 'pdf': {
        const arrayBuffer = await blob.arrayBuffer()
        const pdf = await getDocument({ data: arrayBuffer }).promise
        const numPages = pdf.numPages

        // 清理上一个 observer（如果存在）
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
            } catch { /* 忽略单页渲染错误，不影响其他页 */ }
          })
        }, { rootMargin: '200px' })

        // 预创建所有占位 canvas（不渲染），后续按可见性懒加载
        for (let i = 1; i <= numPages; i++) {
          const canvas = document.createElement('canvas')
          canvas.dataset.pageNum = String(i)
          canvas.style.maxWidth = '100%'
          canvas.style.margin = '0 auto 12px'
          canvas.style.display = 'block'
          canvas.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)'
          // 预设 A4 比例宽高，避免布局抖动
          canvas.width = 800
          canvas.height = 1130
          container.appendChild(canvas)
          pdfPreviewObserver.observe(canvas)
        }
        break
      }
      case 'docx': {
        await renderDocx(blob, container, undefined, {
          className: 'docx-preview',
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: true,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          experimental: false,
          trimXmlDeclaration: true,
          useBase64URL: true,
          renderChanges: false,
          renderHeaders: false,
          renderFooters: false,
          renderFootnotes: true,
          renderEndnotes: true,
        })
        break
      }
      case 'xlsx': {
        try {
          const arrayBuffer = await blob.arrayBuffer()
          const workbook = XLSX.read(arrayBuffer, { type: 'array' })

          // 预渲染所有 sheet 的 HTML
          const sheetsHtml: { name: string; html: string }[] = []
          workbook.SheetNames.forEach((sheetName) => {
            const sheet = workbook.Sheets[sheetName]
            const html = XLSX.utils.sheet_to_html(sheet, {
              id: '',
              editable: false,
            })
            sheetsHtml.push({ name: sheetName, html })
          })

          // 构建 tab 切换栏
          const tabBar = document.createElement('div')
          tabBar.style.display = 'flex'
          tabBar.style.gap = '4px'
          tabBar.style.marginBottom = '12px'
          tabBar.style.borderBottom = '2px solid #e4e7ed'
          tabBar.style.paddingBottom = '0'

          // sheet 内容区
          const sheetContent = document.createElement('div')

          function activateTab(idx: number) {
            // 更新 tab 样式
            tabBar.querySelectorAll('.xlsx-tab').forEach((t, i) => {
              const el = t as HTMLElement
              el.style.color = i === idx ? '#409eff' : '#606266'
              el.style.borderBottom = i === idx ? '2px solid #409eff' : '2px solid transparent'
              el.style.fontWeight = i === idx ? '600' : '400'
            })
            // 显示对应 sheet
            sheetContent.innerHTML = ''
            const wrapper = document.createElement('div')
            wrapper.innerHTML = sheetsHtml[idx].html
            const table = wrapper.querySelector('table')
            if (table) {
              table.style.borderCollapse = 'collapse'
              table.style.width = '100%'
              table.style.fontSize = '13px'
              table.querySelectorAll('td, th').forEach((td: any) => {
                td.style.border = '1px solid #e4e7ed'
                td.style.padding = '4px 8px'
              })
              const headerRow = table.querySelector('tr:first-child')
              if (headerRow) {
                headerRow.querySelectorAll('td, th').forEach((td: any) => {
                  td.style.backgroundColor = '#f5f7fa'
                  td.style.fontWeight = '600'
                })
              }
            }
            sheetContent.appendChild(wrapper)
          }

          sheetsHtml.forEach(({ name }, idx) => {
            const tab = document.createElement('span')
            tab.className = 'xlsx-tab'
            tab.textContent = name
            tab.style.padding = '6px 14px'
            tab.style.cursor = 'pointer'
            tab.style.fontSize = '13px'
            tab.style.transition = 'color 0.15s, border-color 0.15s'
            tab.style.borderBottom = '2px solid transparent'
            tab.style.marginBottom = '-2px'
            tab.addEventListener('click', () => activateTab(idx))
            tabBar.appendChild(tab)
          })

          container.appendChild(tabBar)
          container.appendChild(sheetContent)
          activateTab(0)
        } catch (e: any) {
          container.innerHTML = `<div style="text-align:center;padding:40px;color:#f56c6c;">
            <p style="font-size:48px;">⚠️</p>
            <p>Excel 解析失败：${e.message || '文件格式异常'}</p>
            <p style="font-size:13px;color:#909399;margin-top:12px;">请点击上方「下载」按钮下载后查看</p>
          </div>`
        }
        break
      }
      case 'pptx': {
        const arrayBuffer = await blob.arrayBuffer()
        await initPptxPreview(container, {
          width: 960,
          height: 540,
          mode: 'slide',
        }).preview(arrayBuffer)
        break
      }
      case 'image': {
        const url = URL.createObjectURL(blob)
        const img = document.createElement('img')
        img.src = url
        img.style.maxWidth = '100%'
        img.style.maxHeight = '70vh'
        img.style.objectFit = 'contain'
        img.style.display = 'block'
        img.style.margin = '0 auto'
        container.appendChild(img)
        break
      }
      case 'text': {
        const text = await blob.text()
        const pre = document.createElement('pre')
        pre.textContent = text
        pre.style.whiteSpace = 'pre-wrap'
        pre.style.wordBreak = 'break-word'
        pre.style.fontSize = '13px'
        pre.style.fontFamily = 'monospace'
        pre.style.maxHeight = '60vh'
        pre.style.overflow = 'auto'
        pre.style.padding = '16px'
        pre.style.background = '#fafbfc'
        pre.style.borderRadius = '6px'
        container.appendChild(pre)
        break
      }
      default: {
        container.innerHTML = `<div style="text-align:center;padding:40px;color:#909399;">
          <p style="font-size:48px;">📄</p>
          <p>该文件类型暂不支持预览，请点击下方按钮下载查看</p>
        </div>`
      }
    }
  } catch (err: any) {
    const container = document.getElementById('preview-container')
    if (container) {
      container.innerHTML = `<div style="text-align:center;padding:40px;color:#f56c6c;">
        <p style="font-size:48px;">⚠️</p>
        <p>预览失败：${err.message || '未知错误'}</p>
      </div>`
    }
  } finally {
    previewLoading.value = false
  }
}

// 关闭弹窗时清理资源（避免内存泄漏）
function onPreviewDialogClosed() {
  // 清理 PDF 预览的 IntersectionObserver
  if (pdfPreviewObserver) {
    pdfPreviewObserver.disconnect()
    pdfPreviewObserver = null
  }
  const container = document.getElementById('preview-container')
  if (container) {
    // 清理图片 blob URL
    const imgs = container.querySelectorAll('img[src^="blob:"]')
    imgs.forEach((img) => {
      URL.revokeObjectURL((img as HTMLImageElement).src)
    })
    container.innerHTML = ''
  }
}

onMounted(() => {
  fetchAttachments()
})
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
        <h1 class="header-title">
          <el-icon><Document /></el-icon>
          附件管理
        </h1>
        <div class="header-sub">{{ CONTRACT_TYPE_LABEL[contractType] || contractType }}合同</div>
      </div>
      <div class="header-actions">
        <el-button :icon="Download" @click="handleExportAllAttachments" :disabled="loading">
          一键导出附件
        </el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="categories.length === 0" class="empty-section">
      <div class="table-empty">
        <el-empty description="暂无附件分类配置，请先在系统配置中配置附件分类" />
      </div>
    </div>

    <!-- 双栏主体 -->
    <div v-else class="main-panels">
      <!-- ====== 左侧：分类树 ====== -->
      <div class="left-tree">
        <div class="tree-title">附件分类</div>
        <div class="tree-scroll">
          <div v-for="cat in categories" :key="cat.category_id" class="tree-category">
            <div
              class="tree-cat-header"
              :class="{ collapsed: !isExpanded(cat.category_id) }"
              @click="toggleCategory(cat.category_id)"
            >
              <el-icon class="cat-arrow"><ArrowDown /></el-icon>
              <el-icon class="cat-icon"><Folder /></el-icon>
              <span class="cat-name" :title="cat.category_name">{{ cat.category_name }}</span>
              <span class="cat-count">
                {{ cat.items.reduce((s, it) => s + it.file_count, 0) }}
              </span>
            </div>
            <div v-show="isExpanded(cat.category_id)" class="cat-items">
              <button
                v-for="item in cat.items"
                :key="item.item_id"
                type="button"
                class="tree-item"
                :class="{
                  active: selectedItemId === item.item_id,
                  'is-confirmed': item.confirmed,
                  'is-pending': !item.confirmed && item.file_count > 0,
                  'is-empty': item.file_count === 0,
                }"
                @click="selectedItemId = item.item_id"
              >
                <span
                  class="item-status-dot"
                  :title="item.confirmed ? '已确认' : item.file_count > 0 ? '未确认' : '未上传'"
                />
                <span class="item-label" :title="item.item_name">{{ item.item_name }}</span>
                <span v-if="item.file_count > 0" class="item-file-count">{{ item.file_count }}</span>
                <span
                  class="item-badge"
                  :class="item.confirmed ? 'badge-ok' : item.file_count > 0 ? 'badge-warn' : 'badge-none'"
                >
                  {{ item.confirmed ? '已确认' : item.file_count > 0 ? '未确认' : '未上传' }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== 右侧：文件区 ====== -->
      <div class="right-panel">
        <template v-if="selectedItem">
          <div class="panel-header">
            <div class="item-title">
              <el-checkbox
                :model-value="selectedItem.confirmed"
                :disabled="selectedItem.file_count === 0"
                @change="(val: boolean | CheckboxValueType) => {
                  const v = typeof val === 'boolean' ? val : false
                  if (selectedItem) {
                    v ? handleConfirm(selectedItem) : handleUnconfirm(selectedItem)
                  }
                }"
              >
                <span class="item-name-text">{{ selectedItem.item_name }}</span>
              </el-checkbox>
              <span v-if="selectedItem.expected_type" class="item-type-badge">
                {{ selectedItem.expected_type.toUpperCase() }}
              </span>
            </div>
            <div class="item-status">
              <el-tag :type="itemStatusTagType(selectedItem)" size="small">
                {{ itemStatusText(selectedItem) }}
              </el-tag>
              <span class="file-count-tag">{{ selectedItem.file_count }} 个文件</span>
            </div>
          </div>

          <div class="right-body">
            <div class="file-section" v-if="selectedItem.files.length > 0">
              <div class="file-list-head">
                <span class="col-name">文件名</span>
                <span class="col-size">大小</span>
                <span class="col-time">上传时间</span>
                <span class="col-actions">操作</span>
              </div>
              <div
                v-for="file in selectedItem.files"
                :key="file.id"
                class="file-row"
              >
                <div class="file-info">
                  <el-icon class="file-type-icon"><Document /></el-icon>
                  <span class="file-name" @click="handlePreview(file)" :title="file.filename">
                    {{ file.filename }}
                  </span>
                </div>
                <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
                <span class="file-time">
                  {{ file.uploaded_at ? formatUploadTime(file.uploaded_at) : '—' }}
                </span>
                <div class="file-actions">
                  <el-button size="small" link type="primary" @click="handleDownload(file)">
                    <el-icon><Download /></el-icon> 下载
                  </el-button>
                  <el-button size="small" link type="danger" @click="handleDeleteFile(file)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </div>
              </div>
            </div>

            <div v-else class="file-empty">
              <div class="table-empty table-empty--compact">
                <el-empty description="暂无文件，拖拽或点击下方区域上传" :image-size="64" />
              </div>
            </div>

            <div class="upload-section">
              <div class="upload-label">上传文件</div>
              <el-upload
                :ref="(el: any) => { if (el) uploadRefs[selectedItem!.item_id] = el }"
                :show-file-list="false"
                :before-upload="(file: File) => handleBeforeUpload(file, selectedItem!.item_id)"
                :disabled="uploadingMap[selectedItem!.item_id]"
                drag
                accept="*"
                class="upload-drag-wrap"
              >
                <div class="upload-zone" :class="{ 'is-uploading': uploadingMap[selectedItem!.item_id] }">
                  <template v-if="!uploadingMap[selectedItem!.item_id] && uploadErrorMap[selectedItem!.item_id]">
                    <el-icon class="upload-icon upload-icon--error"><WarningFilled /></el-icon>
                    <span class="upload-text upload-text--error">{{ uploadErrorMap[selectedItem!.item_id] }}</span>
                    <span class="upload-hint">点击或拖拽重新上传</span>
                  </template>
                  <template v-else-if="!uploadingMap[selectedItem!.item_id]">
                    <el-icon class="upload-icon"><Plus /></el-icon>
                    <span class="upload-text">拖拽文件到此处，或点击上传</span>
                    <span class="upload-hint">支持多文件；上传后可预览、下载或删除</span>
                  </template>
                  <template v-else>
                    <el-icon class="upload-icon is-loading"><Loading /></el-icon>
                    <span class="upload-text">上传中 {{ uploadProgressMap[selectedItem!.item_id] ?? 0 }}%</span>
                    <el-progress
                      :percentage="uploadProgressMap[selectedItem!.item_id] ?? 0"
                      :show-text="false"
                      :stroke-width="6"
                      class="upload-progress"
                    />
                  </template>
                </div>
              </el-upload>
            </div>
          </div>
        </template>

        <div v-else class="no-selection">
          <div class="table-empty">
            <el-empty description="请从左侧选择一个附件子项" :image-size="80" />
          </div>
        </div>
      </div>
    </div>

    <!-- 文件预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      width="88%"
      top="4vh"
      destroy-on-close
      :close-on-click-modal="false"
      class="preview-dialog"
      @closed="onPreviewDialogClosed"
    >
      <template #header>
        <div class="preview-header">
          <div class="preview-header-main">
            <div class="preview-header-icon-wrap">
              <el-icon><Document /></el-icon>
            </div>
            <div class="preview-header-text">
              <div class="preview-filename" :title="previewFile?.filename">
                {{ previewFile?.filename || '文件预览' }}
              </div>
              <div v-if="previewFile" class="preview-meta">
                <span class="preview-meta-chip">{{ previewTypeLabel }}</span>
                <span class="preview-meta-chip">{{ formatFileSize(previewFile.file_size) }}</span>
                <span v-if="previewFile.uploaded_at" class="preview-meta-chip">
                  {{ formatUploadTime(previewFile.uploaded_at) }}
                </span>
              </div>
            </div>
          </div>
          <el-button
            type="primary"
            :icon="Download"
            :disabled="!previewFile"
            @click="previewFile && handleDownload(previewFile)"
          >
            下载
          </el-button>
        </div>
      </template>

      <div v-loading="previewLoading" class="preview-body">
        <div id="preview-container" class="preview-container"></div>
      </div>

      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
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
.header-left {
  min-width: 0;
}
.header-title {
  margin: 0 0 6px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.header-title .el-icon {
  color: var(--primary-color);
  font-size: 20px;
}
.header-sub {
  font-size: 13px;
  color: var(--text-secondary);
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-section {
  background: var(--card-bg);
  border-radius: 8px;
  padding: 24px;
}

.main-panels {
  display: flex;
  gap: 0;
  border-radius: 8px;
  overflow: hidden;
  min-height: 520px;
  background: var(--card-bg);
}

.left-tree {
  width: 300px;
  background: #f8fafc;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.tree-title {
  position: sticky;
  top: 0;
  z-index: 1;
  margin: 0;
  padding: 14px 16px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.tree-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 10px 10px 14px;
}

.tree-category {
  margin-bottom: 8px;
}
.tree-category:last-child {
  margin-bottom: 0;
}
.tree-cat-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  transition: background 0.15s;
  user-select: none;
}
.tree-cat-header:hover {
  background: rgba(15, 23, 42, 0.04);
}
.cat-arrow {
  font-size: 11px;
  color: var(--text-secondary);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.tree-cat-header.collapsed .cat-arrow {
  transform: rotate(-90deg);
}
.cat-icon {
  font-size: 15px;
  color: var(--primary-color);
  flex-shrink: 0;
}
.cat-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cat-count {
  flex-shrink: 0;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: #e2e8f0;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  line-height: 20px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.cat-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 2px;
  padding: 0 0 2px 8px;
  border-left: 1px solid #e2e8f0;
  margin-left: 16px;
}
.tree-item {
  appearance: none;
  border: none;
  background: transparent;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: left;
  transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  position: relative;
}
.tree-item:hover {
  background: rgba(37, 99, 235, 0.06);
  color: var(--text-primary);
}
.tree-item.active {
  background: #ffffff;
  color: var(--primary-color);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.03);
}
.tree-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: var(--primary-color);
}

.item-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #94a3b8;
}
.tree-item.is-confirmed .item-status-dot {
  background: var(--success-color);
}
.tree-item.is-pending .item-status-dot {
  background: var(--warning-color);
}
.tree-item.is-empty .item-status-dot {
  background: #cbd5e1;
}

.item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-file-count {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}
.tree-item.active .item-file-count {
  color: var(--primary-color);
  opacity: 1;
}

.item-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
  flex-shrink: 0;
  line-height: 1.4;
}
.badge-ok {
  background: #ecfdf5;
  color: #059669;
}
.badge-warn {
  background: #fffbeb;
  color: #d97706;
}
.badge-none {
  background: #f1f5f9;
  color: #64748b;
}

.right-panel {
  flex: 1;
  background: var(--card-bg);
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 20px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 1;
}
.item-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  min-width: 0;
}
.item-title :deep(.el-checkbox__label) {
  padding-left: 8px;
}
.item-name-text {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 15px;
}
.item-type-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 4px;
  background: #f1f5f9;
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.item-status {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-count-tag {
  font-size: 12px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.right-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.file-section {
  flex: 1;
  overflow-y: auto;
  padding: 14px 20px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.file-list-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px 150px 128px;
  gap: 12px;
  align-items: center;
  padding: 0 14px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 2px;
}
.file-list-head .col-size,
.file-list-head .col-time,
.file-list-head .col-actions {
  text-align: right;
}
.file-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px 150px 128px;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: #f8fafc;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}
.file-row:hover {
  background: #fff;
  border-color: #e2e8f0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.file-type-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #eff6ff;
  color: var(--primary-color);
  font-size: 16px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.file-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.2s;
  min-width: 0;
}
.file-name:hover {
  color: var(--primary-color);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.file-size,
.file-time {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.file-time {
  opacity: 0.9;
}
.file-actions {
  display: flex;
  justify-content: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.file-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.file-empty,
.no-selection {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.upload-section {
  padding: 12px 20px 20px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
  flex-shrink: 0;
}
.upload-label {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}
.upload-drag-wrap {
  display: block;
}
.upload-drag-wrap :deep(.el-upload) {
  display: block;
}
.upload-drag-wrap :deep(.el-upload-dragger) {
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 22px 16px;
  background: #f8fafc;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
  width: auto;
  height: auto;
}
.upload-drag-wrap :deep(.el-upload-dragger:hover),
.upload-drag-wrap :deep(.el-upload-dragger.is-dragover) {
  border-color: var(--primary-color);
  background: rgba(37, 99, 235, 0.04);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.upload-zone.is-uploading {
  opacity: 0.85;
}
.upload-icon {
  font-size: 28px;
  color: var(--primary-color);
  margin-bottom: 4px;
  opacity: 0.85;
}
.upload-icon--error {
  color: var(--danger-color);
  opacity: 1;
}
.upload-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}
.upload-text--error {
  color: var(--danger-color);
}
.upload-hint {
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.85;
}
.upload-progress {
  width: 80%;
  max-width: 300px;
  margin-top: 12px;
}

@media (max-width: 1100px) {
  .file-list-head,
  .file-row {
    grid-template-columns: minmax(0, 1fr) 72px 110px 112px;
    gap: 8px;
  }
}

.preview-body {
  min-height: 360px;
}
.preview-container {
  overflow: auto;
  max-height: calc(88vh - 180px);
  min-height: 360px;
}

@media (max-width: 900px) {
  .main-panels {
    flex-direction: column;
    min-height: 0;
  }
  .left-tree {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
    max-height: 280px;
  }
}
</style>

<!-- 弹窗 teleport 到 body，需非 scoped -->
<style>
.preview-dialog.el-dialog {
  display: flex;
  flex-direction: column;
  max-height: 92vh;
  margin-bottom: 0;
}
.preview-dialog .el-dialog__header {
  padding: 14px 20px;
  margin-right: 0;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}
.preview-dialog .el-dialog__headerbtn {
  top: 16px;
  right: 16px;
}
.preview-dialog .preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-right: 36px;
  min-width: 0;
}
.preview-dialog .preview-header-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}
.preview-dialog .preview-header-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #eff6ff;
  color: var(--primary-color, #2563eb);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 20px;
}
.preview-dialog .preview-header-text {
  min-width: 0;
  flex: 1;
}
.preview-dialog .preview-filename {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #202e3f);
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-dialog .preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}
.preview-dialog .preview-meta-chip {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: var(--text-secondary, #3f5573);
  font-size: 12px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.preview-dialog .el-dialog__body {
  padding: 0;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: #f1f5f9;
}
.preview-dialog .preview-body {
  height: 100%;
  min-height: 360px;
  max-height: calc(92vh - 140px);
}
.preview-dialog .preview-container {
  height: 100%;
  max-height: calc(92vh - 140px);
  min-height: 360px;
  overflow: auto;
  padding: 16px 20px 20px;
  box-sizing: border-box;
}
.preview-dialog .el-dialog__footer {
  padding: 12px 20px 16px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
  flex-shrink: 0;
}
.preview-dialog .docx-preview {
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.preview-dialog .docx-preview section {
  background: #fff;
  margin-bottom: 16px;
  box-shadow: none;
  padding: 32px 40px;
}
.preview-dialog .preview-container > canvas,
.preview-dialog .preview-container > img {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.preview-dialog .preview-container > pre {
  margin: 0;
  background: #fff !important;
  border: 1px solid #e5e7eb;
  border-radius: 8px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
.preview-dialog .xlsx-tab {
  color: var(--text-secondary, #3f5573);
}
</style>
