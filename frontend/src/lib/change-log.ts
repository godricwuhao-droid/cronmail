/**
 * 变更记录内容解析工具（ADR-021）
 *
 * change_log.content 存在两种格式：
 *  - 旧格式：人工输入的纯文本
 *  - 新格式：结构化 JSON 字符串，如
 *    [{"field":"内存(GB)","old":64,"new":128},{"field":"备注","old":null,"new":"升级内存"}]
 *
 * 展示层统一通过 parseChangeContent 判定格式后渲染。
 */

/** 单个字段变更（新格式 JSON 元素） */
export interface ChangeField {
  field: string
  old: unknown
  new: unknown
}

/** 解析结果：json（新格式）或 text（旧格式/解析失败兜底） */
export type ParsedChangeContent =
  | { type: 'json'; fields: ChangeField[] }
  | { type: 'text'; text: string }

/**
 * 解析变更记录内容。
 * 仅当 JSON.parse 成功且为「含 field 键的对象数组」时判定为新格式，
 * 否则一律按纯文本展示（兼容存量数据）。
 */
export function parseChangeContent(content: string | null | undefined): ParsedChangeContent {
  if (content == null) return { type: 'text', text: '' }
  const trimmed = content.trim()
  if (!trimmed.startsWith('[')) return { type: 'text', text: content }
  try {
    const parsed: unknown = JSON.parse(trimmed)
    if (
      Array.isArray(parsed) &&
      parsed.length > 0 &&
      parsed.every(
        (item) =>
          typeof item === 'object' &&
          item !== null &&
          typeof (item as Record<string, unknown>).field === 'string',
      )
    ) {
      return { type: 'json', fields: parsed as ChangeField[] }
    }
  } catch {
    // 非 JSON，按纯文本
  }
  return { type: 'text', text: content }
}

/** 变更值展示：null/undefined 显示「—」 */
export function formatChangeValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
