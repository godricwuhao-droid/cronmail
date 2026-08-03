<template>
  <div class="page-container">
    <div class="page-header">
      <div class="flex items-center gap-base">
        <el-button @click="router.push(`/customers/${customerId}`)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          返回客户
        </el-button>
        <h1 class="page-title">联系人管理</h1>
      </div>
    </div>
    <div class="page-toolbar">
      <div class="page-toolbar-left"></div>
      <div class="page-toolbar-right">
        <el-button type="primary" @click="openDialog()">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
          新建联系人
        </el-button>
      </div>
    </div>
    <div class="content-card" style="padding: 0;">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="title" label="职位" width="140" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="is_primary" label="主要联系人" width="100">
          <template #default="{ row }">
            <span v-if="row.is_primary" class="status-dot status-dot--success">是</span>
            <span v-else class="text-tertiary text-sm">否</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑联系人' : '新建联系人'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="姓名" required><el-input v-model="form.name" placeholder="例如：张三" /></el-form-item>
        <el-form-item label="职位"><el-input v-model="form.title" placeholder="例如：技术总监" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" placeholder="例如：13800138000" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" placeholder="例如：zhangsan@example.com" /></el-form-item>
        <el-form-item label="主要联系人"><el-switch v-model="form.is_primary" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getContacts, createContact, updateContact, deleteContact } from '@/api/customer'

const route = useRoute()
const router = useRouter()
const customerId = route.params.id as string
const list = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', title: '', phone: '', email: '', is_primary: false })

onMounted(() => loadData())

const loadData = async () => {
  loading.value = true
  try { list.value = await getContacts(customerId) } catch { /* ignore */ } finally { loading.value = false }
}

const openDialog = (row?: any) => {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, title: row.title, phone: row.phone, email: row.email, is_primary: row.is_primary })
  } else {
    editingId.value = null
    Object.assign(form, { name: '', title: '', phone: '', email: '', is_primary: false })
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingId.value) await updateContact(customerId, editingId.value, form)
    else await createContact(customerId, form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } catch { /* ignore */ }
}

const handleDelete = async (id: string) => {
  try { await deleteContact(customerId, id); ElMessage.success('删除成功'); loadData() } catch { /* ignore */ }
}
</script>

<style scoped lang="scss">
</style>