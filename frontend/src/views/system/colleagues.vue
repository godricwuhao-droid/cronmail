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
import { Refresh, UserFilled, InfoFilled } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
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
  if (!(await confirmDelete('确定删除该同事？'))) return
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
    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><UserFilled /></el-icon>
          内部同事管理
        </span>
        <div class="header-actions">
          <el-button :icon="Refresh" :disabled="loading" @click="fetchList">刷新</el-button>
          <el-button type="primary" @click="openCreateDialog">+ 新建同事</el-button>
        </div>
      </div>

      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>内部同事与客户联系人数据隔离，可用于邮件抄送等场景。</span>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        row-key="id"
        stripe
        style="width: 100%"
      >
        <template #empty>
          <div class="table-empty">
            <el-empty description="暂无内部同事" :image-size="72" />
          </div>
        </template>
        <el-table-column prop="name" label="姓名" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.name" class="col-name">{{ row.name }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.email" class="col-secondary">{{ row.email }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" min-width="140">
          <template #default="{ row }">
            <span v-if="row.phone">{{ row.phone }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" min-width="140">
          <template #default="{ row }">
            <span v-if="row.department">{{ row.department }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" link type="primary" @click="openEditDialog(row)">
                编辑
              </el-button>
              <el-divider direction="vertical" />
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
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
    </div>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建内部同事' : '编辑内部同事'"
      width="560px"
      destroy-on-close
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>
          {{
            dialogMode === 'create'
              ? '创建后可在邮件抄送等场景中选择该同事；与客户联系人相互独立。'
              : '可更新同事姓名、联系方式与部门信息。'
          }}
        </span>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <div class="dialog-section">
          <div class="dialog-section-title">基本信息</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="姓名" prop="name">
                <el-input
                  v-model="form.name"
                  placeholder="请输入姓名"
                  maxlength="128"
                  show-word-limit
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="部门" prop="department">
                <el-input v-model="form.department" placeholder="选填" maxlength="128" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
        <div class="dialog-section">
          <div class="dialog-section-title">联系方式</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="form.email" placeholder="请输入邮箱地址" maxlength="256" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="电话" prop="phone">
                <el-input v-model="form.phone" placeholder="选填" maxlength="32" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ dialogMode === 'create' ? '创建' : '保存' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.action-buttons {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.action-buttons :deep(.el-button + .el-button) {
  margin-left: 0;
}
.action-buttons :deep(.el-divider--vertical) {
  margin: 0 8px;
  height: 12px;
  border-color: #e5e7eb;
}
.col-name {
  color: var(--text-primary);
  font-weight: 600;
}
.col-secondary {
  color: var(--text-secondary);
}
.col-muted {
  color: #c0c4cc;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
