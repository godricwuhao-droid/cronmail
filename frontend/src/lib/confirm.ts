import { ElMessageBox } from 'element-plus'

/** 删除确认框统一配置（对齐全局 .delete-message-box） */
const DELETE_CONFIRM_OPTIONS = {
  confirmButtonText: '删除',
  cancelButtonText: '取消',
  type: 'warning' as const,
  customClass: 'delete-message-box',
  confirmButtonClass: 'el-button--danger',
  autofocus: false,
}

/**
 * 统一删除二次确认。
 * @returns true 用户确认；false 用户取消
 */
export async function confirmDelete(
  message: string,
  title = '删除确认',
): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title, DELETE_CONFIRM_OPTIONS)
    return true
  } catch {
    return false
  }
}
