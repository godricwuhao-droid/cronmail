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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Refresh, RefreshLeft, Search } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
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
  { label: '到期提醒', value: 'expiry_notice' },
  { label: '回收通知', value: 'reclaim' },
]

const hasFilters = computed(
  () => !!(searchText.value.trim() || triggerFilter.value || activeFilter.value),
)
const emptyDescription = computed(() =>
  hasFilters.value ? '未找到匹配模板' : '暂无模板',
)

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

function clearFilters() {
  searchText.value = ''
  triggerFilter.value = ''
  activeFilter.value = ''
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
  if (!(await confirmDelete('确定删除该模板？'))) return
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
    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><Message /></el-icon>
          邮件模板
        </span>
        <el-button type="primary" @click="goCreate">+ 新建模板</el-button>
      </div>

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
        <el-button :icon="Refresh" :disabled="loading" @click="fetchList">刷新</el-button>
        <el-button :icon="RefreshLeft" :disabled="!hasFilters" @click="clearFilters">重置</el-button>
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
            <el-empty :description="emptyDescription" :image-size="72" />
          </div>
        </template>
        <el-table-column prop="name" label="模板名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="col-name-link" @click="goEdit(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="触发类型" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="TRIGGER_TYPE_TAG[row.trigger_type as TriggerType]" size="small">
              {{ TRIGGER_TYPE_LABEL[row.trigger_type as TriggerType] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject_tpl" label="主题模板" min-width="240" show-overflow-tooltip />
        <el-table-column label="是否启用" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80" align="center" />
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            <span class="col-datetime">{{ formatDateTime(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
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
              <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
            </div>
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
    </div>
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
.col-name-link {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
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
.col-datetime {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
</style>
