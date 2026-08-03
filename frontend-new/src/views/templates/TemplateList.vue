<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">邮件模板</h1>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card" @click="statusFilter = ''" :class="{ active: !statusFilter }">
        <div class="stat-label">全部模板</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'active'" :class="{ active: statusFilter === 'active' }">
        <div class="stat-label">已启用</div>
        <div class="stat-value" style="color: #52C41A;">{{ stats.active }}</div>
      </div>
      <div class="stat-card" @click="statusFilter = 'inactive'" :class="{ active: statusFilter === 'inactive' }">
        <div class="stat-label">已禁用</div>
        <div class="stat-value" style="color: #86909C;">{{ stats.inactive }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">HTML 模板</div>
        <div class="stat-value" style="color: #1677FF;">{{ stats.html }}</div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="page-toolbar">
      <div class="page-toolbar-left">
        <el-input
          v-model="keyword"
          placeholder="例如：模板名称、邮件主题"
          clearable
          style="width: 320px"
          @input="onSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px; margin-left: 12px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="启用" value="active" />
          <el-option label="禁用" value="inactive" />
        </el-select>
        <el-select v-model="typeFilter" placeholder="内容类型" clearable style="width: 140px; margin-left: 12px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="HTML" value="html" />
          <el-option label="文本" value="text" />
        </el-select>
      </div>
      <div class="page-toolbar-right">
        <el-button :icon="Setting" @click="showColumnCustomizer = true">列设置</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
        <el-button type="primary" :icon="Plus" @click="router.push('/templates/create')">创建模板</el-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedRows.length > 0" class="batch-bar">
      <span class="batch-text">已选择 {{ selectedRows.length }} 项</span>
      <el-button type="danger" text @click="handleBatchDelete">批量删除</el-button>
      <el-button text @click="selectedRows = []">取消选择</el-button>
    </div>

    <!-- 表格 -->
    <div class="content-card" style="padding: 0;">
      <el-table
        :data="list"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="onSelectionChange"
        @sort-change="onSortChange"
      >
        <el-table-column v-if="visibleColumns.some(c => c.key === 'selection')" type="selection" width="48" align="center" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'name')" prop="name" label="模板名称" min-width="180">
          <template #default="{ row }">
            <span class="template-name" @click="router.push(`/templates/${row.id}/edit`)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'subject')" prop="subject" label="邮件主题" min-width="240" show-overflow-tooltip />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'content_type')" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.content_type === 'html' ? '' : 'info'" size="small" effect="light">
              {{ row.content_type === 'html' ? 'HTML' : '文本' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'is_active')" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="light">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="visibleColumns.some(c => c.key === 'created_at')" prop="created_at" label="创建时间" width="180" sortable="custom" />
        <el-table-column v-if="visibleColumns.some(c => c.key === 'updated_at')" prop="updated_at" label="更新时间" width="180" sortable="custom" />
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/templates/${row.id}/edit`)">编辑</el-button>
            <el-button link type="primary" @click="handlePreview(row)">预览</el-button>
            <el-popconfirm title="确定删除该模板？此操作不可恢复。" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!loading && list.length === 0" description="暂无模板数据" style="padding: 60px 20px;">
        <el-button type="primary" @click="router.push('/templates/create')">创建模板</el-button>
      </el-empty>

      <!-- 分页 -->
      <div v-if="list.length > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 列自定义对话框 -->
    <ColumnCustomizer
      v-model:visible="showColumnCustomizer"
      :columns="columnStates"
      :column-order="columnOrder"
      :pinned-keys="pinnedKeys"
      @toggle="toggleColumn"
      @reset="resetColumns"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Setting, Download, Plus } from '@element-plus/icons-vue'
import { getTemplates, deleteTemplate } from '@/api/template'
import ColumnCustomizer from '@/components/ColumnCustomizer.vue'
import { useColumnCustomization, useExportExcel } from '@/composables/useTable'

const router = useRouter()

// 数据
const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')
const typeFilter = ref('')
const selectedRows = ref<any[]>([])

// 搜索防抖
const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null
const onSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
}

// 列自定义
const defaultColumns = [
  { key: 'selection', label: '选择', visible: false, pinned: false },
  { key: 'name', label: '模板名称', visible: true, pinned: true },
  { key: 'subject', label: '邮件主题', visible: true, pinned: false },
  { key: 'content_type', label: '类型', visible: true, pinned: false },
  { key: 'is_active', label: '状态', visible: true, pinned: false },
  { key: 'created_at', label: '创建时间', visible: true, pinned: false },
  { key: 'updated_at', label: '更新时间', visible: true, pinned: false },
]

const {
  columnStates,
  columnOrder,
  visibleColumns,
  pinnedKeys,
  toggleColumn,
  resetColumns,
} = useColumnCustomization(defaultColumns, 'template-columns')

const showColumnCustomizer = ref(false)

// 统计
const stats = ref({
  total: 0,
  active: 0,
  inactive: 0,
  html: 0,
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (statusFilter.value) params.is_active = statusFilter.value === 'active'
    if (typeFilter.value) params.content_type = typeFilter.value

    const res: any = await getTemplates(params)
    list.value = res.items || res
    total.value = res.total || 0

    // 更新统计
    stats.value.total = total.value
    stats.value.active = list.value.filter((t: any) => t.is_active).length
    stats.value.inactive = list.value.filter((t: any) => !t.is_active).length
    stats.value.html = list.value.filter((t: any) => t.content_type === 'html').length
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

// 排序
const onSortChange = ({ prop, order }: { prop: string; order: string }) => {
  loadData()
}

// 选择变化
const onSelectionChange = (rows: any[]) => {
  selectedRows.value = rows
}

// 预览
const handlePreview = (row: any) => {
  router.push(`/templates/${row.id}/preview`)
}

// 删除
const handleDelete = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除该模板？此操作不可恢复。', '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    await deleteTemplate(id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* ignore */ }
}

// 批量删除
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个模板？此操作不可恢复。`, '批量删除', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    for (const row of selectedRows.value) {
      await deleteTemplate(row.id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    loadData()
  } catch { /* ignore */ }
}

// 导出 Excel
const { exportExcel } = useExportExcel(list, defaultColumns.filter(c => c.key !== 'selection'), '邮件模板列表')
const handleExport = () => {
  if (list.value.length === 0) {
    ElMessage.warning('暂无数据可导出')
    return
  }
  exportExcel()
  ElMessage.success('导出成功')
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: #1677ff;
    box-shadow: 0 2px 8px rgba(22, 119, 255, 0.08);
  }

  &.active {
    border-color: #1677ff;
    background: #f0f7ff;
  }
}

.stat-label {
  font-size: 13px;
  color: #86909C;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2329;
  line-height: 1;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  background: #e6f4ff;
  border: 1px solid #91caff;
  border-radius: 8px;
  margin-bottom: 12px;
}

.batch-text {
  font-size: 13px;
  color: #1677ff;
  font-weight: 500;
}

.template-name {
  color: #1677ff;
  cursor: pointer;
  font-weight: 500;

  &:hover {
    text-decoration: underline;
  }
}

.pagination-wrapper {
  padding: 16px 20px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--color-border-light);
}
</style>