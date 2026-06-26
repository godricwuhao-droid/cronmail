<script setup lang="ts">
/**
 * 邮件模板 - 编辑 / 新建页
 *
 * 布局：左右分栏
 *   - 左：主题 + Monaco Editor（HTML+Jinja2）+ 富文本签名 + 示例数据 JSON
 *   - 右：iframe 实时预览（防抖 800ms 自动调用 preview 接口）+ 变量参考面板
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import {
  EditPen,
  Document,
  DataAnalysis,
  View,
  Postcard,
  Promotion,
} from '@element-plus/icons-vue'
import * as monaco from 'monaco-editor'
// 配置 monaco worker（Vite 友好做法）
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'

// 设置 MonacoEnvironment（Vite + monaco-editor 标准做法）
self.MonacoEnvironment = {
  getWorker(_: string, label: string) {
    if (label === 'json') return new jsonWorker()
    if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker()
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker()
    if (label === 'typescript' || label === 'javascript') return new tsWorker()
    return new editorWorker()
  },
}

import {
  createTemplate,
  getTemplate,
  getTemplateVariables,
  previewTemplate,
  testSendTemplate,
  updateTemplate,
  type TemplateCreatePayload,
  type TemplateDetail,
  type TemplateTestSendResponse,
  type TriggerType,
  type TemplateVariableItem,
} from '@/api/modules/template'
import {
  getContacts,
  type Contact,
  type ContactListResponse,
} from '@/api/modules/contact'
import { getRental, getRentals } from '@/api/modules/rental'
import { DEFAULT_TEMPLATE_SAMPLE, TRIGGER_TYPE_LABEL } from '@/lib/template'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const templateId = computed(() => (route.params.id as string) || '')

// ============================================================
// 表单
// ============================================================
const form = reactive<TemplateCreatePayload>({
  name: '',
  trigger_type: 'provision' as TriggerType,
  subject_tpl: '',
  body_html: '',
  variables_desc: {},
  signature_html: '',
  is_active: true,
})

const sampleDataText = ref<string>(JSON.stringify(DEFAULT_TEMPLATE_SAMPLE, null, 2))
const sampleDataError = ref<string>('')

const TRIGGER_OPTIONS: Array<{ label: string; value: TriggerType }> = [
  { label: TRIGGER_TYPE_LABEL.provision, value: 'provision' },
  { label: TRIGGER_TYPE_LABEL.expiry_warning, value: 'expiry_warning' },
  { label: TRIGGER_TYPE_LABEL.reclaim, value: 'reclaim' },
]

// ============================================================
// Monaco Editor（正文）
// ============================================================
const editorContainer = ref<HTMLElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let suppressChange = false

// ============================================================
// 富文本签名编辑器（contenteditable）
// ============================================================
const signatureEditorRef = ref<HTMLDivElement | null>(null)

function initEditor() {
  if (!editorContainer.value) return
  editor = monaco.editor.create(editorContainer.value, {
    value: form.body_html,
    language: 'html',
    theme: 'vs',
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 13,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    tabSize: 2,
  })

  editor.onDidChangeModelContent(() => {
    if (suppressChange) return
    form.body_html = editor!.getValue()
    schedulePreview()
  })
}

function onSignatureInput() {
  if (signatureEditorRef.value) {
    form.signature_html = signatureEditorRef.value.innerHTML
  }
}

function onSignaturePaste(_e: ClipboardEvent) {
  // 允许浏览器默认粘贴行为（含图片和 HTML 格式）
  // setTimeout 等 DOM 更新后再同步到 form
  setTimeout(() => {
    if (signatureEditorRef.value) {
      form.signature_html = signatureEditorRef.value.innerHTML
    }
  }, 10)
}

/** 加载/同步已有签名到富文本编辑器 */
function setSignatureContent(html: string) {
  if (signatureEditorRef.value) {
    signatureEditorRef.value.innerHTML = html || ''
  }
}

function setEditorValue(v: string) {
  if (!editor) return
  if (editor.getValue() === v) return
  suppressChange = true
  editor.setValue(v)
  suppressChange = false
}

