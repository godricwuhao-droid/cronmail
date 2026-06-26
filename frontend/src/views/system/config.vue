<script setup lang="ts">
/**
 * 系统配置页 - 临期提醒配置
 *
 * 路由：/system/config
 *
 * 功能：
 *  - 加载时 GET /api/system/config/expiry_warning_days
 *  - 保存时 PUT /api/system/config/expiry_warning_days
 */
import { onMounted, ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Clock } from '@element-plus/icons-vue'
import { getConfig, updateConfig } from '@/api/modules/system'

// ============================================================
// 表单
// ============================================================
const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)

const form = reactive({
  expiry_warning_days: '7,3',
})

const rules: FormRules = {
  expiry_warning_days: [
    { required: true, message: '请输入临期提醒天数', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value || !String(value).trim()) {
          callback(new Error('请输入临期提醒天数'))
          return
        }
        const trimmed = String(value).trim()
        if (!/^\d+(,\d+)*$/.test(trimmed)) {
          callback(new Error('格式：逗号分隔的整数，如 "7,3"'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function fetchConfig() {
  loading.value = true
  try {
    const cfg = await getConfig('expiry_warning_days')
    form.expiry_warning_days = cfg.value || '7,3'
  } catch (e: any) {
    // 404 表示尚未配置，保持默认值
    if (e?.response?.status !== 404) {
      // 其他错误统一处理
    }
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
    await updateConfig('expiry_warning_days', form.expiry_warning_days.trim())
    ElMessage.success('临期提醒配置已保存')
  } catch {
    // 错误已统一处理
  } finally {
    saving.value = false
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
            <el-icon><Clock /></el-icon>
            系统配置
          </span>
          <div class="header-actions">
            <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
          </div>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="140px"
        style="max-width: 560px"
        @submit.prevent="handleSave"
      >
        <el-form-item label="临期提醒天数" prop="expiry_warning_days">
          <el-input
            v-model="form.expiry_warning_days"
            placeholder="如 7,3"
            maxlength="64"
          >
            <template #append>天</template>
          </el-input>
          <div class="form-tip">逗号分隔多个天数，定时任务将按这些天数发送临期提醒</div>
        </el-form-item>
      </el-form>
    </el-card>
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
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  line-height: 1.5;
}
</style>
