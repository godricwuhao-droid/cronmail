<template>
  <div class="page-container">
    <div class="page-header"><div class="flex items-center gap-base"><el-button @click="router.back()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>返回</el-button><h1 class="page-title">{{ isEdit ? '编辑设备' : '创建设备' }}</h1></div></div>
    <div class="content-card">
      <el-form :model="form" label-width="100px" class="contract-form">
        <div class="form-section"><div class="form-section__title">基础信息</div><div class="form-grid">
          <el-form-item label="设备名称" required><el-input v-model="form.name" placeholder="例如：GPU服务器-001" /></el-form-item>
          <el-form-item label="序列号"><el-input v-model="form.serial_number" placeholder="例如：SN20260001" /></el-form-item>
          <el-form-item label="型号"><el-input v-model="form.model" placeholder="例如：NVIDIA A100" /></el-form-item>
          <el-form-item label="IP地址"><el-input v-model="form.ip_address" placeholder="例如：192.168.1.100" /></el-form-item>
          <el-form-item label="位置"><el-input v-model="form.location" placeholder="例如：北京机房A区" /></el-form-item>
          <el-form-item label="状态"><el-select v-model="form.status" style="width: 100%"><el-option label="运行中" value="active" /><el-option label="维护中" value="maintenance" /><el-option label="离线" value="offline" /></el-select></el-form-item>
        </div></div>
        <div class="form-section"><div class="form-section__title">其他信息</div><div class="form-grid form-grid--full">
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入设备描述信息" /></el-form-item>
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
import http from '@/api/request'
const route = useRoute()
const router = useRouter()
const id = route.params.id as string | undefined
const isEdit = !!id
const loading = ref(false)
const form = reactive({ name: '', serial_number: '', model: '', ip_address: '', location: '', status: 'active', description: '' })
onMounted(async () => { if (isEdit) { try { Object.assign(form, await http.get(`/devices/${id!}`)) } catch { /* ignore */ } } })
const handleSave = async () => { loading.value = true; try { if (isEdit) await http.put(`/devices/${id!}`, form); else { const res: any = await http.post('/devices', form); router.push(`/devices/${res.id}`) }; ElMessage.success('保存成功'); router.push('/devices') } catch { /* ignore */ } finally { loading.value = false } }
</script>
<style scoped lang="scss">.contract-form { max-width: 800px; }
.form-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); justify-content: flex-end; }</style>