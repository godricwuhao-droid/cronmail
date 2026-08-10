import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 全局拖拽上传 composable
 *
 * 监听 window 级别的 dragenter / dragover / dragleave / drop 事件，
 * 当用户将文件拖到浏览器窗口任意位置时触发回调。
 *
 * 使用方式：
 *   const { isDragging } = useGlobalDrop({
 *     accept: ['pdf', 'doc', 'docx'],
 *     multiple: false,
 *     onDrop: (files) => { ... },
 *   })
 *
 * @param options.accept 允许的文件扩展名（小写），如 ['pdf', 'docx']，不传则接受所有文件
 * @param options.multiple 是否允许多文件，默认 false（只取第一个）
 * @param options.onDrop 拖放回调，接收过滤后的 File[]
 */
export function useGlobalDrop(options: {
  onDrop: (files: File[]) => void
  accept?: string[]
  multiple?: boolean
}) {
  const isDragging = ref(false)
  let dragCounter = 0

  function handleDragEnter(e: DragEvent) {
    e.preventDefault()
    // 只处理包含文件的拖拽（排除页面内文本/链接拖拽）
    if (!e.dataTransfer?.types.includes('Files')) return
    dragCounter++
    isDragging.value = true
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault()
  }

  function handleDragLeave(_e: DragEvent) {
    dragCounter--
    if (dragCounter <= 0) {
      dragCounter = 0
      isDragging.value = false
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    dragCounter = 0
    isDragging.value = false

    const files = e.dataTransfer?.files
    if (!files || files.length === 0) return

    const fileList = Array.from(files)

    // 格式过滤
    const valid = options.accept
      ? fileList.filter((f) => {
          const ext = f.name.split('.').pop()?.toLowerCase()
          return ext && options.accept!.includes(ext)
        })
      : fileList

    if (valid.length === 0) return

    // 单文件模式只取第一个
    const target = options.multiple !== false ? valid : [valid[0]]
    options.onDrop(target)
  }

  onMounted(() => {
    window.addEventListener('dragenter', handleDragEnter)
    window.addEventListener('dragover', handleDragOver)
    window.addEventListener('dragleave', handleDragLeave)
    window.addEventListener('drop', handleDrop)
  })

  onUnmounted(() => {
    window.removeEventListener('dragenter', handleDragEnter)
    window.removeEventListener('dragover', handleDragOver)
    window.removeEventListener('dragleave', handleDragLeave)
    window.removeEventListener('drop', handleDrop)
  })

  return { isDragging }
}
