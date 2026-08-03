# 列设置 Pattern（拖拽 + 置顶 + 持久化）

> **目的**：把「列设置弹窗（拖拽排序 + 置顶 + 勾选显示 + 持久化）」的实现模式固化下来，让后续任何列表页可以照搬。
>
> **参考实现**：
> - `frontend/src/views/rentals/index.vue`（设备列表）— 最早引入此 pattern
> - `frontend/src/views/contracts/index.vue`（合同列表）— 复用此 pattern
>
> **设计目标**：
> 1. 三个独立维度——**可见性**、**顺序**、**置顶**——分别持久化到 localStorage
> 2. 用原生 HTML5 Drag & Drop API 实现拖拽排序，**不引入第三方库**
> 3. 置顶列在弹窗中排在前面，与未置顶列用分割线分隔
> 4. 表格用 `v-for` + `v-bind` 动态渲染，特殊列用 `<template #default>` 覆盖

---

## 1. 整体结构

### 1.1 三个 localStorage 键

每个列表页使用**三个独立 key**（命名约定 `{page}_columns` / `{page}_column_order` / `{page}_pinned_columns`）：

| Key | 内容 | 类型 | 用途 |
| --- | --- | --- | --- |
| `{page}_columns` | 可见列的 key 列表 | `string[]` | 决定哪些列渲染、勾选框打勾 |
| `{page}_column_order` | 全部列的 key 列表（按用户拖拽顺序） | `string[]` | 决定列的实际渲染顺序（含隐藏列） |
| `{page}_pinned_columns` | 置顶列的 key 列表 | `string[]` | 决定哪些列排在最前 |

> 三个 key 互不影响，可单独修改。比如只改可见性不会重置顺序。

**已使用此 pattern 的 key**：

- `rental_columns` / `rental_column_order` / `rental_pinned_columns`
- `contract_columns` / `contract_column_order` / `contract_pinned_columns`

### 1.2 状态管理

```typescript
// 可见列（弹窗 checkbox 状态 + 表格是否渲染）
const visibleColumns = ref<string[]>(loadVisibleColumns())

// 列顺序（拖拽后的实际顺序，影响表格列渲染顺序）
const columnOrder = ref<string[]>(loadColumnOrder())

// 置顶列（用 ref 数组，置顶越早的越靠前）
const pinnedColumns = ref<string[]>(loadPinned())

// 拖拽状态（仅在拖拽过程中使用，不持久化）
const dragKey = ref<string>('')
const dragOverKey = ref<string>('')
```

### 1.3 关键计算属性

**`orderedColumns`（核心）**：

```typescript
const orderedColumns = computed(() => {
  const all = columnOrder.value
    .map((key) => allColumns.find((c) => c.key === key))
    .filter((c): c is ColumnDef => !!c)
  const pinned = all.filter((c) => isPinned(c.key))
  const unpinned = all.filter((c) => !isPinned(c.key))
  return [...pinned, ...unpinned]
})
```

要点：
- 表格渲染列和弹窗列设置面板**共用同一个 `orderedColumns`**
- 先按 `columnOrder` 排好序，再把置顶的提到最前
- 弹窗里的 `column-divider` 通过比较相邻项的 `isPinned` 状态插入

---

## 2. 拖拽实现要点

### 2.1 使用 HTML5 原生 Drag & Drop API

**为什么不引入第三方库**：
- 项目体量小，原生 API 够用
- 避免引入 `vuedraggable`（依赖 Sortable.js）这类较大依赖
- 列设置场景下，用户拖动的是「静态列表项」，不需要复杂的拖拽反馈

**关键事件**（绑定在 `column-item` div 上）：

| 事件 | 触发时机 | 关键操作 |
| --- | --- | --- |
| `dragstart` | 用户开始拖动 | 设置 `dragKey`、设置 `dataTransfer.effectAllowed = 'move'`、给元素加 `.dragging` 类 |
| `dragover` | 拖动到某个 item 上 | 必须 `e.preventDefault()` 才能触发 drop、设置 `dataTransfer.dropEffect = 'move'`、更新 `dragOverKey` |
| `dragleave` | 离开某个 item | 清空 `dragOverKey`（避免视觉残留） |
| `drop` | 在某个 item 上释放 | 根据 `dragKey` 和 `targetKey` 在 `columnOrder` 中重排 |
| `dragend` | 拖拽结束（无论是否 drop） | 清理 `.dragging` class、清空 `dragKey` 和 `dragOverKey` |

