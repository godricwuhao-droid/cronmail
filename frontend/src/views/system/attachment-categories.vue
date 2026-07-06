<script setup lang="ts">
/**
 * 附件分类管理页（系统配置）
 *
 * 功能：
 *  - 三个 tab 切换合同类型
 *  - 展示分类列表 + 子项
 *  - 增删改分类和子项
 *  - 上移/下移排序
 *  - 软删除
 */
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  FolderOpened,
  Plus,
  Edit,
  Delete,
  Top,
  Bottom,
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
  type ContractType,
  type CreateCategoryPayload,
  type UpdateCategoryPayload,
  type CreateCategoryItemPayload,
  type UpdateCategoryItemPayload,
} from '@/api/modules/attachment'
import { CONTRACT_TYPE_OPTIONS } from '@/lib/contract'

// ============================================================
// 状态
// ============================================================
const activeTab = ref<ContractType>('compute_leasing')
const loading = ref(false)
const categories = ref<AttachmentCategoryConfig[]>([])
const expandedCategories = ref<Set<string>>(new Set())

// ============================================================
// 数据加载
// ============================================================
async function fetchCategories() {
  loading.value = true
  try {
    const res = await listAttachmentCategories(activeTab.value)
    categories.value = res.items
  } catch {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

function handleTabChange(tab: ContractType) {
  activeTab.value = tab
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
  try {
    if (editingCategoryId.value) {
      const payload: UpdateCategoryPayload = {
        name: categoryForm.value.name.trim(),
        code: categoryForm.value.code.trim(),
        sort_order: categoryForm.value.sort_order,
      }
      await updateAttachmentCategory(editingCategoryId.value, payload)
      ElMessage.success('分类已更新')
    } else {
      const payload: CreateCategoryPayload = {
        contract_type: activeTab.value,
        name: categoryForm.value.name.trim(),
        code: categoryForm.value.code.trim(),
        sort_order: categoryForm.value.sort_order,
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
  try {
    await ElMessageBox.confirm(
      `确定删除分类「${cat.name}」？已有关联数据不受影响。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
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
  try {
    await ElMessageBox.confirm(
      `确定删除子项「${item.name}」？已有关联数据不受影响。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
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

onMounted(() => {
  fetchCategories()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><FolderOpened /></el-icon>
            附件分类管理
          </span>
        </div>
      </template>

      <!-- Tab 切换合同类型 -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane
          v-for="opt in CONTRACT_TYPE_OPTIONS"
          :key="opt.value"
          :label="opt.label"
          :name="opt.value"
        />
      </el-tabs>

      <!-- 操作栏 -->
      <div class="toolbar">
        <el-button type="primary" :icon="Plus" @click="openCreateCategory">
          新建分类
        </el-button>
      </div>

      <!-- 分类列表 -->
      <div v-loading="loading">
        <div v-if="categories.length === 0" class="empty-state">
          <el-empty description="暂无分类，请新建" />
        </div>

        <div
          v-for="(cat, catIdx) in categories"
          :key="cat.id"
          class="category-card"
        >
          <!-- 分类头部 -->
          <div class="cat-header">
            <div class="cat-header-left" @click="toggleExpand(cat.id)" style="cursor: pointer; flex: 1;">
              <el-icon
                class="expand-icon"
                :class="{ rotated: !isExpanded(cat.id) }"
              >
                <ArrowDown />
              </el-icon>
              <span class="cat-name">{{ cat.name }}</span>
              <el-tag size="small" type="info" style="margin-left: 8px;">{{ cat.code }}</el-tag>
              <span class="cat-meta">排序: {{ cat.sort_order }}</span>
            </div>
            <div class="cat-header-right">
              <el-button size="small" :icon="Top" :disabled="catIdx === 0" @click="handleMoveCategoryUp(cat, catIdx)" />
              <el-button size="small" :icon="Bottom" :disabled="catIdx >= categories.length - 1" @click="handleMoveCategoryDown(cat, catIdx)" />
              <el-button size="small" :icon="Edit" @click="openEditCategory(cat)">编辑</el-button>
              <el-button size="small" :icon="Delete" type="danger" @click="handleDeleteCategory(cat)">删除</el-button>
            </div>
          </div>

          <!-- 子项列表 -->
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
                <el-button size="small" :icon="Edit" link type="primary" @click="openEditItem(item, cat.id)">编辑</el-button>
                <el-button size="small" :icon="Delete" link type="danger" @click="handleDeleteItem(item)">删除</el-button>
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
    </el-card>

    <!-- 分类弹窗 -->
    <el-dialog
      v-model="categoryDialogVisible"
      :title="categoryDialogTitle"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form :model="categoryForm" label-width="80px" @submit.prevent>
        <el-form-item label="名称" required>
          <el-input v-model="categoryForm.name" placeholder="如 合同协议" maxlength="50" />
        </el-form-item>
        <el-form-item label="编码" required>
          <el-input v-model="categoryForm.code" placeholder="如 contract_agreement" maxlength="50" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="categoryForm.sort_order" :min="1" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCategory">保存</el-button>
      </template>
    </el-dialog>

    <!-- 子项弹窗 -->
    <el-dialog
      v-model="itemDialogVisible"
      :title="itemDialogTitle"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form :model="itemForm" label-width="100px" @submit.prevent>
        <el-form-item label="名称" required>
          <el-input v-model="itemForm.name" placeholder="如 合同扫描件" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="itemForm.description" placeholder="如 合同扫描件PDF" maxlength="200" />
        </el-form-item>
        <el-form-item label="期望类型">
          <el-select v-model="itemForm.expected_type" placeholder="选择文件类型" clearable style="width: 100%">
            <el-option label="PDF" value="pdf" />
            <el-option label="图片" value="image" />
            <el-option label="Excel" value="excel" />
            <el-option label="Word" value="word" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="itemForm.sort_order" :min="1" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.empty-state {
  padding: 40px 0;
}

.category-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}
.cat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #ebeef5;
}
.cat-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cat-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.expand-icon {
  transition: transform 0.2s;
  color: var(--text-secondary);
}
.expand-icon.rotated {
  transform: rotate(-90deg);
}
.cat-name {
  font-weight: 600;
  font-size: 15px;
}
.cat-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: 8px;
}

/* 子项 */
.cat-items {
  padding: 8px 16px 12px;
}
.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-top: 6px;
  background: #fafbfc;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}
.item-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.item-name {
  font-weight: 500;
  font-size: 14px;
}
.item-type-tag {
  font-size: 11px;
  color: var(--text-secondary);
  background: #e5e7eb;
  padding: 1px 6px;
  border-radius: 3px;
}
.item-desc {
  font-size: 12px;
  color: var(--text-secondary);
}
.item-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.add-item-row {
  margin-top: 8px;
  padding-left: 12px;
}
</style>
