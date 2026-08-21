<script setup lang="ts">
/**
 * 项目管理附件配置页（两层结构：项目类型 → 附件分类）
 *
 * 功能：
 *  - 顶部：项目类型标签列表 + 新建按钮
 *  - 选中项目类型后展示该类型下的附件分类
 *  - 分类/子项的 CRUD 和排序
 */
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { confirmDelete } from '@/lib/confirm'
import {
  FolderOpened,
  Plus,
  Edit,
  Delete,
  Top,
  Bottom,
  ArrowDown,
  InfoFilled,
} from '@element-plus/icons-vue'
import {
  listAttachmentCategories,
  createAttachmentCategory,
  updateAttachmentCategory,
  deleteAttachmentCategory,
  reorderAttachmentCategory,
  createAttachmentCategoryItem,
  updateAttachmentCategoryItem,
  deleteAttachmentCategoryItem,
  reorderAttachmentCategoryItem,
  type AttachmentCategoryConfig,
  type AttachmentCategoryItem,
  type CreateCategoryPayload,
  type UpdateCategoryPayload,
  type CreateCategoryItemPayload,
  type UpdateCategoryItemPayload,
} from '@/api/modules/attachment'
import {
  getProjectTypes,
  createProjectType,
  updateProjectType,
  deleteProjectType,
  type ProjectTypeResponse,
} from '@/api/modules/project'

// ============================================================
// 状态
// ============================================================
const loading = ref(false)
const categories = ref<AttachmentCategoryConfig[]>([])
const expandedCategories = ref<Set<string>>(new Set())

// 项目类型列表
const projectTypes = ref<ProjectTypeResponse[]>([])
// 当前选中的项目类型 ID
const selectedTypeId = ref<string>('')

// 当前选中的项目类型对象
const selectedType = computed(() => {
  if (selectedTypeId.value === '') return null
  return projectTypes.value.find((t) => t.id === selectedTypeId.value) || null
})

// 当前选中的 project_type 名称（传给分类 API）
const currentProjectTypeName = computed(() => {
  const t = selectedType.value
  return t ? t.name : ''
})

// 当前选中的项目类型显示标签
const currentTypeLabel = computed(() => {
  const t = selectedType.value
  return t ? t.name : '未知类型'
})

// ============================================================
// 项目类型 CRUD
// ============================================================
async function loadProjectTypes() {
  try {
    projectTypes.value = await getProjectTypes()
  } catch {
    // 静默失败
  }
}

const typeDialogVisible = ref(false)
const typeDialogTitle = ref('')
const typeForm = ref({ name: '', sort_order: 1 })
const editingTypeId = ref<string | null>(null)

function openCreateType() {
  editingTypeId.value = null
  typeDialogTitle.value = '新建项目类型'
  typeForm.value = { name: '', sort_order: projectTypes.value.length + 1 }
  typeDialogVisible.value = true
}

function openEditType(type: ProjectTypeResponse) {
  editingTypeId.value = type.id
  typeDialogTitle.value = '编辑项目类型'
  typeForm.value = { name: type.name, sort_order: type.sort_order }
  typeDialogVisible.value = true
}

async function handleSaveType() {
  if (!typeForm.value.name.trim()) {
    ElMessage.warning('名称不能为空')
    return
  }
  try {
    if (editingTypeId.value) {
      await updateProjectType(editingTypeId.value, {
        name: typeForm.value.name.trim(),
        sort_order: typeForm.value.sort_order,
      })
      ElMessage.success('项目类型已更新')
    } else {
      await createProjectType({
        name: typeForm.value.name.trim(),
        sort_order: typeForm.value.sort_order,
      })
      ElMessage.success('项目类型已创建')
    }
    typeDialogVisible.value = false
    await loadProjectTypes()
  } catch {
    // 错误已统一处理
  }
}