// ============================================================
// 变量参考面板
// ============================================================
const availableVariables = ref<TemplateVariableItem[]>([])

async function loadVariables() {
  try {
    const res = await getTemplateVariables()
    availableVariables.value = res.variables || []
  } catch {
    // 静默失败：变量参考面板空状态不影响主功能
    availableVariables.value = []
  }
}

/** 把变量字段名格式化为 {{ field }} 显示文本 */
function formatVariableTag(field: string): string {
  return `{{ ${field} }}`
}

/** 点击变量标签，插入到 Monaco Editor 当前光标位置 */
function insertVariable(field: string) {
  if (!editor) return
  const text = `{{ ${field} }}`
  const position = editor.getPosition()
  if (position) {
    // 使用 monaco 全局命名空间构造 Range（保留原有 import * as monaco from 'monaco-editor' 的命名空间）
    editor.executeEdits('insert-variable', [
      {
        range: new monaco.Range(
          position.lineNumber,
          position.column,
          position.lineNumber,
          position.column,
        ),
        text,
        forceMoveMarkers: true,
      },
    ])
  }
  editor.focus()
}

// ============================================================
// 预览
// ============================================================
const previewLoading = ref(false)
const renderedSubject = ref('')
const renderedBody = ref('')
const previewFrameRef = ref<HTMLIFrameElement | null>(null)

let previewTimer: ReturnType<typeof setTimeout> | null = null
function schedulePreview() {
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    refreshPreview()
  }, 800)
}

