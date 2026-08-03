<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">附件分类管理</h1></div>
    <div class="page-toolbar">
      <div class="page-toolbar-left"></div>
      <div class="page-toolbar-right"><el-button type="primary" @click="openDialog()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>新增分类</el-button></div>
    </div>
    <div class="content-card" style="padding: 0;">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="分类名称" min-width="200" />
        <el-table-column prop="description" label="描述" min-width="300" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑分类' : '新增分类'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required><el-input v-model="form.name" placeholder="例如：合同扫描件" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入分类描述" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAttachmentCategories, createAttachmentCategory, updateAttachmentCategory, deleteAttachmentCategory } from '@/api/attachment'
const list = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', description: '' })
onMounted(() => loadData())
const loadData = async () => { loading.value = true; try { list.value = await getAttachmentCategories() } catch { /* ignore */ } finally { loading.value = false } }
const openDialog = (row?: any) => { if (row) { editingId.value = row.id; Object.assign(form, row) } else { editingId.value = null; Object.assign(form, { name: '', description: '' }) }; dialogVisible.value = true }
const handleSave = async () => { try { if (editingId.value) await updateAttachmentCategory(editingId.value, form); else await createAttachmentCategory(form); ElMessage.success('保存成功'); dialogVisible.value = false; loadData() } catch { /* ignore */ } }
const handleDelete = async (id: string) => { try { await deleteAttachmentCategory(id); ElMessage.success('删除成功'); loadData() } catch { /* ignore */ } }
</script>
<style scoped lang="scss"></style>