### 2.2 拖拽核心代码

```typescript
function onDragStart(e: DragEvent, key: string) {
  dragKey.value = key
  dragOverKey.value = ''
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    try {
      e.dataTransfer.setData('text/plain', key)
    } catch { /* 某些浏览器不允许 setData */ }
  }
  const el = e.target as HTMLElement | null
  el?.classList.add('dragging')
}

function onDragOver(e: DragEvent, key: string) {
  e.preventDefault()  // 必须，否则 drop 不触发
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  if (key !== dragOverKey.value) dragOverKey.value = key
}

function onDragLeave(key: string) {
  if (dragOverKey.value === key) dragOverKey.value = ''
}

function onDrop(e: DragEvent, targetKey: string) {
  e.preventDefault()
  const from = columnOrder.value.indexOf(dragKey.value)
  const to = columnOrder.value.indexOf(targetKey)
  if (from !== -1 && to !== -1 && from !== to) {
    const arr = [...columnOrder.value]
    arr.splice(from, 1)
    arr.splice(to, 0, dragKey.value)
    columnOrder.value = arr
    persistOrder(arr)
  }
  dragKey.value = ''
  dragOverKey.value = ''
}

function onDragEnd(e: DragEvent) {
  const el = e.target as HTMLElement | null
  el?.classList.remove('dragging')
  dragKey.value = ''
  dragOverKey.value = ''
}
```

### 2.3 视觉反馈 CSS

```css
.column-item {
  cursor: grab;
  transition: background 0.15s;
}
.column-item.dragging {
  opacity: 0.4;  /* 拖动源半透明 */
}
.column-item.drag-over {
  border-top: 2px solid #1e40af;  /* 拖入目标顶部蓝色虚线 */
}
.column-item:active .drag-handle {
  cursor: grabbing;
}
.drag-handle {
  cursor: grab;
  color: #d1d5db;
  user-select: none;
}
```

### 2.4 易踩的坑

1. **`dragover` 必须 `e.preventDefault()`** — 否则浏览器默认行为是「禁止 drop」，drop 事件永远不会触发
2. **`setData` 用 try-catch 包裹** — Firefox 在某些情况下会抛 `InvalidStateError`
3. **`draggable="true"` 必须放在子元素 div 上** — 放在父元素或子元素 input/button 上不生效
4. **`@dragend` 必须监听** — 即便 drop 成功也要清状态，否则 `.dragging` 永久残留

---

## 3. 置顶列实现思路

### 3.1 置顶列的行为

| 维度 | 行为 |
| --- | --- |
| 弹窗面板 | 置顶列排在最前，与未置顶列之间用 `column-divider` 分隔 |
| 表格渲染 | 置顶列在表格中实际排在最前（因为 `orderedColumns` 已经把 pinned 提到前面） |
| 切换 | 点击 📌 按钮：未置顶则置顶（unshift 到 pinned 数组最前）、已置顶则取消置顶 |
| 持久化 | `pinnedColumns` 数组直接 `JSON.stringify` 存到 localStorage |

### 3.2 切换置顶的核心代码

```typescript
function pinColumn(key: string) {
  const idx = pinnedColumns.value.indexOf(key)
  if (idx > -1) {
    pinnedColumns.value.splice(idx, 1)  // 取消置顶
  } else {
    pinnedColumns.value.unshift(key)   // 置顶（放在 pinned 数组最前）
  }
  persistPinned(pinnedColumns.value)
}
function isPinned(key: string) {
  return pinnedColumns.value.includes(key)
}
```

> 多次置顶会形成「后置顶的反而排前」的栈式行为。如需严格的「固定顺序」，可改为 `push(key)`。

### 3.3 弹窗中分割线的渲染

