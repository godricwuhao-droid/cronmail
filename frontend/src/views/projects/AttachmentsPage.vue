<script setup lang="ts">
/**
 * 项目管理 - 附件管理页
 *
 * 基于通用 AttachmentsPage.vue 适配：
 *  - contract_type 固定为 project
 *  - 路由返回 ProjectDetail
 */
import { computed, onMounted, ref, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { CheckboxValueType } from 'element-plus'
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
  UploadFilled,
} from '@element-plus/icons-vue'
import {
  getAttachments,
  deleteAttachment,
  confirmAttachmentItem,
  unconfirmAttachmentItem,
  type AttachmentCategory,
  type AttachmentFile,
  type AttachmentItem,
} from '@/api/modules/attachment'
import { getProjectContract } from '@/api/modules/project'
import { useGlobalDrop } from '@/composables/useGlobalDrop'

// 文件预览相关依赖
import { renderAsync as renderDocx } from 'docx-preview'
import * as XLSX from 'xlsx'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import { init as initPptxPreview } from 'pptx-preview'

// 配置 pdfjs worker
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
GlobalWorkerOptions.workerSrc = pdfjsWorker

const route = useRoute()
const router = useRouter()

// 项目管理固定使用 project 作为附件 contract_type
const contractType = 'project' as const

/** 从合同详情获取 project_type，用于附件分类过滤 */
const projectType = ref<string | undefined>(undefined)

const contractId = computed(() => route.params.id as string)
const companyCode = computed(() => (route.params.company as string) || 'fengyun')

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

// 上传中状态
const uploadingMap = ref<Record<string, boolean>>({})

