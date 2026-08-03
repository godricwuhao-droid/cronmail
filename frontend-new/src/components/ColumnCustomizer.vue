<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="列设置"
    width="480px"
    :close-on-click-modal="false"
  >
    <div class="column-customizer">
      <!-- 列显示/隐藏 -->
      <div class="section">
        <div class="section-title">显示/隐藏列</div>
        <div class="column-list">
          <div
            v-for="col in columns"
            :key="col.key"
            class="column-item"
          >
            <ElIcon class="drag-handle"><Operation /></ElIcon>
            <ElCheckbox
              :model-value="col.visible"
              @change="(val: boolean) => $emit('toggle', col.key, val as boolean)"
            >
              {{ col.label }}
            </ElCheckbox>
            <ElTag v-if="col.pinned" size="small" type="warning">置顶</ElTag>
          </div>
        </div>
      </div>

      <!-- 列顺序 -->
      <div class="section">
        <div class="section-title">列顺序</div>
        <div class="column-order">
          <div
            v-for="(key, index) in columnOrder"
            :key="key"
            class="order-item"
            :class="{ pinned: pinnedKeys.includes(key) }"
          >
            <span class="order-index">{{ index + 1 }}</span>
            <span class="order-label">{{ getColumnLabel(key) }}</span>
            <ElIcon class="drag-handle"><Operation /></ElIcon>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <ElButton @click="handleReset">重置默认</ElButton>
      <ElButton type="primary" @click="emit('update:visible', false)">确定</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { Operation } from '@element-plus/icons-vue'

interface Column {
  key: string
  label: string
  visible: boolean
  pinned: boolean
}

const props = defineProps<{
  visible: boolean
  columns: Column[]
  columnOrder: string[]
  pinnedKeys: string[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  toggle: [key: string, visible: boolean]
  reset: []
}>()

const getColumnLabel = (key: string) => {
  return props.columns.find((c) => c.key === key)?.label || key
}

const handleReset = () => {
  emit('reset')
}
</script>

<style scoped>
.column-customizer {
  max-height: 500px;
  overflow-y: auto;
}

.section {
  margin-bottom: 24px;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  margin-bottom: 12px;
}

.column-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.column-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f7f8fa;
  border-radius: 8px;
  transition: background 0.15s;
}

.column-item:hover {
  background: #eef0f4;
}

.drag-handle {
  color: #c0c4cc;
  cursor: grab;
}

.order-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f7f8fa;
  border-radius: 8px;
  transition: background 0.15s;
}

.order-item:hover {
  background: #eef0f4;
}

.order-item.pinned {
  background: #fff7e6;
  border: 1px solid #ffe58f;
}

.order-index {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1677ff;
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.order-item.pinned .order-index {
  background: #faad14;
}

.order-label {
  flex: 1;
  font-size: 13px;
  color: #4e5969;
}
</style>