**思路**：在 `orderedColumns` 遍历过程中，如果当前项和前一项的 `isPinned` 状态不同，则插入分割线。

```html
<div class="column-list">
  <template v-for="(col, idx) in orderedColumns" :key="col.key">
    <div
      v-if="idx > 0 && isPinned(col.key) !== isPinned(orderedColumns[idx - 1]?.key || '')"
      class="column-divider"
    />
    <div class="column-item" ...>
      <span class="drag-handle">⠿</span>
      <el-button class="pin-btn" :class="{ active: isPinned(col.key) }" @click="pinColumn(col.key)">
        <el-icon><Top /></el-icon>
      </el-button>
      <el-checkbox :model-value="vis(col.key)" @change="toggleColumn(col.key)">
        {{ col.title }}
      </el-checkbox>
    </div>
  </template>
</div>
```

**条件解析**：
- `idx > 0`：第一项前不插分割线
- `isPinned(col.key) !== isPinned(orderedColumns[idx - 1]?.key || '')`：
  - 当前项置顶 + 前一项未置顶 → 分割线
  - 当前项未置顶 + 前一项置顶 → 分割线
  - 同为置顶或同为未置顶 → 不插分割线

### 3.4 置顶按钮的 CSS

```css
.pin-btn {
  padding: 2px;
  margin-right: 4px;
  font-size: 14px;
  opacity: 0.3;  /* 默认半透明，不抢戏 */
}
.pin-btn:hover,
.pin-btn.active {
  opacity: 1;
  color: var(--primary-color);  /* 激活状态显主色 */
}
```

---

## 4. 持久化模式

### 4.1 写入（持久化）

**三个写入函数**（分别在勾选、拖拽、置顶时调用）：

```typescript
function persistColumns(val: string[]) {
  localStorage.setItem('XXX_columns', JSON.stringify(val))
}
function persistOrder(val: string[]) {
  localStorage.setItem('XXX_column_order', JSON.stringify(val))
}
function persistPinned(val: string[]) {
  localStorage.setItem('XXX_pinned_columns', JSON.stringify(val))
}
```

### 4.2 读取（带默认值兜底 + 兼容性兜底）

**所有 loader 函数的统一模式**：

```typescript
function loadVisibleColumns(): string[] {
  try {
    const raw = localStorage.getItem('XXX_columns')
    if (!raw) return [...DEFAULT_VISIBLE]  // 没存过 → 用默认
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...DEFAULT_VISIBLE]  // 解析失败 → 用默认
    // 关键：过滤掉已不存在的 key
    const valid = parsed.filter(
      (k): k is string => typeof k === 'string' && allColumns.some((c) => c.key === k),
    )
    if (!valid.includes('actions')) valid.push('actions')  // 强制保留 required 列
    return valid
  } catch {
    return [...DEFAULT_VISIBLE]
  }
}
```

**columnOrder 的 loader 额外处理缺失列**（因拖拽后存的顺序可能在新版本中缺少新增的列）：

```typescript
function loadColumnOrder(): string[] {
  try {
    const raw = localStorage.getItem('XXX_column_order')
    if (!raw) return [...DEFAULT_ORDER]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...DEFAULT_ORDER]
    const valid = parsed.filter(
      (k): k is string => typeof k === 'string' && allColumns.some((c) => c.key === k),
    )
    // 缺失列补在尾部（新版本加了列时兼容老数据）
    for (const c of allColumns) {
      if (!valid.includes(c.key)) valid.push(c.key)
    }
    return valid
  } catch {
    return [...DEFAULT_ORDER]
  }
}
```

### 4.3 「重置默认」必须三个都清

```typescript
function resetColumns() {
  visibleColumns.value = [...DEFAULT_VISIBLE]
  columnOrder.value = [...DEFAULT_ORDER]
  pinnedColumns.value = [...DEFAULT_PINNED]
  persistColumns(DEFAULT_VISIBLE)
  persistOrder(DEFAULT_ORDER)
  persistPinned(DEFAULT_PINNED)
  ElMessage.success('已恢复默认列设置')
}
```

### 4.4 required 列的兜底

**所有 loader 都要做**：

```typescript
if (!valid.includes('actions')) valid.push('actions')
```

