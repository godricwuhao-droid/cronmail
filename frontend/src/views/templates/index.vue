<script setup lang="ts">
/**
 * 邮件模板 - 列表页
 *
 * 功能：
 *  - 分页 + 筛选
 *  - 触发类型 tag 颜色区分
 *  - 启用/停用切换（编辑页内操作）
 *  - 新建 / 编辑 / 删除
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Search } from '@element-plus/icons-vue'
import {
  deleteTemplate,
  getTemplates,
  updateTemplate,
  type TemplateListItem,
  type TemplateListParams,
  type TriggerType,
} from '@/api/modules/template'
import { TRIGGER_TYPE_LABEL, TRIGGER_TYPE_TAG } from '@/lib/template'

const router = useRouter()

const loading = ref(false)
const list = ref<TemplateListItem[]>([])
const total = ref(0)

const searchText = ref('')
const triggerFilter = ref<TriggerType | ''>('')
// 启用状态过滤：'1' = 启用，'0' = 停用，'' = 全部
const activeFilter = ref<'' | '1' | '0'>('')

const pagination = reactive({
  page: 1,
  page_size: 20,
})

const TRIGGER_OPTIONS: Array<{ label: string; value: TriggerType }> = [
  { label: '开通通知', value: 'provision' },
  { label: '临期提醒', value: 'expiry_warning' },
  { label: '回收通知', value: 'reclaim' },
]

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
    const params: TemplateListParams = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (triggerFilter.value) params.trigger_type = triggerFilter.value
    if (activeFilter.value === '1') params.is_active = true
    else if (activeFilter.value === '0') params.is_active = false
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const res = await getTemplates(params)
    list.value = res.items
    total.value = res.total
  } catch (e) {
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

function goCreate() {
  router.push({ name: 'TemplateCreate' })
}
function goEdit(row: TemplateListItem) {
  router.push({ name: 'TemplateEdit', params: { id: row.id } })
}

async function handleDelete(row: TemplateListItem) {
  try {
    await deleteTemplate(row.id)
    ElMessage.success('模板已删除')
    if (list.value.length === 1 && pagination.page > 1) pagination.page -= 1
    fetchList()
  } catch (e) {
    // 错误已统一处理
  }
}

/**
 * 切换模板启用状态
 * 后端互斥规则：启用某模板时，同 trigger_type 的其他模板会自动被停用
 */
async function toggleActive(row: TemplateListItem, active: boolean) {
  try {
    await updateTemplate(row.id, { is_active: active })
    row.is_active = active
    // 启用时，刷新列表以反映其他模板被自动停用
    if (active) {
      await fetchList()
    }
    ElMessage.success(active ? '已启用' : '已停用')
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
            <el-icon><Message /></el-icon>
            邮件模板
          </span>
          <el-button type="primary" @click="goCreate">+ 新建模板</el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-select
          v-model="triggerFilter"
          placeholder="触发类型"
          clearable
          style="width: 160px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="opt in TRIGGER_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select
          v-model="activeFilter"
          placeholder="启用状态"
          clearable
          style="width: 140px"
          @change="handleFilterChange"
        >
          <el-option label="已启用" value="1" />
          <el-option label="已停用" value="0" />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="搜索模板名称"
          clearable
          style="width: 240px"
          @input="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="fetchList">刷新</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        style="width: 100%"
        empty-text="暂无模板"
      >
        <el-table-column prop="name" label="模板名称" min-width="200" />
        <el-table-column label="触发类型" width="140">
          <template #default="{ row }">
            <el-tag :type="TRIGGER_TYPE_TAG[row.trigger_type as TriggerType]" effect="light" size="small">
              {{ TRIGGER_TYPE_LABEL[row.trigger_type as TriggerType] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject_tpl" label="主题模板" min-width="240" show-overflow-tooltip />
        <el-table-column label="是否启用" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80" align="center" />
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="goEdit(row)">编辑</el-button>
            <el-button
              v-if="row.is_active"
              size="small"
              type="warning"
              link
              @click="toggleActive(row, false)"
            >停用</el-button>
            <el-button
              v-else
              size="small"
              type="success"
              link
              @click="toggleActive(row, true)"
            >启用</el-button>
            <el-popconfirm
              title="确认删除？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

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
  flex-wrap: wrap;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
