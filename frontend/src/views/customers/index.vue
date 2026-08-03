<script setup lang="ts">
/**
 * 客户管理 - 客户列表
 *
 * 功能：
 *  - 分页 + 模糊搜索
 *  - 仅展示 active 客户（已软删除的 inactive 不显示）
 *  - 新建 / 编辑客户（弹窗表单）
 *  - 软删除（el-popconfirm 二次确认）
 *  - 客户名称 / 「联系人」按钮均跳转联系人管理页
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import {
  createCustomer,
  deleteCustomer,
  getCustomers,
  updateCustomer,
  type Customer,
  type CustomerCreatePayload,
  type CustomerUpdatePayload,
} from '@/api/modules/customer'
import {
  listContracts,
  type ContractItem,
} from '@/api/modules/contract'
import {
  CONTRACT_STATUS_LABEL,
  CONTRACT_STATUS_TAG,
} from '@/lib/contract'
import type { ContractStatus } from '@/api/modules/contract'

const router = useRouter()

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
  business_types: [],
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入客户名称', trigger: 'blur' },
    { max: 128, message: '长度不能超过 128 个字符', trigger: 'blur' },
  ],
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  form.name = ''
  form.business_types = []
  dialogVisible.value = true
  // 重置校验状态
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

function openEditDialog(row: Customer) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.name = row.name
  form.business_types = row.business_types ?? []
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
      const payload: CustomerCreatePayload = {
        name: form.name.trim(),
        business_types: form.business_types?.length ? form.business_types : undefined,
      }
      await createCustomer(payload)
      ElMessage.success('客户创建成功')
    } else if (editingId.value) {
      const payload: CustomerUpdatePayload = {
        name: form.name.trim(),
        business_types: form.business_types?.length ? form.business_types : undefined,
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

// ============================================================
// 合同统计弹窗
// ============================================================
const contractDialogVisible = ref(false)
const selectedCustomer = ref<Customer | null>(null)
const customerContracts = ref<ContractItem[]>([])
const loadingContracts = ref(false)

async function showContractDialog(customer: Customer) {
  selectedCustomer.value = customer
  contractDialogVisible.value = true
  loadingContracts.value = true
  try {
    const res = await listContracts({ customer_id: customer.id, page_size: 100 })
    customerContracts.value = res.items
  } catch {
    customerContracts.value = []
  } finally {
    loadingContracts.value = false
  }
}

function goContractDetail(contractId: string) {
  contractDialogVisible.value = false
  router.push({ name: 'ContractDetail', params: { id: contractId } })
}

function statusLabel(s?: string | null) {
  if (!s) return '-'
  return CONTRACT_STATUS_LABEL[s as ContractStatus] ?? s
}

function statusTagType(s?: string | null) {
  if (!s) return 'info'
  return CONTRACT_STATUS_TAG[s as ContractStatus] ?? 'info'
}

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

function goContacts(row: Customer) {
  router.push(`/customers/${row.id}/contacts`)
}

function handleDeleteConfirm(row: Customer) {
  ElMessageBox.confirm(
    `确认删除客户「${row.name}」？此操作会将客户状态置为 inactive。`,
    '删除确认',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    },
  )
    .then(() => handleDelete(row))
    .catch(() => {
      // 用户取消
    })
}

onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page-container customer-page">
    <el-card shadow="never" class="customer-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <span class="title-bar" />
            <span>客户管理</span>
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
        class="customer-table"
        style="width: 100%"
        empty-text="暂无客户"
        :header-cell-style="{
          background: '#FAFAFA',
          color: '#303133',
          fontWeight: 600,
        }"
      >
        <el-table-column label="客户名称" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="col-customer-name" @click="goContacts(row)">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="业务类型" min-width="180" align="center">
          <template #default="{ row }">
            <div v-if="row.business_types && row.business_types.length" class="business-types">
              <el-tag
                v-for="bt in row.business_types"
                :key="bt"
                effect="plain"
                type="primary"
                size="small"
              >
                {{ bt }}
              </el-tag>
            </div>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="contact_count" label="联系人" width="100" align="center">
          <template #default="{ row }">
            <span class="col-number">{{ row.contact_count ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="合同统计" min-width="220" align="center">
          <template #default="{ row }">
            <div class="contract-stat" @click.stop="showContractDialog(row)">
              <span class="stat-total">{{ row.contract_stats?.total ?? 0 }}</span>
              <span class="stat-label">合同总数</span>
              <div class="stat-breakdown">
                <span class="stat-item">
                  <span class="dot dot-green" />
                  生效 {{ row.contract_stats?.active ?? 0 }}
                </span>
                <span class="stat-item">
                  <span class="dot dot-orange" />
                  临期 {{ row.contract_stats?.expired ?? 0 }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="col-time">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" link type="primary" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" link type="primary" @click="goContacts(row)">联系人</el-button>
              <el-button size="small" link type="danger" @click="handleDeleteConfirm(row)">删除</el-button>
            </div>
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
        <el-form-item label="业务类型">
          <el-checkbox-group v-model="form.business_types">
            <el-checkbox value="算力租赁" label="算力租赁" />
            <el-checkbox value="算力服务" label="算力服务" />
            <el-checkbox value="卫星数据" label="卫星数据" />
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 合同列表弹窗 -->
    <el-dialog
      v-model="contractDialogVisible"
      :title="'合同列表 - ' + (selectedCustomer?.name ?? '')"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-table
        :data="customerContracts"
        size="small"
        stripe
        v-loading="loadingContracts"
        empty-text="暂无合同"
        :header-cell-style="{
          background: '#FAFAFA',
          color: '#303133',
          fontWeight: 600,
        }"
      >
        <el-table-column prop="name" label="合同名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="contract_no" label="合同编号" width="160">
          <template #default="{ row }">
            <span v-if="row.contract_no">{{ row.contract_no }}</span>
            <span v-else class="col-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="到期日期" width="120">
          <template #default="{ row }">
            {{ row.end_date?.slice(0, 10) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="goContractDetail(row.id)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ============================================================
   页面容器
   ============================================================ */