**`watch(visibleColumns)` 兜底**（防止用户代码意外清空）：

```typescript
watch(
  visibleColumns,
  (val) => {
    if (val.length === 0 || !val.includes('actions')) {
      const fixed = val.length === 0 ? ['actions'] : [...val, 'actions']
      visibleColumns.value = fixed
      persistColumns(fixed)
    }
  },
  { deep: true },
)
```

### 4.5 「至少保留一列」的提示

```typescript
function guardRequired(next: string[]) {
  if (next.length === 0) {
    visibleColumns.value = ['actions']
    ElMessage.warning('至少需要保留一列可见')
    persistColumns(visibleColumns.value)
    return
  }
  const valid = next.filter((k) => allColumns.some((c) => c.key === k))
  if (!valid.includes('actions')) {
    valid.push('actions')
    ElMessage.warning('操作列不可取消')
  }
  visibleColumns.value = valid
  persistColumns(valid)
}
```

---

## 5. 表格动态列渲染

### 5.1 为什么改用 v-for 动态渲染

旧实现（手写每个 `<el-table-column v-if="vis('xxx')">`）的问题：
- 加一列要改 N 个地方
- 列顺序靠代码位置决定，无法被拖拽改变
- 置顶逻辑复杂

新实现（v-for + v-bind）：
- 加一列只需改 `allColumns` 数组 + 加一个 `<template v-else-if>` 分支
- 列顺序由 `orderedColumns` 决定
- 置顶/拖拽逻辑统一在 `orderedColumns` computed

### 5.2 getColumnProps 模式

**作用**：根据 `col.key` 返回 `el-table-column` 需要的 props。

```typescript
type ColumnProps = Record<string, unknown>

function getColumnProps(col: ColumnDef): ColumnProps {
  const key = col.key
  const base: ColumnProps = {}

  // 普通文本列（直接走 prop，无 template）
  if (key === 'name') {
    base.prop = 'name'
    base.label = '合同名称'
    base['min-width'] = 200
    base['show-overflow-tooltip'] = true
  } else if (key === 'customer_name') {
    base.prop = 'customer_name'
    base.label = '客户'
    base['min-width'] = 160
    base['show-overflow-tooltip'] = true
  }
  // ... 其他普通列 ...

  // 特殊列（需要 template，只设 label / width）
  else if (key === 'status') {
    base.label = '状态'
    base.width = 100
  } else if (key === 'actions') {
    base.label = '操作'
    base.width = 260
    base.fixed = 'right'
  }

  return base
}
```

### 5.3 模板用法

```html
<el-table :data="list" v-loading="loading" ...>
  <template v-for="col in orderedColumns" :key="col.key">
    <el-table-column v-if="vis(col.key)" v-bind="getColumnProps(col)">
      <!-- 特殊列才需要 template -->
      <template v-if="col.key === 'name'" #default="{ row }">
        <span>{{ row.name }}{{ row.renewal_seq > 0 ? `(续${row.renewal_seq})` : '' }}</span>
      </template>
      <template v-else-if="col.key === 'status'" #default="{ row }">
        <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
      </template>
      <template v-else-if="col.key === 'actions'" #default="{ row }">
        <el-button @click="goEdit(row)">编辑</el-button>
      </template>
      <!-- 普通列不加 template，会自动用 prop -->
    </el-table-column>
  </template>
</el-table>
```

**重要**：el-table-column 上 `v-bind` 的 props 不会和 `<template #default>` 冲突。如果不写 template，el-table-column 会用 `prop` 自动显示对应字段。

---

## 6. 复用清单

### 6.1 列设置弹窗 HTML 模板片段

