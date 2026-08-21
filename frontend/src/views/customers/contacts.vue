<script setup lang="ts">
/**
 * 联系人管理页
 *
 * 路由：/customers/:id/contacts
 *  - 页面顶部展示客户名称
 *  - 表格列出该客户下的联系人（is_active=true）
 *  - 支持新增 / 编辑 / 软删除
 *  - 展示该客户下的三类合同列表
 */
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, InfoFilled } from '@element-plus/icons-vue'
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
import { getCustomer, type Customer } from '@/api/modules/customer'
import { listContracts, type ContractItem } from '@/api/modules/contract'
import { listSatelliteContracts, type SatelliteContractItem } from '@/api/modules/satellite-contract'
import { listServiceContracts, type ServiceContractItem } from '@/api/modules/service-contract'

const route = useRoute()
const router = useRouter()
const customerId = ref<string>(String(route.params.id || ''))

// ============================================================
// 客户信息
// ============================================================
const customer = ref<Customer | null>(null)
const customerLoading = ref(false)

async function fetchCustomer() {
  if (!customerId.value) return
  customerLoading.value = true
  try {
    customer.value = await getCustomer(customerId.value)
  } catch (e) {
    // 错误已统一处理
  } finally {
    customerLoading.value = false
  }
}

// 路由参数变化时重新拉取（如从其他客户的联系人页跳过来）
watch(
  () => route.params.id,
  (val) => {
    if (val && val !== customerId.value) {
      customerId.value = String(val)
      fetchCustomer()
      fetchList()
      fetchContracts()
    }
  },
)

// ============================================================
// 合同列表
// ============================================================
interface UnifiedContract {
  id: string
  name: string
  contract_type: '算力租赁' | '卫星数据' | '算力服务'
  contract_no: string | null
  status: string
  start_date: string | null
  end_date: string | null
  route_name: string
}

const customerContracts = ref<UnifiedContract[]>([])
const contractsLoading = ref(false)

async function fetchContracts() {
  if (!customerId.value) return
  contractsLoading.value = true
  const result: UnifiedContract[] = []
  try {
    const leasing = await listContracts({ customer_id: customerId.value, page_size: 100 })
    result.push(...leasing.items.map((c: ContractItem) => ({
      id: c.id,
      name: c.name,
      contract_type: '算力租赁' as const,
      contract_no: c.contract_no ?? null,
      status: c.status,
      start_date: c.start_date,
      end_date: c.end_date,
      route_name: 'ContractDetail',
    })))
  } catch { /* 静默处理 */ }
  try {
    const satellite = await listSatelliteContracts({ customer_id: customerId.value, page_size: 100 })
    result.push(...satellite.items.map((c: SatelliteContractItem) => ({
      id: c.id,
      name: c.name,
      contract_type: '卫星数据' as const,
      contract_no: c.contract_no ?? null,
      status: '-',
      start_date: null,
      end_date: null,
      route_name: 'SatelliteContractDetail',
    })))
  } catch { /* 静默处理 */ }
  try {
    const service = await listServiceContracts({ customer_id: customerId.value, page_size: 100 })
    result.push(...service.items.map((c: ServiceContractItem) => ({
      id: c.id,
      name: c.name,
      contract_type: '算力服务' as const,
      contract_no: c.contract_no ?? null,
      status: '-',
      start_date: c.start_date,
      end_date: c.end_date,
      route_name: 'ServiceContractDetail',
    })))
  } catch { /* 静默处理 */ }
  customerContracts.value = result
  contractsLoading.value = false
}

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
  if (!customerId.value) return
  loading.value = true
  try {
    const res = await getContacts({
      customer_id: customerId.value,
      type: 'customer',
      page: query.page,
      page_size: query.page_size,
    })
    // 软删除过滤：只展示启用的联系人
    list.value = res.items.filter((c) => c.is_active)
    // 注：后端 list_contacts 不过滤 is_active，服务端 total 含已停用联系人
    // 这里用当前页实际展示数（list.length）做 total，避免显示错误的分页
    total.value = list.value.length
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
      const payload: ContactCreatePayload = {
        customer_id: customerId.value,
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || undefined,
        department: form.department.trim() || undefined,
      }
      await createContact(payload)
      ElMessage.success('联系人创建成功')
    } else if (editingId.value) {
      const payload: ContactUpdatePayload = {
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() ? form.phone.trim() : null,
        department: form.department.trim() ? form.department.trim() : null,
      }
      await updateContact(editingId.value, payload)
      ElMessage.success('联系人更新成功')
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
  if (!(await confirmDelete('确定删除该联系人？'))) return
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

function goBack() {
  router.push({ name: 'CustomerList' })
}

function goContract(row: UnifiedContract) {
  router.push({ name: row.route_name, params: { id: row.id } })
}

function formatDateTime(s?: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 19)
}