async function fetchAttachments() {
  loading.value = true
  const previousSelectedId = selectedItemId.value
  try {
    const res = await getAttachments(contractType, contractId.value, projectType.value)
    categories.value = res.categories
    expandedCategories.value = res.categories.map((c) => c.category_id)
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
  router.push({ name: 'ProjectDetail', params: { company: companyCode.value, id: contractId.value } })
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
const uploadProgressMap = ref<Record<string, number>>({})
const uploadErrorMap = ref<Record<string, string>>({})

function handleBeforeUpload(file: File, itemId: string) {
  handleUpload(file, itemId)
  return false
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
      timeout: 600_000,
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
    setTimeout(() => {
      delete uploadProgressMap.value[itemId]
      delete uploadErrorMap.value[itemId]
    }, 3000)
  }
}

// ============================================================
// 批量上传（全局拖拽用）
// ============================================================
async function uploadFiles(files: File[], itemId: string) {
  for (const file of files) {
    await handleUpload(file, itemId)
  }
  // 批量上传完成后刷新列表
  fetchAttachments()
}

// ============================================================
// 全局拖拽上传
// ============================================================
const { isDragging: isGlobalDragging } = useGlobalDrop({
  accept: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'txt'],
  multiple: true,
  onDrop: (files) => {
    if (!selectedItem.value) {
      ElMessage.warning('请先选择附件分类后再拖入文件')
      return
    }
    uploadFiles(files, selectedItem.value.item_id)
  },
})

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
  try {
    await ElMessageBox.confirm(
      `确定删除文件 "${file.filename}"？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
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

let pdfPreviewObserver: IntersectionObserver | null = null

function getPreviewType(file: AttachmentFile): typeof previewType.value {
  const ext = (file.filename || '').split('.').pop()?.toLowerCase()
  const mime = (file.mime_type || '').toLowerCase()
  if (ext === 'pdf' || mime.includes('pdf')) return 'pdf'
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

    await nextTick()
    const container = document.getElementById('preview-container')
    if (!container) return

    container.innerHTML = ''

    switch (previewType.value) {
      case 'pdf': {
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
            } catch { /* 忽略单页渲染错误 */ }
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

          const sheetsHtml: { name: string; html: string }[] = []
          workbook.SheetNames.forEach((sheetName) => {
            const sheet = workbook.Sheets[sheetName]
            const html = XLSX.utils.sheet_to_html(sheet, {
              id: '',
              editable: false,
            })
            sheetsHtml.push({ name: sheetName, html })
          })

          const tabBar = document.createElement('div')
          tabBar.style.display = 'flex'
          tabBar.style.gap = '4px'
          tabBar.style.marginBottom = '12px'
          tabBar.style.borderBottom = '2px solid #e4e7ed'
          tabBar.style.paddingBottom = '0'

          const sheetContent = document.createElement('div')

          function activateTab(idx: number) {
            tabBar.querySelectorAll('.xlsx-tab').forEach((t, i) => {
              const el = t as HTMLElement
              el.style.color = i === idx ? '#409eff' : '#606266'
              el.style.borderBottom = i === idx ? '2px solid #409eff' : '2px solid transparent'
              el.style.fontWeight = i === idx ? '600' : '400'
            })
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

function onPreviewDialogClosed() {
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

onMounted(async () => {
  // 先获取合同详情以拿到 project_type
  try {
    const contract = await getProjectContract(contractId.value)
    projectType.value = (contract as any).project_type || undefined
  } catch {
    // 获取合同详情失败，project_type 保持 undefined
  }
  fetchAttachments()
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <!-- 顶部返回 -->
    <div class="top-bar">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回详情
      </el-button>
    </div>

    <!-- 标题栏 -->
    <div class="title-bar">
      <div>
        <h1 class="title-text">附件管理</h1>
        <div class="title-sub">项目管理合同</div>
      </div>
      <el-button :icon="Download" @click="handleExportAllAttachments" :disabled="loading">
        一键导出附件
      </el-button>
    </div>

    <!-- 空状态 -->
    <div v-if="categories.length === 0" class="empty-section">
      <el-empty description="暂无附件分类配置，请先在系统配置中配置附件分类" />
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
              <span class="cat-name">{{ cat.category_name }}</span>
              <span class="cat-count">{{ cat.items.reduce((s, it) => s + it.file_count, 0) }} 个文件</span>
            </div>
            <div v-show="isExpanded(cat.category_id)" class="cat-items">
              <div
                v-for="item in cat.items"
                :key="item.item_id"
                class="tree-item"
                :class="{ active: selectedItemId === item.item_id }"
                @click="selectedItemId = item.item_id"
              >
                <el-icon class="item-icon"><Document /></el-icon>
                <span class="item-label">{{ item.item_name }}</span>
                <span v-if="item.confirmed" class="item-badge badge-ok">已确认</span>
                <span v-else-if="item.file_count > 0" class="item-badge badge-warn">未确认</span>
                <span v-else class="item-badge badge-none">未上传</span>
              </div>
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
                ({{ selectedItem.expected_type.toUpperCase() }})
              </span>
            </div>
            <div class="item-status">
              <el-tag :type="itemStatusTagType(selectedItem)" size="small" effect="plain">
                {{ itemStatusText(selectedItem) }}
              </el-tag>
              <span class="file-count-tag">{{ selectedItem.file_count }} 个文件</span>
            </div>
          </div>

          <div class="file-section" v-if="selectedItem.files.length > 0">
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
                <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
                <span v-if="file.uploaded_at" class="file-time">
                  {{ formatUploadTime(file.uploaded_at) }}
                </span>
              </div>
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
            <span class="empty-icon">📭</span>
            <span class="empty-label">暂无文件，拖拽或点击下方区域上传</span>
          </div>

          <div class="upload-section" v-if="selectedItem">
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
                  <el-icon class="upload-icon" style="color: #f56c6c"><WarningFilled /></el-icon>
                  <span class="upload-text" style="color: #f56c6c">{{ uploadErrorMap[selectedItem!.item_id] }}</span>
                </template>
                <template v-else-if="!uploadingMap[selectedItem!.item_id]">
                  <el-icon class="upload-icon"><Plus /></el-icon>
                  <span class="upload-text">拖拽文件到此处 或 点击上传</span>
                </template>
                <template v-else>
                  <el-icon class="upload-icon is-loading"><Loading /></el-icon>
                  <span class="upload-text">上传中 {{ uploadProgressMap[selectedItem!.item_id] ?? 0 }}%</span>
                  <el-progress
                    :percentage="uploadProgressMap[selectedItem!.item_id] ?? 0"
                    :show-text="false"
                    :stroke-width="6"
                    style="width: 80%; max-width: 300px; margin-top: 12px"
                  />
                </template>
              </div>
            </el-upload>
          </div>
        </template>

        <div v-else class="no-selection">
          <span class="no-select-icon">📂</span>
          <span>请从左侧选择一个附件子项</span>
        </div>
      </div>
    </div>

    <!-- 文件预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewFile?.filename || '文件预览'"
      width="85%"
      top="3vh"
      destroy-on-close
      :close-on-click-modal="false"
      class="preview-dialog"
      @closed="onPreviewDialogClosed"
    >
      <div v-if="previewFile" style="text-align:right;margin-bottom:12px;">
        <el-button size="small" type="primary" @click="handleDownload(previewFile)">
          <el-icon><Download /></el-icon> 下载
        </el-button>
      </div>
      <div v-loading="previewLoading" style="min-height:300px;">
        <div id="preview-container" style="overflow:auto;max-height:70vh;"></div>
      </div>
    </el-dialog>

    <!-- 全局拖拽上传遮罩 -->
    <Teleport to="body">
      <div v-if="isGlobalDragging" class="global-drop-overlay">
        <div class="global-drop-box">
          <el-icon :size="48"><UploadFilled /></el-icon>
          <p>释放文件以上传到「{{ selectedItem?.item_name || '请先选择附件分类' }}」</p>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ====== 顶部 ====== */
.top-bar { margin-bottom: 16px; }

/* ====== 标题栏 ====== */
.title-bar {
  background: #fff; border-radius: 10px; padding: 18px 24px; margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
  display: flex; align-items: center; justify-content: space-between;
}
.title-text { font-size: 20px; font-weight: 600; margin: 0; }
.title-sub { font-size: 13px; color: #909399; margin-top: 4px; }

/* ====== 空态 ====== */
.empty-section {
  background: #fff; border-radius: 10px; padding: 60px 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}

/* ====== 双栏主体 ====== */
.main-panels {
  display: flex; gap: 0; border-radius: 10px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.06); min-height: 520px;
}

/* ---- 左侧树 ---- */
.left-tree {
  width: 280px; background: #fff; border-right: 1px solid #e4e7ed;
  display: flex; flex-direction: column; flex-shrink: 0;
}
.tree-title {
  padding: 16px 18px 12px; font-size: 13px; color: #909399;
  font-weight: 600; letter-spacing: .5px;
}
.tree-scroll { flex: 1; overflow-y: auto; padding: 0 8px 12px; }

.tree-category { margin-bottom: 2px; }
.tree-cat-header {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px; border-radius: 6px; cursor: pointer;
  font-size: 13px; font-weight: 600; color: #303133; transition: background .15s;
}
.tree-cat-header:hover { background: #f5f7fa; }
.cat-arrow { font-size: 10px; color: #909399; transition: transform .2s; flex-shrink: 0; }
.tree-cat-header.collapsed .cat-arrow { transform: rotate(-90deg); }
.cat-icon { font-size: 15px; color: #e6a23c; }
.cat-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cat-count { font-size: 11px; color: #c0c4cc; margin-left: auto; flex-shrink: 0; }

.cat-items { padding-left: 4px; }
.tree-item {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px 7px 28px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: #606266; transition: all .15s;
}
.tree-item:hover { background: #f0f5ff; color: #409eff; }
.tree-item.active { background: #ecf5ff; color: #409eff; font-weight: 600; }
.item-icon { font-size: 14px; flex-shrink: 0; }
.item-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.item-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 500; flex-shrink: 0;
}
.badge-ok { background: #e1f3d8; color: #67c23a; }
.badge-warn { background: #faecd8; color: #e6a23c; }
.badge-none { background: #f4f4f5; color: #909399; }

/* ---- 右侧面板 ---- */
.right-panel {
  flex: 1; background: #fff; display: flex; flex-direction: column; min-width: 0;
}

.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; border-bottom: 1px solid #ebeef5; flex-shrink: 0;
}
.item-title { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; }
.item-name-text { font-weight: 600; }
.item-type-badge { font-size: 12px; color: #6b7280; font-weight: 700; }
.item-status { display: flex; align-items: center; gap: 8px; }
.file-count-tag { font-size: 12px; color: #909399; }

/* 文件列表 */
.file-section { flex: 1; overflow-y: auto; padding: 12px 24px; }
.file-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 12px; border-radius: 6px; transition: background .15s;
}
.file-row:hover { background: #f5f7fa; }
.file-info { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.file-type-icon { font-size: 18px; color: #909399; flex-shrink: 0; }
.file-name {
  font-size: 13px; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  cursor: pointer; transition: color .2s; flex: 1;
}
.file-name:hover { color: #409eff; text-decoration: underline; }
.file-size { font-size: 12px; color: #909399; white-space: nowrap; min-width: 60px; text-align: right; }
.file-time { font-size: 11px; color: #c0c4cc; white-space: nowrap; min-width: 130px; text-align: right; }
.file-actions { display: flex; gap: 6px; margin-left: 12px; flex-shrink: 0; }

/* 无文件空态 */
.file-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; color: #c0c4cc; gap: 8px;
}
.empty-icon { font-size: 40px; }
.empty-label { font-size: 14px; }

/* 未选中 */
.no-selection {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; color: #c0c4cc; gap: 8px;
}
.no-select-icon { font-size: 40px; }

/* 上传区 */
.upload-section {
  padding: 12px 24px 20px; border-top: 1px solid #ebeef5;
  background: #fafbfc; flex-shrink: 0;
}
.upload-drag-wrap { display: block; }
.upload-drag-wrap :deep(.el-upload) { display: block; }
.upload-drag-wrap :deep(.el-upload-dragger) {
  border: 2px dashed #dcdfe6; border-radius: 8px; padding: 24px;
  background: #fafbfc; transition: border-color .25s, background .25s;
  width: auto; height: auto;
}
.upload-drag-wrap :deep(.el-upload-dragger:hover) {
  border-color: #409eff; background: #f0f5ff;
}
.upload-drag-wrap :deep(.el-upload-dragger.is-dragover) {
  border-color: #409eff; background: #f0f5ff;
}
.upload-zone {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 6px;
}
.upload-zone.is-uploading { opacity: .7; }
.upload-icon { font-size: 32px; color: #8c939d; }
.upload-text { font-size: 13px; color: #909399; }

/* 预览弹窗 */
.preview-dialog :deep(.el-dialog__body) { padding: 12px 24px 24px; }
.docx-preview { padding: 20px; background: #fff; }
.docx-preview section { background: #fff; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); padding: 40px; }

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
</style>
