<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">SMTP配置</h1></div>
    <div class="page-toolbar">
      <div class="page-toolbar-left"></div>
      <div class="page-toolbar-right"><el-button type="primary" @click="openDialog()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>新增配置</el-button></div>
    </div>
    <div class="content-card" style="padding: 0;">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="host" label="主机" width="180" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="username" label="用户名" min-width="180" />
        <el-table-column prop="use_tls" label="TLS" width="80"><template #default="{ row }"><el-tag :type="row.use_tls ? 'success' : 'info'" size="small">{{ row.use_tls ? '是' : '否' }}</el-tag></template></el-table-column>
        <el-table-column prop="is_default" label="默认" width="80"><template #default="{ row }"><el-tag v-if="row.is_default" type="primary" size="small">默认</el-tag><span v-else class="text-tertiary text-sm">-</span></template></el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑SMTP配置' : '新增SMTP配置'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required><el-input v-model="form.name" placeholder="例如：公司邮箱" /></el-form-item>
        <el-form-item label="主机" required><el-input v-model="form.host" placeholder="例如：smtp.qq.com" /></el-form-item>
        <el-form-item label="端口" required><el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" /></el-form-item>
        <el-form-item label="用户名" required><el-input v-model="form.username" placeholder="例如：admin@example.com" /></el-form-item>
        <el-form-item label="密码" required><el-input v-model="form.password" type="password" show-password placeholder="请输入SMTP密码" /></el-form-item>
        <el-form-item label="TLS"><el-switch v-model="form.use_tls" /></el-form-item>
        <el-form-item label="默认"><el-switch v-model="form.is_default" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSmtpConfigs, createSmtpConfig, updateSmtpConfig, deleteSmtpConfig } from '@/api/system'
const list = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', host: '', port: 465, username: '', password: '', use_tls: true, is_default: false })
onMounted(() => loadData())
const loadData = async () => { loading.value = true; try { list.value = await getSmtpConfigs() } catch { /* ignore */ } finally { loading.value = false } }
const openDialog = (row?: any) => { if (row) { editingId.value = row.id; Object.assign(form, row) } else { editingId.value = null; Object.assign(form, { name: '', host: '', port: 465, username: '', password: '', use_tls: true, is_default: false }) }; dialogVisible.value = true }
const handleSave = async () => { try { if (editingId.value) await updateSmtpConfig(editingId.value, form); else await createSmtpConfig(form); ElMessage.success('保存成功'); dialogVisible.value = false; loadData() } catch { /* ignore */ } }
const handleDelete = async (id: string) => { try { await deleteSmtpConfig(id); ElMessage.success('删除成功'); loadData() } catch { /* ignore */ } }
</script>
<style scoped lang="scss"></style>