<template>
  <div class="page-container">
    <div class="page-header"><div class="flex items-center gap-base"><el-button @click="router.back()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>返回</el-button><h1 class="page-title">{{ isEdit ? '编辑模板' : '创建模板' }}</h1></div></div>
    <div class="content-card">
      <el-form :model="form" label-width="100px" class="contract-form">
        <div class="form-section"><div class="form-section__title">基础信息</div><div class="form-grid">
          <el-form-item label="模板名称" required><el-input v-model="form.name" placeholder="例如：合同到期提醒" /></el-form-item>
          <el-form-item label="邮件主题" required><el-input v-model="form.subject" placeholder="例如：您的合同即将到期" /></el-form-item>
          <el-form-item label="内容类型"><el-radio-group v-model="form.content_type"><el-radio value="html">HTML</el-radio><el-radio value="text">纯文本</el-radio></el-radio-group></el-form-item>
          <el-form-item label="状态"><el-switch v-model="form.is_active" active-text="启用" /></el-form-item>
        </div></div>
        <div class="form-section"><div class="form-section__title">邮件内容</div><div class="form-grid form-grid--full">
          <el-form-item label="内容" required><el-input v-model="form.content" type="textarea" :rows="10" placeholder="请输入邮件内容，支持 {name} {date} 等变量" /></el-form-item>
        </div></div>
        <div class="form-actions"><el-button @click="router.back()">取消</el-button><el-button type="primary" :loading="loading" @click="handleSave">保存</el-button></div>
      </el-form>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTemplate, createTemplate, updateTemplate } from '@/api/template'
const route = useRoute()
const router = useRouter()
const id = route.params.id as string | undefined
const isEdit = !!id
const loading = ref(false)
const form = reactive({ name: '', subject: '', content: '', content_type: 'html' as 'html' | 'text', is_active: true })
onMounted(async () => { if (isEdit) { try { Object.assign(form, await getTemplate(id!)) } catch { /* ignore */ } } })
const handleSave = async () => { loading.value = true; try { if (isEdit) await updateTemplate(id!, form); else { const res: any = await createTemplate(form); router.push(`/templates/${res.id}/edit`) }; ElMessage.success('保存成功'); router.push('/templates') } catch { /* ignore */ } finally { loading.value = false } }
</script>
<style scoped lang="scss">.contract-form { max-width: 800px; }
.form-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); justify-content: flex-end; }</style>