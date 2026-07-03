<script setup lang="ts">
/**
 * 内部同事管理页
 *
 * 路由：/system/colleagues
 *
 * 业务说明：
 *  - 与客户联系人共用 /api/contacts 接口，通过 type=colleague 区分
 *  - 创建时不传 customer_id（后端默认为 null）
 *  - 与客户联系人数据完全隔离
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import {
  createContact,
  deleteContact,
  getContacts,
  updateContact,
  type Contact,
  type ContactCreatePayload,
  type ContactUpdatePayload,
} from '@/api/modules/contact'

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<Contact[]>([])
const total = ref(0)

const query = reactive({
  page: 1,
  page_size: 20,
})

async function fetchList() {
  loading.value = true
  try {
    const res = await getContacts({
      type: 'colleague',
      page: query.page,
      page_size: query.page_size,
    })
    // 软删除过滤：只展示启用的
    list.value = res.items.filter((c) => c.is_active)
    // 注：后端 list_contacts 不过滤 is_active，total 包含已停用的，前端过滤后展示
    total.value = res.total
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  query.page = page
  fetchList()
}

function handleSizeChange(size: number) {
  query.page_size = size
  query.page = 1
  fetchList()
}

// ============================================================
// 弹窗表单
// ============================================================
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  name: '',
  email: '',
  phone: '',
  department: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { max: 128, message: '长度不能超过 128 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  phone: [{ max: 32, message: '长度不能超过 32 个字符', trigger: 'blur' }],
  department: [{ max: 128, message: '长度不能超过 128 个字符', trigger: 'blur' }],
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  form.name = ''
  form.email = ''
  form.phone = ''
  form.department = ''
  dialogVisible.value = true
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

function openEditDialog(row: Contact) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.name = row.name
  form.email = row.email
  form.phone = row.phone ?? ''
  form.department = row.department ?? ''
  dialogVisible.value = true
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      // 关键：新建同事不传 customer_id
      const payload: ContactCreatePayload = {
        customer_id: null,
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || undefined,
        department: form.department.trim() || undefined,
      }
      await createContact(payload)
      ElMessage.success('内部同事创建成功')
    } else if (editingId.value) {
      const payload: ContactUpdatePayload = {
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() ? form.phone.trim() : null,
        department: form.department.trim() ? form.department.trim() : null,
      }
      await updateContact(editingId.value, payload)
      ElMessage.success('内部同事更新成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已统一处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Contact) {
  try {
    await deleteContact(row.id)
    ElMessage.success('已删除（状态置为 inactive）')
    if (list.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    fetchList()
  } catch (e) {
    // 错误已统一处理
  }
}

onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-area">
            <span class="title">
              <el-icon><UserFilled /></el-icon>
              内部同事管理
            </span>
            <el-tag type="info" effect="plain">与客户联系人数据隔离</el-tag>
          </div>
          <el-button type="primary" @click="openCreateDialog">+ 新建同事</el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        style="width: 100%"
        empty-text="暂无内部同事"
      >
        <el-table-column prop="name" label="姓名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="phone" label="电话" min-width="140">
          <template #default="{ row }">
            <span v-if="row.phone">{{ row.phone }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" min-width="140">
          <template #default="{ row }">
            <span v-if="row.department">{{ row.department }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="light" size="small">
              {{ row.is_active ? '启用' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-popconfirm
              title="确定删除该同事？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button size="small" link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建内部同事' : '编辑内部同事'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱地址" maxlength="256" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" placeholder="选填" maxlength="32" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="form.department" placeholder="选填" maxlength="128" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.title-area {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.muted {
  color: #c9cdd4;
}
</style>
