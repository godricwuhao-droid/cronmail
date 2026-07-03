<script setup lang="ts">
/**
 * 系统配置页 - 临期提醒配置 + 通知时间配置
 *
 * 路由：/system/config
 *
 * 功能：
 *  - 加载时 GET /api/system/config/expiry_warning_days
 *  - 加载时 GET /api/system/config/schedules
 *  - 保存临期提醒 PUT /api/system/config/expiry_warning_days
 *  - 保存通知时间 PUT /api/system/config/schedules
 */
import { onMounted, ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Clock } from '@element-plus/icons-vue'
import {
  getConfig,
  updateConfig,
  getSchedules,
  updateSchedules,
  type ScheduleConfig,
} from '@/api/modules/system'

// ============================================================
// 临期提醒表单
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

async function handleSaveExpiry() {
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

// ============================================================
// 通知时间配置
// ============================================================
const scheduleLoading = ref(false)
const scheduleSaving = ref(false)

const schedules = reactive<ScheduleConfig>({
  'check-expiring-rentals': '08:00',
  'check-expired-rentals': '00:00',
  'check-reclaim-expired': '01:00',
})

async function fetchSchedules() {
  scheduleLoading.value = true
  try {
    const data = await getSchedules()
    schedules['check-expiring-rentals'] = data['check-expiring-rentals'] || '08:00'
    schedules['check-expired-rentals'] = data['check-expired-rentals'] || '00:00'
    schedules['check-reclaim-expired'] = data['check-reclaim-expired'] || '01:00'
  } catch (e: any) {
    // 404 表示尚未配置，保持默认值
    if (e?.response?.status !== 404) {
      // 其他错误统一处理
    }
  } finally {
    scheduleLoading.value = false
  }
}

async function handleSaveSchedules() {
  scheduleSaving.value = true
  try {
    const data: ScheduleConfig = {
      'check-expiring-rentals': schedules['check-expiring-rentals'],
      'check-expired-rentals': schedules['check-expired-rentals'],
      'check-reclaim-expired': schedules['check-reclaim-expired'],
    }
    const result = await updateSchedules(data)
    ElMessage.success('通知时间配置已保存，Beat 正在重启...')
    if (result.restart && result.restart.includes('error')) {
      ElMessage.warning(result.restart)
    }
  } catch {
    // 错误已统一处理
  } finally {
    scheduleSaving.value = false
  }
}

// ============================================================
// 统一保存入口
// ============================================================
async function handleSave() {
  await handleSaveExpiry()
  await handleSaveSchedules()
}

onMounted(() => {
  fetchConfig()
  fetchSchedules()
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

        <el-divider />

        <div v-loading="scheduleLoading" class="schedule-section">
          <div class="section-title">
            <el-icon><Clock /></el-icon>
            通知时间配置
          </div>
          <div class="schedule-hint">
            设置 Celery Beat 定时任务的每日执行时间（北京时间）
          </div>

          <div class="schedule-items">
            <div class="schedule-item">
              <span class="schedule-label">临期提醒通知</span>
              <el-time-picker
                v-model="schedules['check-expiring-rentals']"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 160px"
              />
            </div>
            <div class="schedule-item">
              <span class="schedule-label">到期回收通知</span>
              <el-time-picker
                v-model="schedules['check-expired-rentals']"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 160px"
              />
            </div>
            <div class="schedule-item">
              <span class="schedule-label">回收执行时间</span>
              <el-time-picker
                v-model="schedules['check-reclaim-expired']"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 160px"
              />
            </div>
          </div>
        </div>
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

/* 通知时间配置 */
.schedule-section {
  margin-top: 0;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.schedule-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 16px;
}
.schedule-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.schedule-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.schedule-label {
  width: 120px;
  font-size: 14px;
  color: #606266;
  flex-shrink: 0;
}
</style>
