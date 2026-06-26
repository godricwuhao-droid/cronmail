<script setup lang="ts">
/**
 * 钉钉通知配置页
 *
 * 路由：/system/dingtalk
 *
 * 功能：
 *  - 加载时 GET /api/system/dingtalk 填充表单（secret 脱敏显示）
 *  - 保存：PUT /api/system/dingtalk
 *  - 测试发送：弹窗输入可覆盖 webhook/secret → POST /api/system/dingtalk/test
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'
import {
  getDingTalkConfig,
  testDingTalk,
  updateDingTalkConfig,
  type DingTalkConfig,
  type DingTalkConfigUpdate,
} from '@/api/modules/system'

// ============================================================
// 主表单
// ============================================================
const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)
/** 是否已存在配置 */
const hasConfig = ref(false)
/** 用户是否修改了 secret */
const secretModified = ref(false)

const form = reactive({
  webhook_url: '',
  secret: '',
  is_active: true,
})

const rules: FormRules = {
  webhook_url: [
    { required: true, message: '请输入 Webhook 地址', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && !String(value).startsWith('https://')) {
          callback(new Error('Webhook 地址必须以 https:// 开头'))
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
    const cfg: DingTalkConfig = await getDingTalkConfig()
    form.webhook_url = cfg.webhook_url
    form.secret = cfg.secret // 脱敏值 "***" 或 ""
    form.is_active = cfg.is_active
    hasConfig.value = true
    secretModified.value = false
  } catch (e: any) {
    // 404 表示尚未配置：保持空表单即可
    if (e?.response?.status === 404) {
      hasConfig.value = false
      secretModified.value = false
    }
  } finally {
    loading.value = false
  }
}

function onSecretInput() {
  // 用户开始修改 secret 时，如果之前是脱敏值 "***"，先清空让用户重新输入
  if (!secretModified.value && form.secret === '***') {
    form.secret = ''
  }
  secretModified.value = true
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
    const payload: DingTalkConfigUpdate = {
      webhook_url: form.webhook_url.trim(),
      is_active: form.is_active,
    }
    // secret：用户修改了传新值，没改则传 "***" 表示保留原值
    if (secretModified.value) {
      payload.secret = form.secret
    } else if (hasConfig.value) {
      payload.secret = '***'
    }
    await updateDingTalkConfig(payload)
    ElMessage.success('钉钉配置已保存')
    hasConfig.value = true
    secretModified.value = false
    // 重新加载以获取最新的脱敏值
    await fetchConfig()
  } catch (e) {
    // 错误已统一处理
  } finally {
    saving.value = false
  }
}

// ============================================================
// 测试发送弹窗
// ============================================================
const testDialogVisible = ref(false)
const testSubmitting = ref(false)
const testFormRef = ref<FormInstance>()
const testResult = ref<{ success: boolean; message: string } | null>(null)

const testForm = reactive({
  webhook_url: '',
  secret: '',
})

const testRules: FormRules = {
  webhook_url: [{ required: true, message: '请输入 Webhook 地址', trigger: 'blur' }],
}

function openTestDialog() {
  // 默认填入已保存的值
  testForm.webhook_url = form.webhook_url
  // secret 是脱敏值 "***" 时不填入，让用户手动输入
  testForm.secret = form.secret === '***' ? '' : form.secret
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
    const res = await testDingTalk({
      webhook_url: testForm.webhook_url.trim(),
      secret: testForm.secret || undefined,
    })
    testResult.value = { success: res.success, message: res.message }
    if (res.success) {
      ElMessage.success(res.message || '测试消息发送成功')
    } else {
      ElMessage.error(res.message || '测试发送失败')
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
    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><ChatDotRound /></el-icon>
            钉钉机器人配置
          </span>
          <div class="header-actions">
            <el-button :disabled="!hasConfig" @click="openTestDialog">测试发送</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="!hasConfig"
        title="尚未配置钉钉通知"
        type="info"
        :closable="false"
        show-icon
        description="请填写钉钉机器人 Webhook 地址后保存。支持加签方式增强安全性。"
        style="margin-bottom: 16px"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="110px"
        style="max-width: 640px"
        @submit.prevent="handleSave"
      >
        <el-form-item label="Webhook 地址" prop="webhook_url">
          <el-input
            v-model="form.webhook_url"
            placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx"
            maxlength="512"
          />
        </el-form-item>
        <el-form-item label="加签密钥" prop="secret">
          <el-input
            v-model="form.secret"
            type="password"
            show-password
            :placeholder="hasConfig ? (secretModified ? '请输入新密钥' : '已配置（留空不修改）') : '选填，用于安全校验'"
            maxlength="256"
            @input="onSecretInput"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
          <span style="margin-left: 10px; color: var(--text-secondary); font-size: 13px;">
            {{ form.is_active ? '已启用' : '已停用' }}
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 测试发送弹窗 -->
    <el-dialog
      v-model="testDialogVisible"
      title="测试发送"
      width="520px"
      :close-on-click-modal="false"
      @closed="testResult = null"
    >
      <el-form ref="testFormRef" :model="testForm" :rules="testRules" label-width="110px">
        <el-form-item label="Webhook 地址" prop="webhook_url">
          <el-input
            v-model="testForm.webhook_url"
            placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx"
            maxlength="512"
          />
        </el-form-item>
        <el-form-item label="加签密钥">
          <el-input
            v-model="testForm.secret"
            type="password"
            show-password
            placeholder="选填，默认使用已保存的密钥"
            maxlength="256"
          />
        </el-form-item>
      </el-form>

      <!-- 测试结果 -->
      <div v-if="testResult" style="margin-top: 12px;">
        <el-alert
          :title="testResult.success ? '发送成功' : '发送失败'"
          :type="testResult.success ? 'success' : 'error'"
          :description="testResult.message"
          :closable="false"
          show-icon
        />
      </div>

      <template #footer>
        <el-button @click="testDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="testSubmitting" @click="handleTest">发送测试消息</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.header-actions {
  display: flex;
  gap: 8px;
}
</style>
