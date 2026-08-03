import { ref, computed, watch, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'

/**
 * 搜索防抖 composable
 * @param delay 防抖延迟时间（毫秒），默认 300ms
 * @returns { searchKeyword, debouncedKeyword, resetSearch }
 */
export function useDebounceSearch(delay = 300) {
  const searchKeyword = ref('')
  const debouncedKeyword = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  const doDebounce = () => {
    debouncedKeyword.value = searchKeyword.value
  }

  watch(searchKeyword, () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(doDebounce, delay)
  })

  const resetSearch = () => {
    searchKeyword.value = ''
    debouncedKeyword.value = ''
    if (timer) clearTimeout(timer)
  }

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return {
    searchKeyword,
    debouncedKeyword,
    resetSearch,
  }
}

/**
 * 列自定义 composable
 * @param columns 列定义数组
 * @param storageKey localStorage 存储键名
 * @returns { visibleColumns, pinnedColumns, columnOrder, toggleColumn, pinColumn, resetColumns, onColumnDragEnd }
 */
export function useColumnCustomization<T extends { key: string; label: string; pinned?: boolean; visible?: boolean }>(
  columns: T[],
  storageKey: string
) {
  // 从 localStorage 读取保存的列配置
  const savedConfig = localStorage.getItem(storageKey)
  let savedOrder: string[] | null = null
  let savedPinned: string[] | null = null

  if (savedConfig) {
    try {
      const config = JSON.parse(savedConfig)
      savedOrder = config.order || null
      savedPinned = config.pinned || null
    } catch {
      // 忽略解析错误
    }
  }

  // 初始化列状态
  const columnStates = columns.map((col) => ({
    key: col.key,
    label: col.label,
    pinned: savedPinned?.includes(col.key) ?? col.pinned ?? false,
    visible: col.visible !== false,
  }))

  // 列顺序
  const columnOrder = ref<string[]>(savedOrder || columnStates.map((c) => c.key))

  // 可见列
  const visibleColumns = computed(() =>
    columnStates.filter((c) => c.visible)
  )

  // 置顶列
  const pinnedColumns = computed(() =>
    columnStates.filter((c) => c.pinned)
  )

  // 保存配置到 localStorage
  const saveConfig = () => {
    const config = {
      order: columnOrder.value,
      pinned: columnStates.filter((c) => c.pinned).map((c) => c.key),
    }
    localStorage.setItem(storageKey, JSON.stringify(config))
  }

  // 切换列显示/隐藏
  const toggleColumn = (key: string, visible: boolean) => {
    const col = columnStates.find((c) => c.key === key)
    if (col) {
      col.visible = visible
      saveConfig()
    }
  }

  // 置顶/取消置顶
  const pinColumn = (key: string, pinned: boolean) => {
    const col = columnStates.find((c) => c.key === key)
    if (col) {
      col.pinned = pinned
      saveConfig()
    }
  }

  // 重置列配置
  const resetColumns = () => {
    columnStates.forEach((col, index) => {
      col.pinned = columns[index]?.pinned ?? false
      col.visible = columns[index]?.visible !== false
    })
    columnOrder.value = columnStates.map((c) => c.key)
    saveConfig()
  }

  // 列拖拽结束
  const onColumnDragEnd = (event: { oldIndex: number; newIndex: number }) => {
    const { oldIndex, newIndex } = event
    if (oldIndex === newIndex) return

    const movedItem = columnOrder.value.splice(oldIndex, 1)[0]
    columnOrder.value.splice(newIndex, 0, movedItem)
    saveConfig()
  }

  return {
    columnStates,
    columnOrder,
    visibleColumns,
    pinnedColumns,
    toggleColumn,
    pinColumn,
    resetColumns,
    onColumnDragEnd,
  }
}

/**
 * 导出 Excel composable
 * @param data 数据数组
 * @param columns 列定义数组
 * @param filename 文件名（不含扩展名）
 * @returns { exportExcel }
 */
export function useExportExcel<T extends Record<string, any>>(
  data: Ref<T[]>,
  columns: { key: string; label: string }[],
  filename: string = 'export'
) {
  const exportExcel = () => {
    if (data.value.length === 0) {
      return
    }

    const headers = columns.map((col) => col.label)
    const rows = data.value.map((row) =>
      columns.map((col) => {
        const value = row[col.key]
        return value !== null && value !== undefined ? value : ''
      })
    )

    const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '数据')
    XLSX.writeFile(wb, `${filename}_${new Date().toISOString().slice(0, 10)}.xlsx`)
  }

  return { exportExcel }
}