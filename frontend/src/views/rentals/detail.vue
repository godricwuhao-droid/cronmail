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
 *  - 收件人表格 + 发送日志表格
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
function triggerLabel(s?: string) {
  const m: Record<string, string> = {
    provision: '开通',
    expiry_warning: '临期',
    reclaim: '回收',
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

onMounted(() => {
  fetchRecord().then(() => loadChangeLogs())
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <!-- 顶部返回 -->
    <div style="margin-bottom: 16px;">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回列表
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
            effect="dark"
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
      <h3 class="section-title">基本信息</h3>
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
      <h3 class="section-title">硬件配置</h3>
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
          {{ record.system_disk_gb ? record.system_disk_gb + ' GB' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="数据盘" :span="2">
          <template v-if="record.data_disks && record.data_disks.length">
            <el-tag
              v-for="(disk, i) in record.data_disks"
              :key="i"
              size="small"
              style="margin-right: 8px;"
            >{{ disk.size_gb }}GB {{ disk.type }}</el-tag>
          </template>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="操作系统">{{ record.os_version || '-' }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 存储与网络 -->
    <section class="detail-section">
      <h3 class="section-title">存储与网络</h3>
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
      <h3 class="section-title">登录凭证</h3>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="账号">{{ record.root_username || 'root' }}</el-descriptions-item>
        <el-descriptions-item label="密码" :span="2">
          <span
            @click="showPassword = !showPassword"
            style="cursor: pointer; display: inline-flex; align-items: center; gap: 8px;"
          >
            <code style="background: #f3f4f6; padding: 4px 12px; border-radius: 4px; font-family: monospace;">
              {{ showPassword ? (record.root_password || '-') : '••••••••' }}
            </code>
            <el-icon style="color: #9ca3af;">
              <View v-if="!showPassword" />
              <Hide v-else />
            </el-icon>
          </span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- 关联合同信息卡片 -->
    <section
      v-if="record.contract_info"
      class="detail-section"
    >
      <h3 class="section-title">关联合同信息</h3>
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

    <!-- 收件人 -->
    <section class="detail-section">
      <h3 class="section-title">收件人</h3>
      <el-table
        :data="record.contacts || []"
        size="small"
        stripe
        border
        empty-text="暂未设置收件人"
        style="width: 100%;"
      >
        <el-table-column prop="name" label="姓名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.recipient_type === 'to' ? 'primary' : 'info'"
              size="small"
            >{{ row.recipient_type === 'to' ? '收件人' : '抄送' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 发送日志 -->
    <section class="detail-section">
      <h3 class="section-title">发送日志</h3>
      <el-table
        :data="record.email_logs || []"
        size="small"
        stripe
        border
        empty-text="暂无发送记录"
        style="width: 100%;"
      >
        <el-table-column prop="recipient" label="收件人" min-width="180" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ triggerLabel(row.trigger_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="主题" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'sent' ? 'success' : 'danger'"
              size="small"
            >{{ row.status === 'sent' ? '成功' : '失败' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sent_at" label="发送时间" width="160" />
      </el-table>
    </section>

    <!-- 变更记录（页面底部） -->
    <section id="changelog-section" class="detail-section">
      <div class="section-header">
        <h3>变更记录</h3>
        <span class="muted">（共 {{ changeLogs.length }} 条）</span>
      </div>
      <el-table :data="changeLogs" size="small" stripe border empty-text="暂无变更记录" style="width:100%">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ formatChangelogTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
      </el-table>
      <div style="margin-top:12px; display:flex; gap:8px;">
        <el-input v-model="newChangeContent" placeholder="输入变更内容" maxlength="500" show-word-limit style="flex:1" />
        <el-button type="primary" :disabled="!newChangeContent.trim()" :loading="changeSubmitting" @click="handleAddChangeLog">
          添加变更记录
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-header {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}
.header-left {
  min-width: 0;
}
.header-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}
.header-sub {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}
.header-customer {
  margin-right: 4px;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  padding-bottom: 12px;
  border-bottom: 2px solid var(--border-color);
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

.hint {
  color: #909399;
  font-size: 13px;
  padding: 8px 0;
}
.muted {
  color: #c0c4cc;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}
.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}
</style>