function contractStatusLabel(s: string) {
  if (s === 'active') return '生效中'
  if (s === 'expiring') return '临期'
  if (s === 'expired') return '已到期'
  if (s === 'reclaimed') return '已回收'
  return s
}

function contractStatusTag(s: string) {
  if (s === 'active') return 'success'
  if (s === 'expiring') return 'warning'
  if (s === 'expired') return 'danger'
  return 'info'
}

onMounted(() => {
  fetchCustomer()
  fetchList()
  fetchContracts()
})
</script>

<template>
  <div class="page-container" v-loading="customerLoading">
    <div class="top-bar">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div class="detail-header">
      <div class="header-left">
        <h1 class="header-title">{{ customer?.name || (customerLoading ? '...' : '客户不存在') }}</h1>
        <div class="header-sub">
          <template v-if="customer?.business_types?.length">
            <span class="biz-text">{{ customer.business_types.join('、') }}</span>
          </template>
          <span v-else class="muted">未设置业务类型</span>
        </div>
      </div>
    </div>

    <section class="detail-section">
      <div class="dialog-section-title">基本信息</div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="客户名称">{{ customer?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="业务类型">
          <span v-if="customer?.business_types?.length">{{ customer.business_types.join('、') }}</span>
          <span v-else class="muted">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="联系人">{{ list.length }} 人</el-descriptions-item>
        <el-descriptions-item label="合同数">{{ customerContracts.length }} 份</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(customer?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(customer?.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="detail-section">
      <div class="section-toolbar">
        <div class="dialog-section-title">
          联系人
          <span class="muted">（共 {{ total }} 人）</span>
        </div>
        <el-button type="primary" :disabled="!customer" @click="openCreateDialog">
          + 新建联系人
        </el-button>
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
            <el-empty description="该客户下暂无联系人" :image-size="72" />
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
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" link type="primary" @click="openEditDialog(row)">编辑</el-button>
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
    </section>

    <section class="detail-section" v-loading="contractsLoading">
      <div class="dialog-section-title">
        合同列表
        <span class="muted">（共 {{ customerContracts.length }} 份）</span>
      </div>
      <el-table
        :data="customerContracts"
        stripe
        style="width: 100%"
      >
        <template #empty>
          <div class="table-empty">
            <el-empty description="该客户下暂无合同" :image-size="72" />
          </div>
        </template>
        <el-table-column label="合同名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tooltip content="点击查看详情" placement="top" :show-after="300">
              <span class="col-name-link" @click="goContract(row)">{{ row.name }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="合同类型" width="110" align="center">
          <template #default="{ row }">
            <span>{{ row.contract_type }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="contract_no" label="合同编号" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.contract_no">{{ row.contract_no }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.status && row.status !== '-'"
              size="small"
              :type="contractStatusTag(row.status)"
            >
              {{ contractStatusLabel(row.status) }}
            </el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="起止日期" min-width="200" align="center">
          <template #default="{ row }">
            <span v-if="row.start_date || row.end_date">
              {{ row.start_date ? row.start_date.slice(0, 10) : '-' }} ~ {{ row.end_date ? row.end_date.slice(0, 10) : '-' }}
            </span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="goContract(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建联系人' : '编辑联系人'"
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
              ? `将为客户「${customer?.name || ''}」添加联系人，可用于合同通知与邮件发送。`
              : '可更新联系人姓名、邮箱、电话与部门。'
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
          <div class="dialog-section-title">基础信息</div>
          <el-form-item label="姓名" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入姓名"
              maxlength="128"
              show-word-limit
              clearable
            />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="form.email"
              placeholder="请输入邮箱地址"
              maxlength="256"
              clearable
            />
          </el-form-item>
        </div>
        <div class="dialog-section">
          <div class="dialog-section-title">其他信息</div>
          <el-form-item label="电话" prop="phone">
            <el-input v-model="form.phone" placeholder="选填" maxlength="32" clearable />
          </el-form-item>
          <el-form-item label="部门" prop="department">
            <el-input v-model="form.department" placeholder="选填" maxlength="128" clearable />
          </el-form-item>
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
.top-bar {
  margin-bottom: 0;
}

.detail-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  border-radius: 8px;
}
.header-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}
.header-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 14px;
  flex-wrap: wrap;
}
.biz-text {
  color: var(--text-primary);
  font-size: 14px;
}

.detail-section {
  padding: 20px;
  border-radius: 8px;
}

.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}
.section-toolbar .dialog-section-title {
  margin: 0;
  padding-top: 0;
  padding-right: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.detail-section > .dialog-section-title {
  margin-bottom: 12px;
}

.col-name {
  color: var(--text-primary);
  font-weight: 600;
}
.col-name-link {
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
}
.col-name-link:hover {
  color: var(--primary-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.col-secondary {
  color: var(--text-secondary);
}
.col-muted {
  color: #c0c4cc;
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

.muted {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 400;
  opacity: 0.85;
}
</style>
