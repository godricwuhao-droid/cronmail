<script setup lang="ts">
/**
 * 合同管理 - 列表页
 *
 * 功能：
 *  - 分页 + 多条件筛选（合同名称模糊搜索、客户、状态）
 *  - 状态用 el-tag 颜色区分
 *  - 行内操作：详情、编辑、删除（带确认）
 *  - 「+ 新建合同」按钮跳转 /contracts/create
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Search } from '@element-plus/icons-vue'
import {
  deleteContract,
  listContracts,
  type ContractItem,
  type ContractListParams,
  type ContractStatus,
} from '@/api/modules/contract'
import { getCustomers, type Customer } from '@/api/modules/customer'
import {
  CONTRACT_BILLING_MODEL_LABEL,
  CONTRACT_STATUS_LABEL,
  CONTRACT_STATUS_TAG,
} from '@/lib/contract'

const router = useRouter()

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<ContractItem[]>([])
const total = ref(0)

const searchText = ref('')
const statusFilter = ref<ContractStatus | ''>('')
const customerFilter = ref('')

const pagination = reactive({
  page: 1,
  page_size: 20,
})

// 客户下拉（仅展示 active 客户）
const customerOptions = ref<Customer[]>([])
async function loadCustomerOptions() {
  try {
    const res = await getCustomers({ page: 1, page_size: 100 })
    customerOptions.value = res.items.filter((c) => c.status === 'active')
  } catch {
    // 错误已统一处理
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    fetchList()
  }, 300)
}

function handleFilterChange() {
  pagination.page = 1
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params: ContractListParams = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (customerFilter.value) params.customer_id = customerFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const res = await listContracts(params)
    list.value = res.items
    total.value = res.total
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchList()
}

function handleSizeChange(size: number) {
  pagination.page_size = size
  pagination.page = 1
  fetchList()
}

// ============================================================
// 行操作
// ============================================================
function goDetail(row: ContractItem) {
  router.push({ name: 'ContractDetail', params: { id: row.id } })
}

function goEdit(row: ContractItem) {
  router.push({ name: 'ContractEdit', params: { id: row.id } })
}

function goCreate() {
  router.push({ name: 'ContractCreate' })
}

async function handleDelete(row: ContractItem) {
  try {
    await deleteContract(row.id)
    ElMessage.success('合同已删除')
    if (list.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    fetchList()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 展示辅助
// ============================================================
function statusLabel(s?: string | null) {
  if (!s) return '-'
  return CONTRACT_STATUS_LABEL[s as ContractStatus] ?? s
}
function statusTagType(s?: string | null) {
  if (!s) return 'info'
  return CONTRACT_STATUS_TAG[s as ContractStatus] ?? 'info'
}
function billingLabel(s?: string | null) {
  if (!s) return '-'
  return CONTRACT_BILLING_MODEL_LABEL[s] ?? s
}
function formatDate(s?: string | null) {
  if (!s) return '-'
  return s.length >= 10 ? s.slice(0, 10) : s
}

onMounted(() => {
  loadCustomerOptions()
  fetchList()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Document /></el-icon>
            合同管理
          </span>
          <el-button type="primary" @click="goCreate">+ 新建合同</el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="toolbar">
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 140px"
          @change="handleFilterChange"
        >
          <el-option label="生效中" value="active" />
          <el-option label="临期" value="expiring" />
          <el-option label="已到期" value="expired" />
          <el-option label="已回收" value="reclaimed" />
        </el-select>
        <el-select
          v-model="customerFilter"
          placeholder="客户"
          clearable
          filterable
          style="width: 200px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="c in customerOptions"
            :key="c.id"
            :label="c.name"
            :value="c.id"
          />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="按合同名称搜索"
          clearable
          style="width: 260px"
          @input="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button @click="fetchList">刷新</el-button>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        row-key="id"
        border
        stripe
        style="width: 100%"
        empty-text="暂无合同"
      >
        <el-table-column prop="name" label="合同名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="客户" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.customer_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="contract_no" label="合同编号" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.contract_no">{{ row.contract_no }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="开始日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.start_date) }}
          </template>
        </el-table-column>
        <el-table-column label="到期日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.end_date) }}
          </template>
        </el-table-column>
        <el-table-column label="计费方式" width="100">
          <template #default="{ row }">
            {{ billingLabel(row.billing_model) }}
          </template>
        </el-table-column>
        <el-table-column label="设备数" width="80" align="center">
          <template #default="{ row }">
            <span>{{ row.rental_count ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="goDetail(row)">详情</el-button>
            <el-button size="small" link type="primary" @click="goEdit(row)">编辑</el-button>
            <el-popconfirm
              title="确定删除该合同？关联设备不会被删除"
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

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.muted {
  color: #c0c4cc;
}
</style>
