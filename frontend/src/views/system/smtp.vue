<script setup lang="ts">
/**
 * SMTP 配置页
 *
 * 路由：/system/smtp
 *
 * 功能：
 *  - 加载时 GET /api/system/smtp 填充表单（不含密码）
 *  - 保存：PUT /api/system/smtp
 *  - 测试连接：弹窗输入测试邮箱 → POST /api/system/smtp/test
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Message, InfoFilled } from '@element-plus/icons-vue'
import {
  getSmtpConfig,
  testSmtp,
  updateSmtpConfig,
  type SmtpConfig,
  type SmtpConfigUpdate,
} from '@/api/modules/system'

// ============================================================
// 主表单
// ============================================================
const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)
/** 是否已存在配置（控制密码是否必填） */
const hasConfig = ref(false)
/** 表单是否处于"修改密码"模式 */
const changingPassword = ref(false)

const form = reactive({
  host: '',
  port: 465,
  username: '',
  password: '',
  sender_name: '',
  sender_email: '',
  encryption: 'tls' as 'tls' | 'starttls' | 'none',
})

const rules: FormRules = {
  host: [{ required: true, message: '请输入 SMTP 服务器地址', trigger: 'blur' }],
  port: [
    {
      required: true,
      message: '请输入端口',
      trigger: 'blur',
    },
    {
      validator: (_rule, value, callback) => {
        const n = Number(value)
        if (!Number.isInteger(n) || n < 1 || n > 65535) {
          callback(new Error('端口范围 1-65535'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  username: [{ max: 256, message: '长度不能超过 256 个字符', trigger: 'blur' }],
  password: [
    {
      validator: (_rule, value, callback) => {
        // 已存在配置且未勾选"修改密码"：跳过校验
        if (hasConfig.value && !changingPassword.value) {
          callback()
          return
        }
        if (!value) {
          callback(new Error('请输入密码'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  sender_name: [{ max: 128, message: '长度不能超过 128 个字符', trigger: 'blur' }],
  sender_email: [
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        if (String(value).indexOf('@') === -1) {
          callback(new Error('邮箱格式不正确'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

async function fetchConfig() {
  loading.value = true
  try {
    const cfg: SmtpConfig = await getSmtpConfig()
    form.host = cfg.host
    form.port = cfg.port
    form.username = cfg.username ?? ''
    form.sender_name = cfg.sender_name ?? ''
    form.sender_email = cfg.sender_email ?? ''
    form.encryption = cfg.encryption
    form.password = '' // 后端不返回密码
    hasConfig.value = true
    changingPassword.value = false
  } catch (e: any) {
    // 404 表示尚未配置：保持空表单即可（__silent 已阻止全局错误提示）
    if (e?.response?.status === 404) {
      hasConfig.value = false
      changingPassword.value = true
      return
    }
    // 非 404 错误（如网络断开）：手动提示
    ElMessage.error('加载 SMTP 配置失败，请检查网络连接')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload: SmtpConfigUpdate = {
      host: form.host.trim(),
      port: Number(form.port),
      username: form.username.trim() || undefined,
      sender_name: form.sender_name.trim() || undefined,
      sender_email: form.sender_email.trim() || undefined,
      encryption: form.encryption,
    }
    // 仅在新建或主动修改密码时传递
    if (!hasConfig.value || changingPassword.value) {
      payload.password = form.password
    }
    await updateSmtpConfig(payload)
    ElMessage.success('SMTP 配置已保存')
    hasConfig.value = true
    changingPassword.value = false
    form.password = ''
  } catch (e) {
    // 错误已统一处理
  } finally {
    saving.value = false
  }
}

function togglePasswordChange(val: boolean) {
  changingPassword.value = val
  if (val) {
    form.password = ''
  }
  // 触发一次校验状态刷新
  setTimeout(() => formRef.value?.clearValidate(['password']), 0)
}

// ============================================================
// 测试连接弹窗
// ============================================================
const testDialogVisible = ref(false)
const testSubmitting = ref(false)
const testFormRef = ref<FormInstance>()
const testResult = ref<{ success: boolean; message: string } | null>(null)
const testForm = reactive({ test_email: '' })
const testRules: FormRules = {
  test_email: [
    { required: true, message: '请输入测试邮箱', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (String(value).indexOf('@') === -1) {
          callback(new Error('邮箱格式不正确'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function openTestDialog() {
  // 优先用发件人邮箱做默认值
  testForm.test_email = form.sender_email || form.username || ''
  testResult.value = null
  testDialogVisible.value = true
  setTimeout(() => testFormRef.value?.clearValidate(), 0)
}

async function handleTest() {
  if (!testFormRef.value) return
  try {
    await testFormRef.value.validate()
  } catch {
    return
  }
  testSubmitting.value = true
  testResult.value = null
  try {
    const res = await testSmtp({ test_email: testForm.test_email.trim() })
    testResult.value = { success: res.success, message: res.message }
    if (res.success) {
      ElMessage.success(res.message || '测试邮件已发送')
    } else {
      ElMessage.error(res.message || '测试失败')
    }
  } catch (e) {
    // 错误已统一处理
  } finally {
    testSubmitting.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div class="page-container">
    <div class="page-panel" v-loading="loading">
      <div class="card-header">
        <span class="title">
          <el-icon><Message /></el-icon>
          SMTP 配置
        </span>
        <div class="header-actions">
          <el-button :disabled="!hasConfig" @click="openTestDialog">测试连接</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </div>
      </div>

      <div v-if="!hasConfig" class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>尚未配置 SMTP。请填写完整服务器信息后保存，首次保存后将自动启用。</span>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="config-form"
        @submit.prevent="handleSave"
      >
        <div class="dialog-section">
          <div class="dialog-section-title">服务器连接</div>
          <el-row :gutter="16">
            <el-col :span="24">
              <el-form-item label="SMTP 服务器" prop="host">
                <el-input v-model="form.host" placeholder="如 smtp.example.com" maxlength="256" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="端口" prop="port">
                <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="加密方式" prop="encryption">
                <el-select v-model="form.encryption" style="width: 100%">
                  <el-option label="SSL/TLS (端口 465)" value="tls" />
                  <el-option label="STARTTLS (端口 587)" value="starttls" />
                  <el-option label="无加密 (端口 25)" value="none" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="dialog-section">
          <div class="dialog-section-title">账号认证</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="用户名" prop="username">
                <el-input v-model="form.username" placeholder="SMTP 登录账号（通常为邮箱）" maxlength="256" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="密码" prop="password">
                <div class="password-area">
                  <el-input
                    v-model="form.password"
                    type="password"
                    show-password
                    :placeholder="hasConfig ? (changingPassword ? '请输入新密码' : '已配置（留空不修改）') : '请输入密码'"
                    :disabled="hasConfig && !changingPassword"
                    maxlength="256"
                  />
                  <el-checkbox
                    v-if="hasConfig"
                    class="password-change"
                    :model-value="changingPassword"
                    @change="togglePasswordChange($event as boolean)"
                  >
                    修改密码
                  </el-checkbox>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="dialog-section">
          <div class="dialog-section-title">发件人信息</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="发件人名称" prop="sender_name">
                <el-input v-model="form.sender_name" placeholder="如 CronMail" maxlength="128" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="发件人邮箱" prop="sender_email">
                <el-input v-model="form.sender_email" placeholder="发件人邮箱地址" maxlength="256" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
    </div>

    <!-- 测试连接弹窗 -->
    <el-dialog
      v-model="testDialogVisible"
      title="测试 SMTP 连接"
      width="560px"
      destroy-on-close
      :close-on-click-modal="false"
      class="create-dialog"
      @closed="testResult = null"
    >
      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>将使用已保存的 SMTP 配置发送一封测试邮件，用于验证服务器连通与账号可用性。</span>
      </div>

      <el-form ref="testFormRef" :model="testForm" :rules="testRules" label-position="top">
        <div class="dialog-section">
          <div class="dialog-section-title">收件信息</div>
          <el-form-item label="测试邮箱" prop="test_email">
            <el-input
              v-model="testForm.test_email"
              placeholder="用于接收测试邮件的邮箱"
              maxlength="256"
            />
          </el-form-item>
        </div>
      </el-form>

      <div v-if="testResult" class="test-result">
        <el-alert
          :title="testResult.success ? '发送成功' : '发送失败'"
          :type="testResult.success ? 'success' : 'error'"
          :description="testResult.message"
          :closable="false"
          show-icon
        />
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="testDialogVisible = false">关闭</el-button>
          <el-button type="primary" :loading="testSubmitting" @click="handleTest">发送测试邮件</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.config-form {
  max-width: 720px;
}
.config-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
}
.config-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
.password-area {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  width: 100%;
}
.password-change {
  align-self: flex-start;
  height: auto;
  margin-right: 0;
}
.test-result {
  margin-top: 4px;
}
</style>
