<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">同事管理</h1></div>
    <div class="page-toolbar">
      <div class="page-toolbar-left"></div>
      <div class="page-toolbar-right"><el-button type="primary" @click="openDialog()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>新增同事</el-button></div>
    </div>
    <div class="content-card" style="padding: 0;">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="department" label="部门" width="140" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑同事' : '新增同事'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="姓名" required><el-input v-model="form.name" placeholder="例如：张三" /></el-form-item>
        <el-form-item label="邮箱" required><el-input v-model="form.email" placeholder="例如：zhangsan@example.com" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" placeholder="例如：13800138000" /></el-form-item>
        <el-form-item label="部门"><el-input v-model="form.department" placeholder="例如：技术部" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getColleagues, createColleague, updateColleague, deleteColleague } from '@/api/system'
const list = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', email: '', phone: '', department: '' })
onMounted(() => loadData())
const loadData = async () => { loading.value = true; try { list.value = await getColleagues() } catch { /* ignore */ } finally { loading.value = false } }
const openDialog = (row?: any) => { if (row) { editingId.value = row.id; Object.assign(form, row) } else { editingId.value = null; Object.assign(form, { name: '', email: '', phone: '', department: '' }) }; dialogVisible.value = true }
const handleSave = async () => { try { if (editingId.value) await updateColleague(editingId.value, form); else await createColleague(form); ElMessage.success('保存成功'); dialogVisible.value = false; loadData() } catch { /* ignore */ } }
const handleDelete = async (id: string) => { try { await deleteColleague(id); ElMessage.success('删除成功'); loadData() } catch { /* ignore */ } }
</script>
<style scoped lang="scss"></style>