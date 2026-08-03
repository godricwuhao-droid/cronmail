<template>
  <div class="page-container">
    <div class="page-header"><div class="flex items-center gap-base"><el-button @click="router.back()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>返回</el-button><h1 class="page-title">{{ isEdit ? '编辑项目' : '新建项目' }}</h1></div></div>
    <div class="content-card">
      <el-form :model="form" label-width="100px" class="contract-form">
        <div class="form-section"><div class="form-section__title">基础信息</div><div class="form-grid">
          <el-form-item label="项目名称" required><el-input v-model="form.name" placeholder="例如：千星控股一期项目" /></el-form-item>
          <el-form-item label="客户" required><el-select v-model="form.customer_id" placeholder="请选择客户" filterable style="width: 100%"><el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
          <el-form-item label="开始日期"><el-date-picker v-model="form.start_date" type="date" placeholder="选择开始日期" style="width: 100%" /></el-form-item>
          <el-form-item label="结束日期"><el-date-picker v-model="form.end_date" type="date" placeholder="选择结束日期" style="width: 100%" /></el-form-item>
        </div></div>
        <div class="form-section"><div class="form-section__title">其他信息</div><div class="form-grid form-grid--full">
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入项目描述信息" /></el-form-item>
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
import { getProjectContract, createProjectContract, updateProjectContract } from '@/api/project'
import { getCustomers } from '@/api/customer'
const route = useRoute()
const router = useRouter()
const id = route.params.id as string | undefined
const isEdit = !!id
const loading = ref(false)
const customers = ref<any[]>([])
const form = reactive({ name: '', customer_id: '', customer_name: '', start_date: '', end_date: '', status: 'active', description: '' })
onMounted(async () => { try { customers.value = await getCustomers({ page_size: 200 }) } catch { /* ignore */ } if (isEdit) { try { Object.assign(form, await getProjectContract('qianxing', id!)) } catch { /* ignore */ } } })
const handleSave = async () => { loading.value = true; try { if (isEdit) await updateProjectContract('qianxing', id!, form); else { const res: any = await createProjectContract('qianxing', form); router.push(`/projects/qianxing/${res.id}`) }; ElMessage.success('保存成功'); router.push('/projects/qianxing') } catch { /* ignore */ } finally { loading.value = false } }
</script>
<style scoped lang="scss">.contract-form { max-width: 800px; }
.form-actions { margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-light); display: flex; gap: var(--spacing-sm); justify-content: flex-end; }</style>