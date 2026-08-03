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
import { UserFilled, Back, Notebook } from '@element-plus/icons-vue'
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

onMounted(() => {
  fetchCustomer()
  fetchList()
  fetchContracts()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-area">
            <el-button :icon="Back" text @click="goBack">返回客户列表</el-button>
            <span class="title">
              <el-icon><UserFilled /></el-icon>
              联系人管理
            </span>
            <span v-if="customer" class="customer-subtitle">
              — {{ customer.name }}
            </span>
            <el-tag v-else-if="!customerLoading" type="danger" effect="plain">客户不存在</el-tag>
            <template v-if="customer?.business_types?.length">
              <el-tag
                v-for="bt in customer.business_types"
                :key="bt"
                size="small"
                effect="plain"
                type="primary"
              >
                {{ bt }}
              </el-tag>
            </template>
          </div>
          <el-button type="primary" :disabled="!customer" @click="openCreateDialog">
            + 新建联系人
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        style="width: 100%"
        empty-text="该客户下暂无联系人"
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
              title="确定删除该联系人？"
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

    <!-- 合同列表 -->
    <el-card shadow="never" style="margin-top: 16px;" v-loading="contractsLoading">
      <template #header>
        <span class="title">
          <el-icon><Notebook /></el-icon>
          合同列表
        </span>
      </template>
      <el-table
        :data="customerContracts"
        border
        stripe
        style="width: 100%"
        empty-text="该客户下暂无合同"
        size="small"
      >
        <el-table-column prop="name" label="合同名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="合同类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="plain"
              :type="row.contract_type === '算力租赁' ? 'primary' : row.contract_type === '算力服务' ? 'success' : 'warning'"
            >
              {{ row.contract_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contract_no" label="合同编号" min-width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.status && row.status !== '-'"
              size="small"
              :type="row.status === 'active' ? 'success' : row.status === 'expiring' ? 'warning' : row.status === 'expired' ? 'danger' : 'info'"
            >
              {{ row.status === 'active' ? '生效中' : row.status === 'expiring' ? '临期' : row.status === 'expired' ? '已到期' : row.status === 'reclaimed' ? '已回收' : row.status }}
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
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="$router.push({ name: row.route_name, params: { id: row.id } })">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建联系人' : '编辑联系人'"
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
.customer-subtitle {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
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