```html
<el-popover
  v-model:visible="popoverVisible"
  placement="bottom-end"
  :width="260"
  trigger="click"
  popper-class="XXX-column-popover"  <!-- 改成你的页面前缀 -->
>
  <template #reference>
    <el-button :icon="OperationIcon" :disabled="loading">列设置</el-button>
  </template>
  <div class="column-popover-body">
    <div class="column-popover-header">
      <span>拖拽调整顺序 · 勾选显示</span>
      <el-link type="primary" :underline="false" @click="resetColumns">重置默认</el-link>
    </div>
    <div class="column-list">
      <template v-for="(col, idx) in orderedColumns" :key="col.key">
        <div
          v-if="idx > 0 && isPinned(col.key) !== isPinned(orderedColumns[idx - 1]?.key || '')"
          class="column-divider"
        />
        <div
          class="column-item"
          :class="{
            'drag-over': dragOverKey === col.key && dragKey !== col.key,
            dragging: dragKey === col.key,
          }"
          draggable="true"
          @dragstart="onDragStart($event, col.key)"
          @dragover="onDragOver($event, col.key)"
          @dragleave="onDragLeave(col.key)"
          @drop="onDrop($event, col.key)"
          @dragend="onDragEnd"
        >
          <span class="drag-handle" aria-hidden="true">⠿</span>
          <el-button
            link
            class="pin-btn"
            :class="{ active: isPinned(col.key) }"
            @click="pinColumn(col.key)"
            :title="isPinned(col.key) ? '取消置顶' : '置顶到最前'"
          >
            <el-icon><Top /></el-icon>
          </el-button>
          <el-checkbox
            :model-value="vis(col.key)"
            :disabled="col.required"
            @change="toggleColumn(col.key)"
          >
            {{ col.title }}<span v-if="col.required" class="required-tip">（必选）</span>
          </el-checkbox>
        </div>
      </template>
    </div>
  </div>
</el-popover>
```

### 6.2 列设置弹窗 CSS

```css
<style>
/* Popover 内容（非 scoped 才能作用到 el-popover 内部生成的 DOM） */
.XXX-column-popover .column-popover-body {  /* 改前缀 */
  font-size: 13px;
}
.XXX-column-popover .column-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--text-secondary, #606266);
  font-weight: 600;
}
.XXX-column-popover .column-list {
  max-height: 400px;
  overflow-y: auto;
}
.XXX-column-popover .column-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: grab;
  transition: background 0.15s;
}
.XXX-column-popover .column-item:hover { background: #f3f4f6; }
.XXX-column-popover .column-item.dragging { opacity: 0.4; }
.XXX-column-popover .column-item.drag-over { border-top: 2px solid #1e40af; }
.XXX-column-popover .drag-handle {
  color: #d1d5db;
  font-size: 16px;
  cursor: grab;
  user-select: none;
  line-height: 1;
}
.XXX-column-popover .column-item:active .drag-handle { cursor: grabbing; }
.XXX-column-popover .required-tip {
  color: var(--el-color-info, #909399);
  font-size: 12px;
  margin-left: 4px;
}
.XXX-column-popover .pin-btn {
  padding: 2px;
  margin-right: 4px;
  font-size: 14px;
  opacity: 0.3;
}
.XXX-column-popover .pin-btn:hover,
.XXX-column-popover .pin-btn.active {
  opacity: 1;
  color: var(--primary-color);
}
.XXX-column-popover .column-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 6px;
}
</style>
```

### 6.3 核心 script 函数清单

需要从 `import` 到 `onMounted` 之间复制的全部函数：

