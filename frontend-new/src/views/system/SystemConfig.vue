<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">系统配置</h1></div>
    <div class="content-card">
      <el-form :model="form" label-width="120px" class="contract-form" v-if="form">
        <div class="form-section"><div class="form-section__title">邮件配置</div><div class="form-grid">
          <el-form-item label="发件人邮箱"><el-input v-model="form.mail_from" placeholder="例如：noreply@example.com" /></el-form-item>
          <el-form-item label="发件人名称"><el-input v-model="form.mail_from_name" placeholder="例如：CronMail系统" /></el-form-item>
        </div></div>
        <div class="form-section"><div class="form-section__title">定时任务配置</div><div class="form-grid">
          <el-form-item label="Cron表达式"><el-input v-model="form.cron_expression" placeholder="例如：0 9 * * * 表示每天9点执行" /></el-form-item>
        </div></div>
        <div class="form-actions"><el-button type="primary" :loading="loading" @click="handleSave">保存配置</el-button></div>
      </el-form>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemConfig, updateSystemConfig } from '@/api/system'
const loading = ref(false)
const form = reactive({ mail_from: '', mail_from_name: '', default_template_id: '', cron_expression: '' })
onMounted(async () => { try { const data = await getSystemConfig(); Object.assign(form, data) } catch { /* ignore */ } })
const handleSave = async () => { loading.value = true; try { await updateSystemConfig(form); ElMessage.success('保存成功') } catch { /* ignore */ } finally { loading.value = false } }
</script>
<style scoped lang="scss">.contract-form { max-width: 800px; }
.form-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); justify-content: flex-end; }</style>