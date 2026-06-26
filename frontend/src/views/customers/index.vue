<script setup lang="ts">
/**
 * 客户管理 - 客户列表
 *
 * 功能：
 *  - 分页 + 模糊搜索
 *  - 仅展示 active 客户（已软删除的 inactive 不显示）
 *  - 新建 / 编辑客户（弹窗表单）
 *  - 软删除（el-popconfirm 二次确认）
 *  - 启用 / 停用切换
 *  - 客户名称 / 「联系人」按钮均跳转联系人管理页
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { UserFilled, Search } from '@element-plus/icons-vue'
import {
  createCustomer,
  deleteCustomer,
  getCustomers,
  updateCustomer,
  type Customer,
  type CustomerCreatePayload,
  type CustomerUpdatePayload,
} from '@/api/modules/customer'
import { getRentals } from '@/api/modules/rental'

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<Customer[]>([])
const total = ref(0)

const query = reactive({
  search: '',
  page: 1,
  page_size: 20,
})

// 防抖搜索
let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    query.page = 1
    fetchList()
  }, 300)
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getCustomers({
      search: query.search || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    // 防御性兜底：兼容后端可能的多层包装（如 { data: { items, total } }）
    const payload = (res as any)?.items ? res : (res as any)?.data?.items ? (res as any).data : res
    // 列表只展示 active 客户，过滤掉已软删除（inactive）的记录
    const items = (payload.items ?? []).filter((c: any) => c.status !== 'inactive')
    list.value = items
    total.value = items.length
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[CustomerList] raw response:', res, '→ parsed:', payload)
    }
  } catch (e) {
    // 错误已由 axios 拦截器统一提示
    // eslint-disable-next-line no-console
    console.error('[CustomerList] fetch failed:', e)
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
// 弹窗表单（新建 / 编辑共用）
// ============================================================
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive<CustomerCreatePayload>({
  name: '',
  code: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入客户名称', trigger: 'blur' },
    { max: 128, message: '长度不能超过 128 个字符', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入客户编码', trigger: 'blur' },
    { max: 64, message: '长度不能超过 64 个字符', trigger: 'blur' },
  ],
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  form.name = ''
  form.code = ''
  dialogVisible.value = true
  // 重置校验状态
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

/* 编辑功能暂时停用：操作列调整为 联系人 / 启用·停用 / 删除
function openEditDialog(row: Customer) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.name = row.name
  form.code = row.code
  dialogVisible.value = true
  setTimeout(() => formRef.value?.clearValidate(), 0)
}
*/

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
      const payload: CustomerCreatePayload = {
        name: form.name.trim(),
        code: form.code.trim(),
      }
      await createCustomer(payload)
      ElMessage.success('客户创建成功')
    } else if (editingId.value) {
      const payload: CustomerUpdatePayload = {
        name: form.name.trim(),
        code: form.code.trim(),
      }
      await updateCustomer(editingId.value, payload)
      ElMessage.success('客户更新成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已统一处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Customer) {
  try {
    await deleteCustomer(row.id)
    ElMessage.success('已删除（状态置为 inactive）')
    // 若删除的是当前页最后一条，自动回退一页
    if (list.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    fetchList()
  } catch (e) {
    // 错误已统一处理
  }
}

async function toggleStatus(row: Customer) {
  const newStatus = row.status === 'active' ? 'inactive' : 'active'
  const actionLabel = newStatus === 'inactive' ? '停用' : '启用'

  // 停用时检查该客户下的活跃租赁（租赁中），有关联则阻断操作
  if (newStatus === 'inactive') {
    try {
      const res = await getRentals({ customer_id: row.id, status: '租赁中', page: 1, page_size: 1 })
      const activeTotal = res?.total ?? 0
      if (activeTotal > 0) {
        await ElMessageBox.alert(
          `该客户下有 ${activeTotal} 条活跃租赁记录（租赁中），请先处理关联的租赁记录后再停用。`,
          '无法停用',
          { confirmButtonText: '知道了', type: 'warning' },
        )
        return
      }
    } catch (e: any) {
      // 校验失败时阻断操作，避免漏判导致数据不一致
      ElMessage.warning('无法校验关联租赁记录，请稍后重试')
      console.error('[CustomerList] check active rentals failed:', e)
      return
    }
  }

  // 启用 / 停用 二次确认
  try {
    await ElMessageBox.confirm(
      `确认${actionLabel}客户「${row.name}」？`,
      `${actionLabel}确认`,
      {
        confirmButtonText: actionLabel,
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    // 用户取消
    return
  }

  try {
    await updateCustomer(row.id, { status: newStatus })
    row.status = newStatus
    if (newStatus === 'inactive') {
      // 停用后从列表移除（与列表只展示 active 一致）
      list.value = list.value.filter((c) => c.id !== row.id)
    }
    ElMessage.success(newStatus === 'active' ? '已启用' : '已停用')
  } catch (e) {
    // 错误已统一处理
  }
}

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
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
          <span class="title">
            <el-icon><UserFilled /></el-icon>
            客户管理
          </span>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="toolbar">
        <el-input
          v-model="query.search"
          placeholder="按客户名称搜索"
          clearable
          style="width: 280px"
          @input="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="openCreateDialog">+ 新建客户</el-button>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        style="width: 100%"
        empty-text="暂无客户"
      >
        <el-table-column label="客户名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" :underline="'never'" @click="$router.push(`/customers/${row.id}/contacts`)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="客户编码" min-width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'active' ? 'success' : 'info'"
              effect="light"
              size="small"
            >
              {{ row.status === 'active' ? '启用' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contact_count" label="联系人数量" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.contact_count" type="info" effect="plain" size="small">
              {{ row.contact_count }}
            </el-tag>
            <span v-else class="muted">0</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="$router.push(`/customers/${row.id}/contacts`)">联系人</el-button>
            <el-button
              v-if="row.status === 'active'"
              size="small" type="warning" link
              @click="toggleStatus(row)"
            >停用</el-button>
            <el-button
              v-else
              size="small" type="success" link
              @click="toggleStatus(row)"
            >启用</el-button>
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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
      :title="dialogMode === 'create' ? '新建客户' : '编辑客户'"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="客户名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入客户名称" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="客户编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入客户编码（唯一标识）" maxlength="64" show-word-limit />
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
}
.card-header .title {
  font-size: 16px;
  font-weight: 600;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
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