function buildIframeHtml(body: string, subject: string) {
  // 用一个简单的全屏 HTML 文档包裹预览
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>${escapeHtml(subject)}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; padding: 24px; color: #303133; line-height: 1.6; }
  h1, h2, h3 { color: #303133; }
  table { border-collapse: collapse; }
  </style>
</head>
<body>
${body}
</body>
</html>`
}

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function getSampleData(): Record<string, unknown> | null {
  sampleDataError.value = ''
  try {
    const parsed = JSON.parse(sampleDataText.value)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      sampleDataError.value = '示例数据必须是 JSON 对象'
      return null
    }
    return parsed as Record<string, unknown>
  } catch (e: any) {
    sampleDataError.value = `JSON 解析失败: ${e?.message || e}`
    return null
  }
}

async function refreshPreview() {
  const sample = getSampleData()
  // 拼接签名到 body 后端（前端拼接），同时把 signature_html 也传给后端
  // - 后端预览接口已支持 signature_html 字段，会自动拼到 body 末尾
  // - 前端这里也拼接一次，避免双重拼接：只传 body_html（已含签名），signature_html 不传
  const bodyWithSig = form.body_html + (form.signature_html ? `\n${form.signature_html}` : '')

  if (!sample) {
    // 解析失败时，本地简单替换 {{ var }} 做一个降级渲染
    renderedSubject.value = form.subject_tpl.replace(/{{\s*([\w.]+)\s*}}/g, '（$1）')
    renderedBody.value = bodyWithSig.replace(/{{\s*([\w.]+)\s*}}/g, '（$1）')
    applyIframe()
    return
  }
  previewLoading.value = true
  try {
    const res = await previewTemplate({
      subject_tpl: form.subject_tpl,
      body_html: bodyWithSig,
      sample_data: sample,
    })
    renderedSubject.value = res.subject_rendered
    renderedBody.value = res.body_rendered
  } catch (e) {
    // 错误已统一处理
    renderedSubject.value = form.subject_tpl
    renderedBody.value = bodyWithSig
  } finally {
    previewLoading.value = false
    applyIframe()
  }
}

function applyIframe() {
  if (previewFrameRef.value) {
    const html = buildIframeHtml(renderedBody.value || '<p style="color:#909399">（暂无内容）</p>', renderedSubject.value)
    previewFrameRef.value.srcdoc = html
  }
}

// ============================================================
// 加载详情（编辑模式）
// ============================================================
const loadingDetail = ref(false)
const detail = ref<TemplateDetail | null>(null)

async function loadDetail() {
  if (!templateId.value) return
  loadingDetail.value = true
  try {
    const data = await getTemplate(templateId.value)
    detail.value = data
    form.name = data.name
    form.trigger_type = data.trigger_type
    form.subject_tpl = data.subject_tpl
    form.body_html = data.body_html
    form.variables_desc = data.variables_desc || {}
    form.signature_html = data.signature_html || ''
    form.is_active = data.is_active
    setEditorValue(data.body_html)
    setSignatureContent(data.signature_html || '')
    await nextTick()
    refreshPreview()
  } catch (e) {
    // 错误已统一处理
  } finally {
    loadingDetail.value = false
  }
}

// ============================================================
// 监听表单变化自动刷新预览
// ============================================================
watch(
  () => form.subject_tpl,
  () => schedulePreview(),
)
watch(
  () => sampleDataText.value,
  () => schedulePreview(),
)

// ============================================================
// 保存
// ============================================================
const formRef = ref<FormInstance>()
const submitting = ref(false)

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.error('请输入模板名称')
    return
  }
  if (!form.subject_tpl.trim()) {
    ElMessage.error('请输入主题模板')
    return
  }
  // 同步当前编辑器内容
  if (editor) form.body_html = editor.getValue()
  if (!form.body_html.trim()) {
    ElMessage.error('请输入正文模板')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateTemplate(templateId.value, form)
      ElMessage.success('已保存')
    } else {
      const created = await createTemplate(form)
      ElMessage.success('已创建')
      // 切换到编辑模式停留在当前页
      router.replace({ name: 'TemplateEdit', params: { id: created.id } })
      detail.value = created
    }
  } catch (e) {
    // 错误已统一处理
  } finally {
    submitting.value = false
  }
}

function handleToggleActive() {
  form.is_active = !form.is_active
  ElMessage.info(form.is_active ? '已切换为启用（记得保存）' : '已切换为停用（记得保存）')
}

function goBack() {
  router.push({ name: 'TemplateList' })
}

function resetSample() {
  sampleDataText.value = JSON.stringify(DEFAULT_TEMPLATE_SAMPLE, null, 2)
  sampleDataError.value = ''
  schedulePreview()
}

// ============================================================
// 测试发送弹窗
// ============================================================
interface ContactOption {
  id: string
  name: string
  email: string
  group: '客户联系人' | '内部同事'
}

const testSendVisible = ref(false)
const contactsLoading = ref(false)
const contactOptions = ref<ContactOption[]>([])
const toContactIds = ref<string[]>([])
const ccContactIds = ref<string[]>([])

/** 测试发送：选中的租赁记录 id（用于生成 sample_data） */
const rentalId = ref<string>('')

/** 测试发送：租赁记录下拉选项 */
interface RentalOption {
  id: string
  customer?: { id: string; name: string } | null
  machine_model?: string
  private_ip?: string | null
}
const rentalOptions = ref<RentalOption[]>([])

/** 测试发送：选中的租赁记录映射出来的 sample_data（直接传给后端） */
const sampleData = reactive<Record<string, unknown>>({})

/** 测试发送结果 */
const testResult = ref<TemplateTestSendResponse | null>(null)
const testSubmitting = ref(false)

/** 是否正在拉取租赁详情（loading 状态） */
const rentalDetailLoading = ref(false)

async function fetchAllContacts(): Promise<ContactListResponse[]> {
  // 并行拉取：客户联系人（全部）+ 内部同事（全部）
  return Promise.all([
    getContacts({ type: 'customer', all: true }),
    getContacts({ type: 'colleague' }),
  ])
}

function buildContactOptions(list: ContactListResponse[]): ContactOption[] {
  const [customerRes, colleagueRes] = list
  const customers: ContactOption[] = (customerRes?.items || []).map((c: Contact) => ({
    id: c.id,
    name: c.name,
    email: c.email,
    group: '客户联系人',
  }))
  const colleagues: ContactOption[] = (colleagueRes?.items || []).map((c: Contact) => ({
    id: c.id,
    name: c.name,
    email: c.email,
    group: '内部同事',
  }))
  return [...customers, ...colleagues]
}

function contactLabel(opt: ContactOption): string {
  return `${opt.name} <${opt.email}>`
}

async function loadRentalOptions() {
  try {
    const res = await getRentals({ page: 1, page_size: 100 })
    // 兼容两种返回形态：直接 items 或包在 data 中
    rentalOptions.value =
      ((res as any)?.items as RentalOption[]) ||
      ((res as any)?.data?.items as RentalOption[]) ||
      []
  } catch {
    rentalOptions.value = []
  }
}

async function onRentalChange(val: string | number | undefined) {
  const rentalIdValue = val == null ? '' : String(val)
  rentalId.value = rentalIdValue
  // 清空当前 sample_data
  Object.keys(sampleData).forEach((k) => delete sampleData[k])

  if (!rentalIdValue) return

  rentalDetailLoading.value = true
  try {
    const res = await getRental(rentalIdValue)
    const detail: any = (res as any)?.data || res || {}
    // 把详情字段映射为 sample_data
    Object.assign(sampleData, {
      customer_name: detail.customer?.name || '',
      machine_model: detail.machine_model || '',
      cpu_model: detail.cpu_model || '',
      memory_gb: detail.memory_gb || '',
      gpu_info: detail.gpu_info || '',
      system_disk_gb: detail.system_disk_gb || '',
      data_disks: detail.data_disks || [],
      os_version: detail.os_version || '',
      bandwidth_mbps: detail.bandwidth_mbps || '',
      rack_location: detail.rack_location || '',
      private_ip: detail.private_ip || '',
      public_ips: detail.public_ips || [],
      ssh_port: detail.ssh_port || '',
      root_username: detail.root_username || '',
      root_password: detail.root_password || '',
      billing_model: detail.billing_model || '',
      start_date: detail.start_date || '',
      end_date: detail.end_date || '',
      remark: detail.remark || '',
    })
  } catch (e) {
    ElMessage.error('获取租赁详情失败')
  } finally {
    rentalDetailLoading.value = false
  }
}

async function openTestSendDialog() {
  if (!isEdit.value) {
    ElMessage.warning('请先保存模板后再测试发送')
    return
  }
  // 同步当前编辑器最新内容
  if (editor) form.body_html = editor.getValue()
  if (signatureEditorRef.value) form.signature_html = signatureEditorRef.value.innerHTML

  testResult.value = null
  toContactIds.value = []
  ccContactIds.value = []
  rentalId.value = ''
  Object.keys(sampleData).forEach((k) => delete sampleData[k])
  testSendVisible.value = true

  // 并行拉取：联系人 + 租赁记录下拉
  contactsLoading.value = true
  try {
    const [contactList] = await Promise.all([fetchAllContacts(), loadRentalOptions()])
    contactOptions.value = buildContactOptions(contactList)
  } catch (e) {
    // 错误已统一处理
  } finally {
    contactsLoading.value = false
  }
}

async function handleTestSend() {
  if (!templateId.value) return
  if (toContactIds.value.length === 0) {
    ElMessage.error('请至少选择一位收件人')
    return
  }

  testSubmitting.value = true
  try {
    const res = await testSendTemplate(templateId.value, {
      to_contact_ids: toContactIds.value,
      cc_contact_ids: ccContactIds.value,
      sample_data: sampleData,
    })
    testResult.value = res
    if (res.success) {
      ElMessage.success(res.message || '测试发送成功')
    } else {
      ElMessage.warning(res.message || '测试发送失败')
    }
  } catch (e) {
    // 错误已统一处理
  } finally {
    testSubmitting.value = false
  }
}

function closeTestSendDialog() {
  testSendVisible.value = false
  testResult.value = null
}

onMounted(async () => {
  await nextTick()
  initEditor()
  if (isEdit.value) {
    await loadDetail()
  } else {
    // 新建模式：填一个简单示例
    form.subject_tpl = '【CronMail】您的服务器 {{ machine_model }} 已开通'
    form.body_html = `<h2>尊敬的 {{ customer_name }}：</h2>
<p>您租赁的服务器已就绪，请查收以下信息：</p>
<table border="1" cellspacing="0" cellpadding="6">
  <tr><th>机器型号</th><td>{{ machine_model }}</td></tr>
  <tr><th>CPU</th><td>{{ cpu_model }}</td></tr>
  <tr><th>内存</th><td>{{ memory_gb }} GB</td></tr>
  <tr><th>系统盘</th><td>{{ system_disk_gb }} GB</td></tr>
  <tr><th>操作系统</th><td>{{ os_version }}</td></tr>
  <tr><th>内网IP</th><td>{{ private_ip }}</td></tr>
  <tr><th>SSH 端口</th><td>{{ ssh_port }}</td></tr>
  <tr><th>root</th><td>{{ root_username }} / {{ root_password }}</td></tr>
  <tr><th>服务期</th><td>{{ start_date }} ~ {{ end_date }}</td></tr>
</table>
<p>如有疑问，请联系运维。</p>`
    form.signature_html = `<p style="color:#999; font-size:12px; margin-top:24px;">
  --<br/>
  CronMail 自动发送<br/>
  如有疑问请联系运维团队
</p>`
    setEditorValue(form.body_html)
    setSignatureContent(form.signature_html)
    await nextTick()
    refreshPreview()
  }
  // 加载变量参考（无论新建/编辑都可显示）
  loadVariables()
})

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
    editor = null
  }
  if (previewTimer) clearTimeout(previewTimer)
})
</script>

<template>
  <div class="page-container" v-loading="loadingDetail">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><EditPen /></el-icon>
            {{ isEdit ? '编辑邮件模板' : '新建邮件模板' }}
          </span>
          <el-button link @click="goBack">返回</el-button>
        </div>
      </template>

      <!-- 顶部元数据 -->
      <el-form
        ref="formRef"
        :model="form"
        label-width="100px"
        class="meta-form"
        @submit.prevent
      >
        <el-row :gutter="16">
          <el-col :span="10">
            <el-form-item label="模板名称">
              <el-input v-model="form.name" placeholder="如 资源开通通知" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="触发类型">
              <el-select v-model="form.trigger_type" style="width: 100%">
                <el-option
                  v-for="opt in TRIGGER_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="启用状态">
              <el-switch
                v-model="form.is_active"
                active-text="启用"
                inactive-text="停用"
                inline-prompt
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="主题模板">
          <el-input
            v-model="form.subject_tpl"
            placeholder="支持 {{ variable }} 变量"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <!-- 左右分栏：编辑器 + 预览 -->
      <div class="editor-layout">
        <!-- 左侧 -->
        <div class="editor-pane">
          <div class="pane-title">
            <el-icon><Document /></el-icon>
            正文模板 (HTML + Jinja2 变量)
          </div>
          <div ref="editorContainer" class="monaco-container"></div>

          <div class="pane-title" style="margin-top: 16px">
            <el-icon><Postcard /></el-icon>
            邮件签名（HTML，渲染时自动拼接在正文末尾）
          </div>
          <el-card shadow="never" class="signature-card">
            <template #header>
              <div class="signature-card-header">
                <span style="font-weight: 600;">邮件签名</span>
                <span style="font-size: 12px; color: #9ca3af; margin-left: 8px;">
                  支持从 Outlook / 网页邮箱粘贴签名（含图片和格式）
                </span>
              </div>
            </template>
            <div
              ref="signatureEditorRef"
              contenteditable="true"
              class="rich-signature-editor"
              @input="onSignatureInput"
              @paste="onSignaturePaste"
            ></div>
          </el-card>

          <div class="pane-title" style="margin-top: 16px">
            <el-icon><DataAnalysis /></el-icon>
            示例数据 (JSON)
          </div>
          <el-input
            v-model="sampleDataText"
            type="textarea"
            :rows="10"
            :class="{ 'is-error': !!sampleDataError }"
            spellcheck="false"
            placeholder='示例: {"machine_model": "Dell R740", "private_ip": "10.0.0.1"}'
          />
          <div v-if="sampleDataError" class="err-msg">{{ sampleDataError }}</div>
          <div class="sample-actions">
            <el-button size="small" @click="resetSample">重置示例</el-button>
            <el-button size="small" type="primary" @click="refreshPreview">
              刷新预览
            </el-button>
          </div>
        </div>

        <!-- 右侧 -->
        <div class="preview-pane">
          <div class="pane-title">
            <el-icon><View /></el-icon>
            实时预览
            <span v-if="previewLoading" class="preview-loading">渲染中…</span>
          </div>
          <div class="preview-subject" v-if="renderedSubject">
            <span class="lbl">主题：</span>{{ renderedSubject }}
          </div>
          <iframe ref="previewFrameRef" class="preview-frame" sandbox="allow-same-origin"></iframe>
        </div>
      </div>

      <!-- 变量参考（编辑器/预览区下方） -->
      <el-card shadow="never" class="variable-card">
        <template #header>
          <div class="variable-card-header">
            <span style="font-weight: 600;">可用模板变量</span>
            <el-tag size="small" type="info">自动同步后端字段</el-tag>
          </div>
        </template>
        <div v-if="availableVariables.length === 0" class="variable-empty">
          暂无可用变量
        </div>
        <div v-else class="variable-grid">
          <div
            v-for="v in availableVariables"
            :key="v.field"
            class="variable-chip"
            :title="`点击插入 {{ ${v.field} }}`"
            @click="insertVariable(v.field)"
          >
            <code>{{ formatVariableTag(v.field) }}</code>
            <span class="var-label">{{ v.label }}</span>
            <span class="var-type">{{ v.type }}</span>
          </div>
        </div>
      </el-card>

      <!-- 底部操作 -->
      <div class="footer-actions">
        <el-button @click="goBack">取消</el-button>
        <div class="spacer" />
        <el-button
          type="success"
          :icon="Promotion"
          :disabled="!isEdit"
          @click="openTestSendDialog"
        >
          测试发送
        </el-button>
        <el-button @click="handleToggleActive">
          {{ form.is_active ? '停用' : '启用' }}
        </el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">
          保存
        </el-button>
      </div>
    </el-card>

    <!-- 测试发送弹窗 -->
    <el-dialog
      v-model="testSendVisible"
      title="测试发送邮件"
      width="720px"
      :close-on-click-modal="false"
      @close="closeTestSendDialog"
    >
      <el-form label-width="100px" @submit.prevent>
        <el-form-item label="收件人" required>
          <el-select
            v-model="toContactIds"
            multiple
            filterable
            remote
            reserve-keyword
            placeholder="搜索联系人姓名或邮箱…"
            style="width: 100%"
            :loading="contactsLoading"
            :max-collapse-tags="3"
            collapse-tags
            collapse-tags-tooltip
          >
            <el-option-group
              v-for="group in ['客户联系人', '内部同事']"
              :key="group"
              :label="group"
            >
              <el-option
                v-for="opt in contactOptions.filter((o) => o.group === group)"
                :key="opt.id"
                :value="opt.id"
                :label="contactLabel(opt)"
              />
            </el-option-group>
          </el-select>
        </el-form-item>

        <el-form-item label="抄送">
          <el-select
            v-model="ccContactIds"
            multiple
            filterable
            remote
            reserve-keyword
            placeholder="搜索联系人姓名或邮箱…"
            style="width: 100%"
            :loading="contactsLoading"
            :max-collapse-tags="3"
            collapse-tags
            collapse-tags-tooltip
          >
            <el-option-group
              v-for="group in ['客户联系人', '内部同事']"
              :key="group"
              :label="group"
            >
              <el-option
                v-for="opt in contactOptions.filter((o) => o.group === group)"
                :key="opt.id"
                :value="opt.id"
                :label="contactLabel(opt)"
              />
            </el-option-group>
          </el-select>
        </el-form-item>

        <el-form-item label="选择租赁记录">
          <el-select
            v-model="rentalId"
            filterable
            placeholder="选择一条租赁记录作为测试数据（不选则用模板默认变量）"
            style="width: 100%"
            :loading="rentalDetailLoading"
            clearable
            @change="onRentalChange"
          >
            <el-option
              v-for="r in rentalOptions"
              :key="r.id"
              :label="`${r.customer?.name || ''} - ${r.machine_model || ''} (${r.private_ip || ''})`"
              :value="r.id"
            />
          </el-select>
          <div class="form-hint">
            选中的租赁记录详情会作为模板变量传入。
            <span v-if="rentalId" style="color: var(--primary-color)">
              已选 <strong>{{ Object.keys(sampleData).length }}</strong> 个字段
            </span>
          </div>
        </el-form-item>
      </el-form>

      <!-- 发送结果 -->
      <div v-if="testResult" class="test-result" :class="testResult.success ? 'ok' : 'fail'">
        <div class="result-header">
          <el-tag :type="testResult.success ? 'success' : 'danger'" effect="dark" size="small">
            {{ testResult.success ? '发送成功' : '发送失败' }}
          </el-tag>
          <span class="result-msg">{{ testResult.message }}</span>
        </div>
        <div class="result-row">
          <span class="lbl">主题：</span>{{ testResult.subject_rendered }}
        </div>
        <div class="result-row">
          <span class="lbl">收件人：</span>{{ testResult.to_emails.join(', ') || '（无）' }}
        </div>
        <div v-if="testResult.cc_emails.length" class="result-row">
          <span class="lbl">抄送：</span>{{ testResult.cc_emails.join(', ') }}
        </div>
      </div>

      <template #footer>
        <el-button @click="closeTestSendDialog">关闭</el-button>
        <el-button
          type="primary"
          :loading="testSubmitting"
          :disabled="toContactIds.length === 0"
          @click="handleTestSend"
        >
          发送测试邮件
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-header .title {
  font-size: 16px;
  font-weight: 600;
}
.meta-form {
  max-width: 100%;
}
.editor-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
  min-height: 600px;
}
.editor-pane,
.preview-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.pane-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pane-title .el-icon {
  color: var(--primary-color);
  font-size: 15px;
}
.preview-loading {
  font-weight: normal;
  color: #909399;
  font-size: 12px;
}
.monaco-container {
  width: 100%;
  height: 380px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}
.signature-card {
  margin-bottom: 0;
}
.signature-card :deep(.el-card__body) {
  padding: 12px;
}
.signature-card-header {
  display: flex;
  align-items: center;
}
.rich-signature-editor {
  min-height: 140px;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
  outline: none;
  transition: border-color 0.2s;
  background: #fff;
}
.rich-signature-editor:focus {
  border-color: #1e40af;
}
.rich-signature-editor img {
  max-width: 100%;
  height: auto;
}
.is-error :deep(textarea) {
  border-color: #f56c6c;
}
.err-msg {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
}
.sample-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
.preview-subject {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px 12px;
  margin-bottom: 8px;
  font-size: 13px;
}
.preview-subject .lbl {
  color: #909399;
  margin-right: 4px;
}
.preview-frame {
  flex: 1;
  width: 100%;
  min-height: 380px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
}
.variable-card {
  margin-top: 16px;
  border-radius: 12px;
}
.variable-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.variable-empty {
  font-size: 13px;
  color: #9ca3af;
  padding: 8px 4px;
}
.variable-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.variable-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
  user-select: none;
}
.variable-chip:hover {
  border-color: #1e40af;
  background: #eff6ff;
}
.variable-chip code {
  background: #fef3c7;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  white-space: nowrap;
  color: #92400e;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
.var-label {
  color: #374151;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.var-type {
  color: #9ca3af;
  font-size: 11px;
  text-transform: uppercase;
  flex-shrink: 0;
}
@media (max-width: 700px) {
  .variable-grid {
    grid-template-columns: 1fr;
  }
}
.footer-actions {
  display: flex;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
.spacer {
  flex: 1;
}
@media (max-width: 1100px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
.form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 4px;
}
.test-result {
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 4px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
}
.test-result.ok {
  background: #f0f9eb;
  border-color: #e1f3d8;
}
.test-result.fail {
  background: #fef0f0;
  border-color: #fde2e2;
}
.test-result .result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.test-result .result-msg {
  font-size: 13px;
  color: var(--text-primary);
}
.test-result .result-row {
  font-size: 12px;
  line-height: 1.7;
  color: #606266;
  word-break: break-all;
}
.test-result .lbl {
  color: #909399;
  margin-right: 4px;
}
</style>
