<script setup lang="ts">
/**
 * 租赁记录 - 详情页（对齐合同详情页风格）
 *
 * 设计要点：
 *  - 顶部 header：设备型号 + 客户 + 状态 tag + 操作按钮
 *  - 基本信息卡片：el-descriptions :column="3" border
 *  - 硬件配置卡片：el-descriptions :column="3" border
 *  - 存储与网络卡片：el-descriptions :column="3" border
 *  - 登录凭证卡片
 *  - 关联合同信息卡片（已有）

 *  - 变更记录按钮
 */
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, View, Hide } from '@element-plus/icons-vue'
import {
  getRental,
} from '@/api/modules/rental'
import {
  listChangeLogs,
  createChangeLog,
  type ChangeLogEntry,
} from '@/api/modules/contract'
import { safeStatusLabel, safeStatusTagType } from '@/lib/rental'
import { parseChangeContent, formatChangeValue } from '@/lib/change-log'

const route = useRoute()
const router = useRouter()

const record = ref<any>({})
const loading = ref(false)
const showPassword = ref(false)

// === 拉取详情 ===
async function fetchRecord() {
  loading.value = true
  try {
    const res = await getRental(route.params.id as string)
    record.value = (res as any)?.data ?? res
  } catch {
    // 错误已由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

// === 操作按钮 ===
function handleEdit() {
  router.push(`/rentals/${route.params.id}/edit`)
}

function goBack() {
  router.push({ name: 'RentalList' })
}

// === 展示辅助函数 ===
function statusTagType(s?: string) {
  return safeStatusTagType(s)
}
function statusLabel(s?: string) {
  return safeStatusLabel(s)
}
function billingLabel(s?: string) {
  const m: Record<string, string> = {
    monthly: '按月',
    quarterly: '按季',
    yearly: '按年',
    custom: '自定义',
  }
  return m[s || ''] || s || '-'
}
function formatBandwidth(mbps?: number | null) {
  if (mbps == null) return '-'
  return mbps >= 1000 ? `${(mbps / 1000).toFixed(1)} Gbps` : `${mbps} Mbps`
}
function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}
function isExpiring(date?: string | null) {
  if (!date) return false
  const d = new Date(date).getTime()
  const now = Date.now()
  const diff = d - now
  return diff > 0 && diff <= 3 * 24 * 60 * 60 * 1000
}

// ============================================================
// 变更记录（页面底部预览表）
// ============================================================
const changeLogs = ref<ChangeLogEntry[]>([])
const newChangeContent = ref('')
const changeSubmitting = ref(false)

async function loadChangeLogs() {
  if (!record.value?.id) return
  try {
    const res = await listChangeLogs('rental', record.value.id)
    changeLogs.value = Array.isArray(res) ? res : []
  } catch {
    changeLogs.value = []
  }
}

async function handleAddChangeLog() {
  if (!newChangeContent.value.trim() || !record.value?.id) return
  changeSubmitting.value = true
  try {
    await createChangeLog({
      target_type: 'rental',
      target_id: record.value.id,
      content: newChangeContent.value.trim(),
    })
    newChangeContent.value = ''
    await loadChangeLogs()
    ElMessage.success('已添加')
  } catch {
    // 错误已统一处理
  } finally {
    changeSubmitting.value = false
  }
}

/** 滚动锚点到页面底部变更记录区域 */
function scrollToChangeLogs() {
  const el = document.getElementById('changelog-section')
  if (el) el.scrollIntoView({ behavior: 'smooth' })
}

function formatChangelogTime(s?: string | null) {
  if (!s) return '-'
  return s.slice(0, 16).replace('T', ' ')
}

/** 变更记录内容为 JSON 新格式时返回字段数组，否则返回 null（模板内避免重复解析） */
function changeFields(content: string | null | undefined) {
  const parsed = parseChangeContent(content)
  return parsed.type === 'json' ? parsed.fields : null
}

onMounted(() => {
  fetchRecord().then(() => loadChangeLogs())
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
        <h1 class="header-title">{{ record.machine_model || '...' }}</h1>
        <div class="header-sub">
          <span class="header-customer">{{ record.customer?.name || '-' }}</span>
          <el-tag
            v-if="record.status"
            :type="statusTagType(record.status)"
            size="small"
          >{{ statusLabel(record.status) }}</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button :disabled="record.status === '已断电'" @click="handleEdit">编辑</el-button>
        <el-button @click="scrollToChangeLogs">变更记录</el-button>
      </div>
    </div>

    <!-- 基本信息 -->
    <section class="detail-section">
      <div class="dialog-section-title">基本信息</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="客户名称">{{ record.customer?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="机器型号">{{ record.machine_model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="租赁状态">
          <el-tag
            v-if="record.status"
            :type="statusTagType(record.status)"
            size="small"
          >{{ statusLabel(record.status) }}</el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="计费方式">{{ billingLabel(record.billing_model) }}</el-descriptions-item>
        <el-descriptions-item label="自动续期">{{ record.auto_renew ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="开通时间">{{ record.start_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="到期时间">
          <span :class="{ 'expiring-text': isExpiring(record.end_date) }">
            {{ record.end_date || '-' }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(record.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(record.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">
          <span v-if="record.remark">{{ record.remark }}</span>
          <span v-else class="muted">—</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 硬件配置 -->
    <section class="detail-section">
      <div class="dialog-section-title">硬件配置</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="CPU 型号">{{ record.cpu_model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="内存容量">
          {{ record.memory_gb ? record.memory_gb + ' GB' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="GPU 信息">
          <span v-if="record.gpu_info" class="highlight-value">{{ record.gpu_info }}</span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="系统盘">
          {{ record.system_disk || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="数据盘" :span="2">
          <template v-if="record.data_disks && record.data_disks.length">
            <div class="storage-list">
              <div v-for="(disk, i) in record.data_disks" :key="i" class="storage-item-detail">
                <span class="storage-dot">●</span>
                <span class="storage-text">{{ disk }}</span>
              </div>
            </div>
          </template>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="操作系统">{{ record.os_version || '-' }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 存储与网络 -->
    <section class="detail-section">
      <div class="dialog-section-title">存储与网络</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="内网 IP">{{ record.private_ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="公网 IP">
          {{ (record.public_ips || []).join(', ') || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="带宽">
          <span v-if="record.bandwidth_mbps" class="highlight-value">
            {{ formatBandwidth(record.bandwidth_mbps) }}
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="SSH 端口">{{ record.ssh_port || 22 }}</el-descriptions-item>
        <el-descriptions-item label="机架位置" :span="2">{{ record.rack_location || '-' }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 登录凭证 -->
    <section class="detail-section">
      <div class="dialog-section-title">登录凭证</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="账号">{{ record.root_username || 'root' }}</el-descriptions-item>
        <el-descriptions-item label="密码" :span="2">
          <span
            class="password-toggle"
            @click="showPassword = !showPassword"
          >
            <code class="password-code">
              {{ showPassword ? (record.root_password || '-') : '••••••••' }}
            </code>
            <el-icon class="password-icon">
              <View v-if="!showPassword" />
              <Hide v-else />
            </el-icon>
          </span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 关联合同信息 -->
    <section
      v-if="record.contract_info"
      class="detail-section"
    >
      <div class="dialog-section-title">关联合同信息</div>
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="合同名称">
          <el-link
            type="primary"
            :underline="false"
            @click="router.push({ name: 'ContractDetail', params: { id: record.contract_info.id } })"
          >
            {{ record.contract_info.name }}
          </el-link>
        </el-descriptions-item>
        <el-descriptions-item label="客户">
          {{ record.customer?.name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="到期时间">
          {{ record.contract_info.end_date }}
        </el-descriptions-item>
        <el-descriptions-item label="计费方式">
          {{ billingLabel(record.contract_info.billing_model) }}
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 变更记录（页面底部） -->
    <section id="changelog-section" class="detail-section">
      <div class="section-toolbar">
        <div class="dialog-section-title">变更记录</div>
        <span class="muted">共 {{ changeLogs.length }} 条</span>
      </div>
      <el-table :data="changeLogs" stripe style="width:100%">
        <template #empty>
          <div class="table-empty table-empty--compact">
            <el-empty description="暂无变更记录" :image-size="64" />
          </div>
        </template>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            <span class="col-secondary">{{ formatChangelogTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <!-- 内容：兼容旧纯文本与新结构化 JSON（字段：旧值 → 新值） -->
        <el-table-column label="内容" min-width="360">
          <template #default="{ row }">
            <template v-if="changeFields(row.content)">
              <div
                v-for="(f, i) in changeFields(row.content)!"
                :key="i"
                class="change-field-line"
              >
                <el-tag size="small" type="info" class="change-field-tag">{{ f.field }}</el-tag>
                <span class="change-value">{{ formatChangeValue(f.old) }}</span>
                <span class="change-arrow">→</span>
                <span class="change-value change-value-new">{{ formatChangeValue(f.new) }}</span>
              </div>
            </template>
            <span v-else>{{ row.content }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="changelog-add">
        <el-input v-model="newChangeContent" placeholder="输入变更内容" maxlength="500" show-word-limit style="flex:1" />
        <el-button type="primary" :disabled="!newChangeContent.trim()" :loading="changeSubmitting" @click="handleAddChangeLog">
          添加变更记录
        </el-button>
      </div>
    </section>
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
.header-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}
.header-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 14px;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.detail-section {
  padding: 20px;
  border-radius: 8px;
}
.detail-section > .dialog-section-title {
  margin-bottom: 12px;
}

.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}
.section-toolbar .dialog-section-title {
  margin: 0;
  padding-top: 0;
  padding-right: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.muted {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 400;
  opacity: 0.85;
}

.highlight-value {
  background: #1e40af;
  color: #fff;
  padding: 2px 10px;
  border-radius: 4px;
  display: inline-block;
  font-weight: 600;
  font-size: 13px;
}

.expiring-text {
  color: #ef4444 !important;
  font-weight: 600;
}

.password-toggle {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.password-code {
  background: #f3f4f6;
  padding: 4px 12px;
  border-radius: 4px;
  font-family: monospace;
}
.password-icon {
  color: #9ca3af;
}

.changelog-add {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

/* 变更记录：结构化 JSON 渲染（字段：旧值 → 新值） */
.change-field-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  line-height: 1.8;
}
.change-field-tag {
  flex-shrink: 0;
}
.change-value {
  color: var(--text-secondary, #606266);
  word-break: break-all;
}
.change-value-new {
  color: var(--text-primary, #1f2937);
  font-weight: 500;
}
.change-arrow {
  color: #909399;
  flex-shrink: 0;
}

.storage-list { display: flex; flex-direction: column; gap: 4px; }
.storage-item-detail { display: flex; align-items: center; padding: 2px 0; }
.storage-dot { color: var(--primary-color); margin-right: 6px; font-size: 10px; }
.storage-text { font-size: 13px; color: var(--text-primary); }
.col-secondary {
  color: var(--text-secondary);
}
</style>