.customer-page {
  padding: 4px;
}

/* ============================================================
   卡片
   ============================================================ */
.customer-card {
  border-radius: 4px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12);
  border: none;
}
.customer-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}
.customer-card :deep(.el-card__body) {
  padding: 24px;
}

.card-header {
  display: flex;
  align-items: center;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-bar {
  display: block;
  width: 4px;
  height: 16px;
  background: #1890ff;
  border-radius: 2px;
}

/* ============================================================
   工具栏
   ============================================================ */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

/* ============================================================
   客户名称列
   ============================================================ */
.col-customer-name {
  color: #303133;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}
.col-customer-name:hover {
  color: #409eff;
}

/* ============================================================
   业务类型列
   ============================================================ */
.business-types {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-wrap: wrap;
  width: 100%;
}
.business-types :deep(.el-tag) {
  font-size: 12px;
}

/* ============================================================
   合同统计列（单行展示）
   ============================================================ */
.contract-stat {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 12px;
  white-space: nowrap;
  cursor: pointer;
}
.stat-total {
  font-size: 18px;
  font-weight: bold;
  color: #262626;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  font-size: 12px;
  color: #bfbfbf;
  margin-left: 2px;
}
.stat-breakdown {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #8c8c8c;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.dot-green {
  background: #52c41a;
}
.dot-orange {
  background: #faad14;
}

/* ============================================================
   联系人数量列
   ============================================================ */
.col-number {
  font-variant-numeric: tabular-nums;
  color: #8c8c8c;
}

/* ============================================================
   创建时间列
   ============================================================ */
.col-time {
  color: #8c8c8c;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

/* ============================================================
   操作列
   ============================================================ */
.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

/* ============================================================
   通用
   ============================================================ */
.col-muted {
  color: #c9cdd4;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