async function handleDeleteType(type: ProjectTypeResponse) {
  if (!(await confirmDelete(`确定删除项目类型「${type.name}」？删除后该类型下的附件分类不受影响。`))) return
  try {
    await deleteProjectType(type.id)
    ElMessage.success('项目类型已删除')
    if (selectedTypeId.value === type.id) {
      selectedTypeId.value = projectTypes.value.length > 0 ? projectTypes.value[0].id : ''
      fetchCategories()
    }
    await loadProjectTypes()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 分类数据加载
// ============================================================
async function fetchCategories() {
  loading.value = true
  try {
    const pt = currentProjectTypeName.value
    const res = await listAttachmentCategories('project', pt)
    categories.value = res.items
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

function handleTypeSelect(typeId: string) {
  selectedTypeId.value = typeId
  expandedCategories.value.clear()
  fetchCategories()
}

function toggleExpand(catId: string) {
  if (expandedCategories.value.has(catId)) {
    expandedCategories.value.delete(catId)
  } else {
    expandedCategories.value.add(catId)
  }
}

function isExpanded(catId: string): boolean {
  return expandedCategories.value.has(catId)
}

// ============================================================
// 分类 CRUD
// ============================================================
const categoryDialogVisible = ref(false)
const categoryDialogTitle = ref('')
const categoryForm = ref({
  name: '',
  code: '',
  sort_order: 1,
})
const editingCategoryId = ref<string | null>(null)

function openCreateCategory() {
  editingCategoryId.value = null
  categoryDialogTitle.value = '新建分类'
  categoryForm.value = {
    name: '',
    code: '',
    sort_order: categories.value.length + 1,
  }
  categoryDialogVisible.value = true
}

function openEditCategory(cat: AttachmentCategoryConfig) {
  editingCategoryId.value = cat.id
  categoryDialogTitle.value = '编辑分类'
  categoryForm.value = {
    name: cat.name,
    code: cat.code,
    sort_order: cat.sort_order,
  }
  categoryDialogVisible.value = true
}

async function handleSaveCategory() {
  if (!categoryForm.value.name.trim() || !categoryForm.value.code.trim()) {
    ElMessage.warning('名称和编码不能为空')
    return
  }

  const projectType = currentProjectTypeName.value

  try {
    if (editingCategoryId.value) {
      const payload: UpdateCategoryPayload = {
        name: categoryForm.value.name.trim(),
        code: categoryForm.value.code.trim(),
        sort_order: categoryForm.value.sort_order,
        project_type: projectType,
      }
      await updateAttachmentCategory(editingCategoryId.value, payload)
      ElMessage.success('分类已更新')
    } else {
      const payload: CreateCategoryPayload = {
        contract_type: 'project',
        name: categoryForm.value.name.trim(),
        code: categoryForm.value.code.trim(),
        sort_order: categoryForm.value.sort_order,
        project_type: projectType,
      }
      await createAttachmentCategory(payload)
      ElMessage.success('分类已创建')
    }
    categoryDialogVisible.value = false
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

async function handleDeleteCategory(cat: AttachmentCategoryConfig) {
  if (!(await confirmDelete(`确定删除分类「${cat.name}」？已有关联数据不受影响。`))) return
  try {
    await deleteAttachmentCategory(cat.id)
    ElMessage.success('分类已删除')
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

async function handleMoveCategoryUp(cat: AttachmentCategoryConfig, index: number) {
  if (index === 0) return
  const newOrder = categories.value[index - 1].sort_order
  try {
    await reorderAttachmentCategory(cat.id, newOrder)
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

async function handleMoveCategoryDown(cat: AttachmentCategoryConfig, index: number) {
  if (index >= categories.value.length - 1) return
  const newOrder = categories.value[index + 1].sort_order
  try {
    await reorderAttachmentCategory(cat.id, newOrder)
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

// ============================================================
// 子项 CRUD
// ============================================================
const itemDialogVisible = ref(false)
const itemDialogTitle = ref('')
const itemForm = ref({
  name: '',
  description: '',
  expected_type: '',
  sort_order: 1,
})
const editingItemId = ref<string | null>(null)
const currentCategoryId = ref<string>('')

function openCreateItem(catId: string, currentItems: AttachmentCategoryItem[]) {
  editingItemId.value = null
  currentCategoryId.value = catId
  itemDialogTitle.value = '新建子项'
  itemForm.value = {
    name: '',
    description: '',
    expected_type: '',
    sort_order: currentItems.length + 1,
  }
  itemDialogVisible.value = true
}

function openEditItem(item: AttachmentCategoryItem, catId: string) {
  editingItemId.value = item.id
  currentCategoryId.value = catId
  itemDialogTitle.value = '编辑子项'
  itemForm.value = {
    name: item.name,
    description: item.description || '',
    expected_type: item.expected_type || '',
    sort_order: item.sort_order,
  }
  itemDialogVisible.value = true
}

async function handleSaveItem() {
  if (!itemForm.value.name.trim()) {
    ElMessage.warning('名称不能为空')
    return
  }
  try {
    if (editingItemId.value) {
      const payload: UpdateCategoryItemPayload = {
        name: itemForm.value.name.trim(),
        description: itemForm.value.description.trim() || undefined,
        expected_type: itemForm.value.expected_type.trim() || undefined,
        sort_order: itemForm.value.sort_order,
      }
      await updateAttachmentCategoryItem(editingItemId.value, payload)
      ElMessage.success('子项已更新')
    } else {
      const payload: CreateCategoryItemPayload = {
        name: itemForm.value.name.trim(),
        description: itemForm.value.description.trim() || undefined,
        expected_type: itemForm.value.expected_type.trim() || undefined,
        sort_order: itemForm.value.sort_order,
      }
      await createAttachmentCategoryItem(currentCategoryId.value, payload)
      ElMessage.success('子项已创建')
    }
    itemDialogVisible.value = false
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

async function handleDeleteItem(item: AttachmentCategoryItem) {
  if (!(await confirmDelete(`确定删除子项「${item.name}」？已有关联数据不受影响。`))) return
  try {
    await deleteAttachmentCategoryItem(item.id)
    ElMessage.success('子项已删除')
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

async function handleMoveItemUp(item: AttachmentCategoryItem, items: AttachmentCategoryItem[], index: number) {
  if (index === 0) return
  const newOrder = items[index - 1].sort_order
  try {
    await reorderAttachmentCategoryItem(item.id, newOrder)
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

async function handleMoveItemDown(item: AttachmentCategoryItem, items: AttachmentCategoryItem[], index: number) {
  if (index >= items.length - 1) return
  const newOrder = items[index + 1].sort_order
  try {
    await reorderAttachmentCategoryItem(item.id, newOrder)
    fetchCategories()
  } catch {
    // 错误已统一处理
  }
}

onMounted(async () => {
  await loadProjectTypes()
  if (projectTypes.value.length > 0) {
    selectedTypeId.value = projectTypes.value[0].id
  }
  fetchCategories()
})
</script>

<template>
  <div class="page-container">
    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><FolderOpened /></el-icon>
          项目配置
        </span>
        <div class="header-actions">
          <el-button :icon="Plus" @click="openCreateType">
            新建项目类型
          </el-button>
          <el-button
            type="primary"
            :icon="Plus"
            :disabled="!selectedType"
            @click="openCreateCategory"
          >
            新建分类
          </el-button>
        </div>
      </div>

      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>先选择项目类型，再维护该类型下的附件分类与子项。</span>
      </div>

      <!-- 项目类型 -->
      <div class="dialog-section">
        <div class="section-toolbar">
          <div class="dialog-section-title">项目类型</div>
          <div v-if="selectedType" class="type-ops">
            <el-button size="small" link type="primary" :icon="Edit" @click="openEditType(selectedType)">
              编辑
            </el-button>
            <el-divider direction="vertical" />
            <el-button size="small" link type="danger" :icon="Delete" @click="handleDeleteType(selectedType)">
              删除
            </el-button>
          </div>
        </div>
        <div class="type-tags-row">
          <el-tag
            v-for="t in projectTypes"
            :key="t.id"
            :type="selectedTypeId === t.id ? 'primary' : 'info'"
            :effect="selectedTypeId === t.id ? 'dark' : 'plain'"
            size="large"
            class="type-tag"
            @click="handleTypeSelect(t.id)"
          >
            {{ t.name }}
          </el-tag>
          <span v-if="projectTypes.length === 0" class="muted">暂无项目类型，请先新建</span>
        </div>
      </div>

      <!-- 附件分类 -->
      <div class="dialog-section">
        <div class="dialog-section-title">
          附件分类
          <span class="muted">（{{ currentTypeLabel }}）</span>
        </div>

        <div v-loading="loading" class="category-list">
          <div v-if="!selectedType" class="table-empty">
            <el-empty description="请先选择或新建项目类型" :image-size="72" />
          </div>
          <div v-else-if="categories.length === 0" class="table-empty">
            <el-empty :description="`「${currentTypeLabel}」下暂无分类，请新建`" :image-size="72" />
          </div>

          <div
            v-for="(cat, catIdx) in categories"
            :key="cat.id"
            class="category-block"
          >
            <div class="cat-header">
              <div class="cat-header-left" @click="toggleExpand(cat.id)">
                <el-icon
                  class="expand-icon"
                  :class="{ rotated: !isExpanded(cat.id) }"
                >
                  <ArrowDown />
                </el-icon>
                <span class="cat-name">{{ cat.name }}</span>
                <el-tag size="small" type="info">{{ cat.code }}</el-tag>
                <span class="cat-meta">排序 {{ cat.sort_order }}</span>
              </div>
              <div class="cat-header-right">
                <el-button size="small" :icon="Top" :disabled="catIdx === 0" @click="handleMoveCategoryUp(cat, catIdx)" />
                <el-button size="small" :icon="Bottom" :disabled="catIdx >= categories.length - 1" @click="handleMoveCategoryDown(cat, catIdx)" />
                <el-divider direction="vertical" />
                <el-button size="small" link type="primary" :icon="Edit" @click="openEditCategory(cat)">编辑</el-button>
                <el-button size="small" link type="danger" :icon="Delete" @click="handleDeleteCategory(cat)">删除</el-button>
              </div>
            </div>

            <div v-show="isExpanded(cat.id)" class="cat-items">
              <div
                v-for="(item, itemIdx) in cat.items"
                :key="item.id"
                class="item-row"
              >
                <div class="item-info">
                  <span class="item-name">{{ item.name }}</span>
                  <span v-if="item.expected_type" class="item-type-tag">
                    {{ item.expected_type.toUpperCase() }}
                  </span>
                  <span v-if="item.description" class="item-desc">{{ item.description }}</span>
                </div>
                <div class="item-actions">
                  <el-button size="small" :icon="Top" :disabled="itemIdx === 0" @click="handleMoveItemUp(item, cat.items, itemIdx)" />
                  <el-button size="small" :icon="Bottom" :disabled="itemIdx >= cat.items.length - 1" @click="handleMoveItemDown(item, cat.items, itemIdx)" />
                  <el-divider direction="vertical" />
                  <el-button size="small" link type="primary" @click="openEditItem(item, cat.id)">编辑</el-button>
                  <el-button size="small" link type="danger" @click="handleDeleteItem(item)">删除</el-button>
                </div>
              </div>
              <div class="add-item-row">
                <el-button size="small" :icon="Plus" link type="primary" @click="openCreateItem(cat.id, cat.items)">
                  添加子项
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 项目类型弹窗 -->
    <el-dialog
      v-model="typeDialogVisible"
      :title="typeDialogTitle"
      width="560px"
      destroy-on-close
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>
          {{
            editingTypeId
              ? '可更新项目类型名称与排序。'
              : '项目类型用于区分不同业务线下的附件分类配置。'
          }}
        </span>
      </div>
      <el-form :model="typeForm" label-position="top" class="dialog-form" @submit.prevent>
        <div class="dialog-section">
          <div class="dialog-section-title">类型信息</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="16">
              <el-form-item label="名称" required>
                <el-input v-model="typeForm.name" placeholder="如 算力服务合同" maxlength="100" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-form-item label="排序">
                <el-input-number v-model="typeForm.sort_order" :min="1" :max="999" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="typeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveType">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 分类弹窗 -->
    <el-dialog
      v-model="categoryDialogVisible"
      :title="categoryDialogTitle"
      width="560px"
      destroy-on-close
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>
          {{
            editingCategoryId
              ? '可更新分类名称、编码与排序。'
              : `将为「${currentTypeLabel}」创建附件分类；编码建议使用英文下划线风格。`
          }}
        </span>
      </div>
      <el-form :model="categoryForm" label-position="top" class="dialog-form" @submit.prevent>
        <div class="dialog-section">
          <div class="dialog-section-title">分类信息</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="名称" required>
                <el-input v-model="categoryForm.name" placeholder="如 合同协议" maxlength="50" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="编码" required>
                <el-input v-model="categoryForm.code" placeholder="如 contract_agreement" maxlength="50" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="排序">
                <el-input-number v-model="categoryForm.sort_order" :min="1" :max="999" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="categoryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveCategory">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 子项弹窗 -->
    <el-dialog
      v-model="itemDialogVisible"
      :title="itemDialogTitle"
      width="560px"
      destroy-on-close
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>
          {{
            editingItemId
              ? '可更新子项名称、描述、期望类型与排序。'
              : '子项用于约束该分类下可上传的附件条目。'
          }}
        </span>
      </div>
      <el-form :model="itemForm" label-position="top" class="dialog-form" @submit.prevent>
        <div class="dialog-section">
          <div class="dialog-section-title">子项信息</div>
          <el-row :gutter="16">
            <el-col :span="24">
              <el-form-item label="名称" required>
                <el-input v-model="itemForm.name" placeholder="如 合同扫描件" maxlength="50" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="描述">
                <el-input v-model="itemForm.description" placeholder="如 合同扫描件PDF" maxlength="200" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="期望类型">
                <el-select v-model="itemForm.expected_type" placeholder="选择文件类型" clearable style="width: 100%">
                  <el-option label="PDF" value="pdf" />
                  <el-option label="图片" value="image" />
                  <el-option label="Excel" value="excel" />
                  <el-option label="Word" value="word" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="排序">
                <el-input-number v-model="itemForm.sort_order" :min="1" :max="999" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="itemDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveItem">保存</el-button>
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
.section-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.section-toolbar .dialog-section-title {
  margin: 0;
  padding-bottom: 0;
  border-bottom: none;
  flex: 1;
}
.section-toolbar .dialog-section-title::before {
  content: '';
  width: 3px;
  height: 13px;
  border-radius: 1px;
  background: var(--primary-color);
  flex-shrink: 0;
}
.type-ops {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.type-ops :deep(.el-divider--vertical),
.cat-header-right :deep(.el-divider--vertical),
.item-actions :deep(.el-divider--vertical) {
  margin: 0 8px;
  height: 12px;
  border-color: #e5e7eb;
}
.type-tags-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.type-tag {
  cursor: pointer;
  user-select: none;
}
.muted {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 400;
}
.category-list {
  min-height: 120px;
}
.category-block + .category-block {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}
.cat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  flex-wrap: wrap;
}
.cat-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}
.cat-header-right {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.expand-icon {
  transition: transform 0.2s;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.expand-icon.rotated {
  transform: rotate(-90deg);
}
.cat-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}
.cat-meta {
  font-size: 12px;
  color: var(--text-secondary);
}
.cat-items {
  padding: 4px 0 8px 24px;
}
.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  flex-wrap: wrap;
}
.item-row:last-of-type {
  border-bottom: none;
}
.item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  flex-wrap: wrap;
}
.item-name {
  font-weight: 500;
  font-size: 13px;
  color: var(--text-primary);
}
.item-type-tag {
  font-size: 11px;
  color: var(--text-secondary);
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 3px;
}
.item-desc {
  font-size: 12px;
  color: var(--text-secondary);
}
.item-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.add-item-row {
  margin-top: 4px;
}
.dialog-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
}
.dialog-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
</style>