```typescript
// 1. 类型定义
interface ColumnDef {
  key: string
  title: string
  default?: boolean
  required?: boolean
}

// 2. 常量（每个页面不同）
const allColumns: ColumnDef[] = [
  { key: 'xxx', title: 'XXX', default: true },
  // ...
  { key: 'actions', title: '操作', default: true, required: true },
]
const STORAGE_KEY = 'XXX_columns'              // 改前缀
const ORDER_STORAGE_KEY = 'XXX_column_order'   // 改前缀
const PIN_STORAGE_KEY = 'XXX_pinned_columns'   // 改前缀
const DEFAULT_VISIBLE: string[] = allColumns.filter(c => c.default).map(c => c.key)
const DEFAULT_ORDER: string[] = allColumns.map(c => c.key)
const DEFAULT_PINNED = ['xxx', 'yyy', 'zzz']    // 按业务选 2-3 个核心列

// 3. 三个 loader（已有 try-catch 模板，照搬）
function loadVisibleColumns(): string[] { ... }
function loadColumnOrder(): string[] { ... }
function loadPinned(): string[] { ... }

// 4. 三个 ref
const visibleColumns = ref<string[]>(loadVisibleColumns())
const columnOrder = ref<string[]>(loadColumnOrder())
const pinnedColumns = ref<string[]>(loadPinned())
const popoverVisible = ref(false)

// 5. 三个 persist
function persistColumns(val: string[]) { ... }
function persistOrder(val: string[]) { ... }
function persistPinned(val: string[]) { ... }

// 6. 核心 computed
const orderedColumns = computed(() => { ... })
const dragKey = ref<string>('')
const dragOverKey = ref<string>('')

// 7. 辅助
function vis(key: string) { return visibleColumns.value.includes(key) }
function isPinned(key: string) { return pinnedColumns.value.includes(key) }
function pinColumn(key: string) { ... }
function toggleColumn(key: string) { ... }
function guardRequired(next: string[]) { ... }
function resetColumns() { ... }

// 8. 拖拽函数（5 个）
function onDragStart(e: DragEvent, key: string) { ... }
function onDragOver(e: DragEvent, key: string) { ... }
function onDragLeave(key: string) { ... }
function onDrop(e: DragEvent, targetKey: string) { ... }
function onDragEnd(e: DragEvent) { ... }

// 9. 动态列 props
type ColumnProps = Record<string, unknown>
function getColumnProps(col: ColumnDef): ColumnProps { ... }

// 10. watch 兜底
watch(visibleColumns, (val) => { ... }, { deep: true })
```

### 6.4 图标导入

```typescript
import { Document, Operation as OperationIcon, Search, Top } from '@element-plus/icons-vue'
//                                              ^^^^^ 必加
```

---

## 7. 验收清单

实现完后逐项打勾：

- [ ] 列设置 popover 中：拖手柄 ⠿ + 置顶按钮 📌 + checkbox ☐ 三件套齐全
- [ ] 置顶列在面板中排在前面，与未置顶列有分割线
- [ ] 表格中置顶列实际排在最前
- [ ] 拖拽排序可正常工作（顶部蓝色虚线反馈 + 拖动源半透明）
- [ ] 「重置默认」三个 key 全部清空
- [ ] 刷新页面后置顶/顺序/可见性都保持
- [ ] 操作列不可取消，提示「操作列不可取消」
- [ ] 全空时保留 actions，提示「至少需要保留一列可见」
- [ ] `vue-tsc --noEmit` 零错误
- [ ] 0 lint 错误

---

## 8. 注意事项

1. **不要在 `orderedColumns` 内 mutate `columnOrder`** — 始终是 read-only 派生
2. **`columnOrder` 必须包含所有列**（含隐藏的）— 这样取消勾选时顺序仍正确
3. **`pinnedColumns` 顺序就是置顶的「前后」顺序** — unshift 决定新置顶列在 pinned 内的位置
4. **不要把 required 列加进 `DEFAULT_PINNED`** — 必选列不需要置顶强调
5. **不要忘记 popper-class 改成页面级前缀** — 避免多个列表页的样式互相污染
6. **CSS 写在 `<style>`（非 scoped）** — popover 内容是动态插入的，scoped 选择器打不到

---

## 9. 参考实现

### 9.1 rentals/index.vue（最完整的实现）

位置：`frontend/src/views/rentals/index.vue`

关键差异点：
- 有 25 列（含 4 个格式化列 `data_disks` / `public_ips` / `memory_gb` / `system_disk` / `bandwidth_mbps`）
- 有顶部 selection 列（el-table 的多选列）
- 拖拽 5 个函数、置顶函数、动态列 props 函数都齐全
- DEFAULT_PINNED = `['machine_model', 'private_ip', 'status']`

### 9.2 contracts/index.vue

位置：`frontend/src/views/contracts/index.vue`

关键差异点：
- 有续期相关字段 `renewal_seq` / `has_renewal` / `renewed_from_id`，需要保留
- 附件状态列（3 个圆点指示器）
- DEFAULT_PINNED = `['name', 'status', 'amount']`

---

**最后修订时间**：2026-07-18
