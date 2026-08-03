<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">钉钉通知配置</h1></div>
    <div class="content-card">
      <el-form :model="form" label-width="120px" class="contract-form" v-if="form">
        <div class="form-section"><div class="form-section__title">钉钉机器人配置</div><div class="form-grid form-grid--full">
          <el-form-item label="启用通知"><el-switch v-model="form.enabled" /></el-form-item>
          <el-form-item label="Webhook地址"><el-input v-model="form.webhook" placeholder="例如：https://oapi.dingtalk.com/robot/send?access_token=xxx" /></el-form-item>
          <el-form-item label="加签密钥"><el-input v-model="form.secret" type="password" show-password placeholder="请输入加签密钥（可选）" /></el-form-item>
        </div></div>
        <div class="form-actions"><el-button type="primary" :loading="loading" @click="handleSave">保存配置</el-button></div>
      </el-form>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDingtalkConfig, updateDingtalkConfig } from '@/api/system'
const loading = ref(false)
const form = reactive({ enabled: false, webhook: '', secret: '' })
onMounted(async () => { try { const data = await getDingtalkConfig(); Object.assign(form, data) } catch { /* ignore */ } })
const handleSave = async () => { loading.value = true; try { await updateDingtalkConfig(form); ElMessage.success('保存成功') } catch { /* ignore */ } finally { loading.value = false } }
</script>
<style scoped lang="scss">.contract-form { max-width: 800px; }
.form-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); justify-content: flex-end; }</style>