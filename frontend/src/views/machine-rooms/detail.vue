<script setup lang="ts">
/**
 * 机房管理 - 详情页（ADR-026：tab 单位 = 排（真实实体）；ADR-027：点位图视觉重设计——
 * 机架列卡片化 + 双层表头收敛（状态点 + ⋯ 菜单）+ 占用格状态条色块 + 横幅改紧凑统计条；
 * ADR-028：多 U 设备合并为跨行色块（同 rental_id 连续格，块高 = u_size×行高）+
 * 点选上架预校验（u_position = 设备底部 U，区间 [n, n+size-1] 向上延伸；越界/重叠红字提示并禁用确认）；
 * ADR-029：机柜断电（power_on=false）→ 柜内整列（组头以下）灰化叠加（纯视觉，不改设备状态））
 *
 * 功能：
 *  - tab 结构：每个排一个 tab（label = 排名 + 柜数，如「A排（2柜）」），
 *    最后一个 tab 为「仓库（N）」；排被删后回落第一排/仓库
 *  - 选中排 tab：内容区 = 排工具栏（左侧灰字统计 `{排名} · N柜 · X/Y U已用`，
 *    右侧「+ 添加机柜」primary + 编辑排/删除排图标按钮；room.note 非空时 el-alert info 一行）
 *    → 整排浅灰卡片（#f3f5f7，padding 12px，圆角 12px）→ 机柜组并排（横向滚动）：
 *    每组 = 机柜组头（浅灰圆角顶：机柜名 13px 600 + 8px 状态圆点（通电绿/未通电灰，title 提示）
 *    + 右侧 ⋯ 图标按钮（点击展开 el-dropdown：通电/断电、编辑、删除、添加机架））
 *    + 柜内机架卡片（白底 1px #e8eaed 边框圆角 8px，列间距 12px）；
 *    机架头（浅灰：机架名 12px 600 + 占用/容量 11px 灰字；hover 时右上角浮现
 *    编辑/删除 2 个 16px 图标）；表头总高 ~64px；
 *    空机柜（无机架）按 2 列占位：组头 + 「U位空列 + 暂无机架」浅灰占位卡（10px 灰字），
 *    宽度与正常机架卡（44px + 128px）一致，加机架入口保留在组头 ⋯ 菜单「添加机架」；
 *    机架卡体每行 = U 位号列（44px，#fafbfc 底，10px #9aa3ad 水平居中）+ 设备格（128px，行高 34px），
 *    行序 capacity_u→1；已占用格 = 铺满整格的色块（inset 0 无圆角 + 左侧 2px 状态条，
 *    格内文字水平居中：型号 11px 600 单行省略 + IP 10px），四色状态体系（ADR-028 裁决，
 *    2026-10-27 再调整：对齐设备列表 el-tag 色）：
 *    租赁中 橙 底 #fdf3e3/条 #e6a23c/型号 #8a5a12/IP #b8905c（= 列表 warning tag 橙同色系），
 *    故障 红 底 #fdecec/条 #e06c6c/型号 #a33/IP #c98a8a，
 *    空闲中 绿 底 #e7f4e4/条 #34c759/型号 #2b6b23/IP #7a8a76，
 *    已断电 灰黑 底 #f0f1f3/条 #6b7280/型号 #3d4450/IP #8a919c（深灰黑系，非纯黑），
 *    未知/空状态兜底→绿；hover 色块加深 + 轻阴影，点击跳设备详情；
 *    空格白底无字，hover 整格浅绿底 + 中央浮现 "+"（12px 绿）
 *  - 点选 U 位上架（ADR-024 保留）：空 U 位格可点击（hover 显示 "+"）→
 *    「放入设备」对话框（目标位置只读 = `{机柜名}/{机架名} · U{u}`；设备列表 = 仓库未上架设备
 *    GET /api/rentals?warehoused=true，search 按型号模糊、防抖 300ms；单选行）→
 *    PUT /api/rentals/{id} 提交 machine_room_id + rack_id + u_position，409 展示后端 detail
 *  - 三级添加：「+ 添加排」在页面卡头右上（与机房名同一水平线）、「+ 添加机柜」在当前排工具栏
 *    （名称+电源开关）；排工具栏另有「编辑排」（排名+备注，复用新建排对话框）；
 *    「添加机架」在机柜组头 ⋯ 菜单（名称+容量）；所有删除走 confirmDelete + 409 detail 展示
 *  - 紧凑统计条（ADR-027，替代原深蓝横幅）：排工具栏左侧灰字 `A排 · 10柜 · X/Y U已用`
 *    （12px，数字 600，统计口径 = 当前排）；room.note 非空时 el-alert info light 一行
 *  - 未定位 U 的在架设备提示来自 point-map 响应 unlocated 字段（ADR-024，缺省按空数组兜底）
 *  - 仓库 tab：未上架设备表格 + 详情跳转（上架入口统一到点位图空格点击）
 *  - 数据全部来自 GET /api/machine-rooms/{id}/point-map（ADR-026）
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Delete, Edit, InfoFilled, MoreFilled, OfficeBuilding, Plus } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
import {
  createCabinet,
  createRack,
  createRow,
  deleteCabinet,
  deleteRack,
  deleteRow,
  getPointMap,
  updateCabinet,
  updateRack,
  updateRow,
  type Cabinet,
  type MachineRoom,
  type RackPoint,
  type RackRow,
  type RoomDeviceBrief,
} from '@/api/modules/machine-room'
import { getRentals, updateRental, type RentalListItem } from '@/api/modules/rental'
import { formatRackLocation, safeStatusLabel, safeStatusTagType } from '@/lib/rental'

const route = useRoute()
const router = useRouter()

const roomId = computed(() => route.params.id as string)

// ============================================================
// 点位图数据（ADR-026 point-map）
// ============================================================
const loading = ref(false)
const room = ref<MachineRoom | null>(null)
const rows = ref<RackRow[]>([])
const warehoused = ref<RoomDeviceBrief[]>([])
/** 在架但未定位 U 的设备（ADR-024：point-map 响应 unlocated 字段，缺省空数组兜底） */
const unlocated = ref<RoomDeviceBrief[]>([])
const activeTab = ref('')

async function loadPoints() {
  loading.value = true
  try {
    const data = await getPointMap(roomId.value)
    room.value = data.room
    rows.value = data.rows
    warehoused.value = data.warehoused
    unlocated.value = data.unlocated ?? []
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// 排 tab（ADR-026：tab 单位 = 排，真实实体）
// ============================================================
/** 当前选中的排（activeTab 为排 id 字符串时） */
const currentRow = computed(
  () => rows.value.find((r) => String(r.id) === activeTab.value) ?? null,
)

/**
 * tab 修正：排增删后保证 activeTab 有效
 *  - 无排 → 落到「仓库」tab
 *  - 当前排已不存在（如被删）→ 落到第一排 tab
 *  - 「仓库」tab 始终保留
 */
watch(rows, (list) => {
  if (list.length === 0) {
    activeTab.value = 'warehouse'
    return
  }
  if (activeTab.value !== 'warehouse' && !list.some((r) => String(r.id) === activeTab.value)) {
    activeTab.value = String(list[0].id)
  }
})

// ============================================================
// 排内机柜分组 + 机架卡片点阵（ADR-027 视觉重设计：机架列卡片化）
// ============================================================
/** 机架已定位 U 的设备数 */
function rackOccupiedCount(rack: RackPoint) {
  return rack.u_cells.filter((c) => c.rental_id != null).length
}

/** 当前排全部机架（机柜顺序 → 柜内机架顺序） */
const rowRacks = computed(() => currentRow.value?.cabinets.flatMap((c) => c.racks) ?? [])

/** 当前排已定位 U 的设备数（工具栏统计口径 = 当前排） */
const rowOccupied = computed(
  () => rowRacks.value.reduce((sum, r) => sum + rackOccupiedCount(r), 0),
)

/** 当前排 U 位总容量（统计条 `X/Y U已用` 的分母） */
const rowCapacity = computed(() => rowRacks.value.reduce((sum, r) => sum + r.capacity_u, 0))

/** 当前排机架容量最大值（空机柜占位卡体高度对齐用，无机架时兜底 4 行） */
const rowMaxU = computed(() => {
  const m = rowRacks.value.reduce((max, r) => Math.max(max, r.capacity_u), 0)
  return m > 0 ? m : 4
})

/** 机架 U 位行序：capacity_u → 1（顶部高 U，1 在最下） */
function rackUList(rack: RackPoint): number[] {
  const out: number[] = []
  for (let u = rack.capacity_u; u >= 1; u--) out.push(u)
  return out
}

/** 占用格四色状态类名（ADR-028 裁决，2026-10-27 再调整：对齐设备列表 el-tag 色）：
 *  租赁中→橙（= 列表 warning tag 橙同色系）/ 故障→红 / 空闲中→绿 / 已断电→灰黑；
 *  未知/空状态兜底→绿 */
function cellClass(cell: { status: string | null }): string {
  if (cell.status === '租赁中') return 'u-block-rented'
  if (cell.status === '故障') return 'u-block-fault'
  if (cell.status === '空闲中') return 'u-block-idle'
  if (cell.status === '已断电') return 'u-block-off'
  return 'u-block-idle'
}

// ============================================================
// 多 U 合并渲染（ADR-028：同一 rental_id 的连续格 → 跨 u_size 行的色块）
// 后端契约：多 U 设备区间 [u_position, u_position+u_size-1] 内每个 U 格都标记同一 brief（含 u_size）；
// brief 缺 u_size 时按连续同 rental_id 格数推断
// ============================================================
/** 设备块：占用 [bottomU, topU]，topU = 区间上端 = 底部 + size - 1 */
interface UBlock {
  rental_id: string
  topU: number
  bottomU: number
  size: number
  model: string | null
  ip: string | null
  status: string | null
  remark: string | null
}

/** 格渲染视图：block-top = 块首格（区间上端，渲染跨行色块）/ block-interior = 块内其余格（透明占位）/ empty = 空格 */
interface UCellView {
  kind: 'block-top' | 'block-interior' | 'empty'
  block: UBlock | null
}

const EMPTY_VIEW: UCellView = { kind: 'empty', block: null }

/** rack.id → (u → 格视图)，point-map 数据变化时重算 */
const cellViews = computed(() => {
  const map = new Map<number, Map<number, UCellView>>()
  for (const row of rows.value) {
    for (const cab of row.cabinets) {
      for (const rack of cab.racks) {
        const byU = new Map<number, UCellView>()
        const cells = [...rack.u_cells].sort((a, b) => a.u - b.u)
        let i = 0
        while (i < cells.length) {
          const c = cells[i]
          if (c.rental_id == null) {
            byU.set(c.u, { ...EMPTY_VIEW })
            i++
            continue
          }
          // 连续同 rental_id 格归为一组（多 U 设备区间）
          let j = i
          while (j + 1 < cells.length && cells[j + 1].rental_id === c.rental_id) j++
          const size = c.u_size ?? j - i + 1
          let topU = c.u + size - 1
          if (topU > cells[j].u) topU = cells[j].u // 防御：u_size 与标记格数不一致时以标记格上端为准
          const block: UBlock = {
            rental_id: c.rental_id,
            topU,
            bottomU: c.u,
            size: topU - c.u + 1,
            model: c.machine_model,
            ip: c.private_ip,
            status: c.status,
            remark: c.remark,
          }
          for (let k = i; k <= j; k++) {
            byU.set(cells[k].u, {
              kind: cells[k].u === topU ? 'block-top' : 'block-interior',
              block,
            })
          }
          i = j + 1
        }
        map.set(rack.id, byU)
      }
    }
  }
  return map
})

/** 取机架某 U 位的渲染视图（缺省 empty） */
function viewOf(rack: RackPoint, u: number): UCellView {
  return cellViews.value.get(rack.id)?.get(u) ?? EMPTY_VIEW
}

/** 行底边（u 与 u-1 之间）是否位于合并块内部：是则隐藏行分隔线（块整体圆角） */
function borderHidden(rack: RackPoint, u: number): boolean {
  const cur = viewOf(rack, u).block
  if (!cur) return false
  const below = viewOf(rack, u - 1).block
  return below != null && below.rental_id === cur.rental_id
}

/** 机柜组头 ⋯ 菜单命令分发（ADR-027：操作收敛进下拉菜单） */
function onCabinetCommand(cab: Cabinet, cmd: string) {
  if (cmd === 'power') {
    handleToggleCabinetPower(cab, !cab.power_on)
  } else if (cmd === 'edit') {
    openEditCabinet(cab)
  } else if (cmd === 'delete') {
    handleDeleteCabinet(cab)
  } else if (cmd === 'add-rack') {
    openCreateRack(cab)
  }
}

// ============================================================
// 排：新建 / 编辑 / 删除
// ============================================================
const rowDialogVisible = ref(false)
const editingRow = ref<RackRow | null>(null)
const rowSubmitting = ref(false)
const rowFormRef = ref<FormInstance>()

const rowForm = reactive({
  name: '',
  note: '',
})

const rowRules: FormRules = {
  name: [{ required: true, message: '请输入排名称', trigger: 'blur' }],
}

function openCreateRow() {
  editingRow.value = null
  rowForm.name = ''
  rowForm.note = ''
  rowDialogVisible.value = true
}

function openEditRow(row: RackRow) {
  editingRow.value = row
  rowForm.name = row.name
  rowForm.note = row.note ?? ''
  rowDialogVisible.value = true
}

async function handleRowSubmit() {
  if (!rowFormRef.value) return
  try {
    await rowFormRef.value.validate()
  } catch {
    ElMessage.error('请检查表单填写')
    return
  }
  rowSubmitting.value = true
  try {
    if (editingRow.value) {
      // 编辑：排名可改 + 备注（400 排名重复走统一错误处理）
      await updateRow(roomId.value, editingRow.value.id, {
        name: rowForm.name.trim(),
        note: rowForm.note.trim() || null,
      })
      ElMessage.success('排已更新')
    } else {
      await createRow(roomId.value, {
        name: rowForm.name.trim(),
        note: rowForm.note.trim() || null,
      })
      ElMessage.success('排已创建')
    }
    rowDialogVisible.value = false
    loadPoints()
  } catch (e) {
    // 错误已统一处理
  } finally {
    rowSubmitting.value = false
  }
}

async function handleDeleteRow(row: RackRow) {
  if (!(await confirmDelete(`确定删除「${row.name}」？删除后其下机柜一并删除。`))) return
  try {
    await deleteRow(roomId.value, row.id, { __silent: true })
    ElMessage.success('排已删除')
    loadPoints()
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

// ============================================================
// 机柜：新建 / 编辑 / 删除 / 电源
// ============================================================
const cabinetDialogVisible = ref(false)
const editingCabinet = ref<Cabinet | null>(null)
/** 新建机柜时所属的排 */
const targetRow = ref<RackRow | null>(null)
const cabinetSubmitting = ref(false)
const cabinetFormRef = ref<FormInstance>()

const cabinetForm = reactive({
  name: '',
  power_on: true,
})

const cabinetRules: FormRules = {
  name: [{ required: true, message: '请输入机柜名称', trigger: 'blur' }],
}

function openCreateCabinet(row: RackRow) {
  editingCabinet.value = null
  targetRow.value = row
  cabinetForm.name = ''
  cabinetForm.power_on = true
  cabinetDialogVisible.value = true
}

function openEditCabinet(cab: Cabinet) {
  editingCabinet.value = cab
  targetRow.value = null
  cabinetForm.name = cab.name
  cabinetForm.power_on = cab.power_on
  cabinetDialogVisible.value = true
}

async function handleCabinetSubmit() {
  if (!cabinetFormRef.value) return
  try {
    await cabinetFormRef.value.validate()
  } catch {
    ElMessage.error('请检查表单填写')
    return
  }
  cabinetSubmitting.value = true
  try {
    if (editingCabinet.value) {
      // 编辑：改机柜名仍只读，开放电源状态
      await updateCabinet(editingCabinet.value.id, { power_on: cabinetForm.power_on })
      ElMessage.success('机柜已更新')
    } else if (targetRow.value) {
      await createCabinet(roomId.value, targetRow.value.id, {
        name: cabinetForm.name.trim(),
        power_on: cabinetForm.power_on,
      })
      ElMessage.success('机柜已创建')
    }
    cabinetDialogVisible.value = false
    loadPoints()
  } catch (e) {
    // 错误已统一处理
  } finally {
    cabinetSubmitting.value = false
  }
}

async function handleDeleteCabinet(cab: Cabinet) {
  if (!(await confirmDelete(`确定删除机柜「${cab.name}」？删除后其下机架一并删除。`))) return
  try {
    await deleteCabinet(cab.id, { __silent: true })
    ElMessage.success('机柜已删除')
    loadPoints()
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

/** 机柜组头电源开关（change 即 PUT /api/cabinets/{id}） */
async function handleToggleCabinetPower(cab: Cabinet, val: boolean | string | number) {
  try {
    await updateCabinet(cab.id, { power_on: !!val })
    ElMessage.success(!!val ? '已通电' : '已断电')
    loadPoints()
  } catch (e) {
    // 错误已统一处理
  }
}

// ============================================================
// 机架：新建 / 编辑 / 删除
// ============================================================
const rackDialogVisible = ref(false)
const editingRack = ref<RackPoint | null>(null)
/** 新建机架时所属的机柜 */
const targetCabinet = ref<Cabinet | null>(null)
const rackSubmitting = ref(false)
const rackFormRef = ref<FormInstance>()

const rackForm = reactive({
  name: '',
  capacity_u: 24,
})

const rackRules: FormRules = {
  name: [{ required: true, message: '请输入机架名称', trigger: 'blur' }],
  capacity_u: [{ required: true, message: '请输入 U 位容量', trigger: 'blur' }],
}

function openCreateRack(cab: Cabinet) {
  editingRack.value = null
  targetCabinet.value = cab
  rackForm.name = ''
  rackForm.capacity_u = 24
  rackDialogVisible.value = true
}

function openEditRack(rack: RackPoint) {
  editingRack.value = rack
  targetCabinet.value = null
  rackForm.name = rack.name
  rackForm.capacity_u = rack.capacity_u
  rackDialogVisible.value = true
}

async function handleRackSubmit() {
  if (!rackFormRef.value) return
  try {
    await rackFormRef.value.validate()
  } catch {
    ElMessage.error('请检查表单填写')
    return
  }
  rackSubmitting.value = true
  try {
    if (editingRack.value) {
      // 编辑开放 capacity_u（改机架名仍只读）
      await updateRack(editingRack.value.id, { capacity_u: rackForm.capacity_u })
      ElMessage.success('机架已更新')
    } else if (targetCabinet.value) {
      await createRack(targetCabinet.value.id, {
        name: rackForm.name.trim(),
        capacity_u: rackForm.capacity_u,
      })
      ElMessage.success('机架已创建')
    }
    rackDialogVisible.value = false
    loadPoints()
  } catch (e) {
    // 错误已统一处理
  } finally {
    rackSubmitting.value = false
  }
}

async function handleDeleteRack(rack: RackPoint) {
  if (!(await confirmDelete(`确定删除机架「${rack.name}」？`))) return
  try {
    await deleteRack(rack.id, { __silent: true })
    ElMessage.success('机架已删除')
    loadPoints()
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

// ============================================================
// 点选 U 位上架（ADR-024：空格点击 → 放入设备对话框）
// ============================================================
const placeVisible = ref(false)
const placeCabinet = ref<Cabinet | null>(null)
const targetRack = ref<RackPoint | null>(null)
const targetU = ref(0)
const deviceSearch = ref('')
const deviceList = ref<RentalListItem[]>([])
const deviceLoading = ref(false)
const selectedDevice = ref<RentalListItem | null>(null)
const placeSubmitting = ref(false)

/** 搜索防抖（~300ms） */
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(deviceSearch, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadDevices(), 300)
})

/** 仓库未上架设备列表（GET /api/rentals?warehoused=true，search 按型号模糊） */
async function loadDevices() {
  deviceLoading.value = true
  try {
    const res = await getRentals({
      warehoused: true,
      search: deviceSearch.value.trim() || undefined,
      page: 1,
      page_size: 100,
    })
    deviceList.value = res.items
  } catch (e) {
    // 错误已统一处理
  } finally {
    deviceLoading.value = false
  }
}

/** 点击空格：打开「放入设备」对话框（目标位置 = 点击的格，只读） */
function openPlaceDevice(cab: Cabinet, rack: RackPoint, u: number) {
  placeCabinet.value = cab
  targetRack.value = rack
  targetU.value = u
  deviceSearch.value = ''
  selectedDevice.value = null
  placeVisible.value = true
  loadDevices()
}

function onDeviceRowChange(row: RentalListItem | null) {
  selectedDevice.value = row
}

// ============================================================
// 上架预校验（ADR-028：u_position = 设备底部 U，占用区间 [n, n+size-1] 向上延伸）
// ============================================================
/** 选中设备的 U 数（brief 缺 u_size 按 1 兜底） */
const selectedSize = computed(() => selectedDevice.value?.u_size ?? 1)
/** 选中设备后的占用区间上端 */
const placeTopU = computed(() => targetU.value + selectedSize.value - 1)
/** 越界：区间上端超出机架容量 */
const placeOutOfBounds = computed(
  () => targetRack.value != null && placeTopU.value > targetRack.value.capacity_u,
)
/** 重叠：区间与机架内已占用格相交（待上架设备在仓库，不在架内，故任意已占格相交即冲突） */
const placeOverlap = computed(() => {
  if (!targetRack.value || !selectedDevice.value) return false
  return targetRack.value.u_cells.some(
    (c) => c.rental_id != null && c.u >= targetU.value && c.u <= placeTopU.value,
  )
})
/** 确认按钮禁用：未选设备 / 越界 / 重叠（后端 400/409 仍保留兜底） */
const placeDisabled = computed(
  () => !selectedDevice.value || placeOutOfBounds.value || placeOverlap.value,
)

async function handlePlace() {
  if (!selectedDevice.value || !targetRack.value || !placeCabinet.value) {
    ElMessage.warning('请选择要放入的设备')
    return
  }
  placeSubmitting.value = true
  try {
    await updateRental(selectedDevice.value.id, {
      machine_room_id: Number(roomId.value),
      rack_id: targetRack.value.id,
      u_position: targetU.value,
    })
    ElMessage.success(`已上架 ${placeCabinet.value.name}/${targetRack.value.name}-U${targetU.value}`)
    placeVisible.value = false
    loadPoints()
  } catch (e) {
    // ADR-028：400 越界 / 409 位置冲突：统一拦截器不展示 detail，这里手动提示（前端预校验的兜底）
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 400 || status === 409) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      ElMessage.error(detail || (status === 409 ? 'U 位已被占用' : '上架位置校验失败'))
    }
    // 其余错误已统一处理
  } finally {
    placeSubmitting.value = false
  }
}

// ============================================================
// 跳转设备详情
// ============================================================
function goRental(rentalId: string) {
  router.push(`/rentals/${rentalId}`)
}

onMounted(loadPoints)
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="top-bar">
      <el-button @click="router.push({ name: 'MachineRoomList' })">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div class="page-panel">
      <!-- 机房信息头（「添加排」固定在卡头右上，与机房名同一水平线） -->
      <div class="card-header">
        <span class="title">
          <el-icon><OfficeBuilding /></el-icon>
          {{ room?.name || '机房详情' }}
        </span>
        <div class="header-right">
          <div class="room-meta">
            <el-tag v-if="room?.code" type="info" size="small">{{ room.code }}</el-tag>
            <span v-if="room?.address" class="room-address">{{ room.address }}</span>
            <span v-if="room?.note" class="room-note">{{ room.note }}</span>
          </div>
          <el-button type="primary" :icon="Plus" @click="openCreateRow">添加排</el-button>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="room-tabs">
        <!-- 每个排一个 tab（ADR-026：排为真实实体） -->
        <el-tab-pane v-for="row in rows" :key="row.id" :name="String(row.id)">
          <template #label>{{ row.name }}（{{ row.cabinets.length }}柜）</template>

          <!-- 当前排工具栏（ADR-027：横幅 → 紧凑统计条，统计口径 = 当前排） -->
          <div class="toolbar">
            <span class="row-stats">
              {{ row.name }} · {{ row.cabinets.length }}柜 ·
              <b>{{ rowOccupied }}</b>/<b>{{ rowCapacity }}</b> U已用
            </span>
            <span v-if="row.note" class="muted">备注 {{ row.note }}</span>
            <div class="toolbar-right">
              <el-button type="primary" :icon="Plus" @click="openCreateCabinet(row)">
                添加机柜
              </el-button>
              <el-button circle size="small" :icon="Edit" title="编辑排" @click="openEditRow(row)" />
              <el-button
                circle
                size="small"
                :icon="Delete"
                title="删除排"
                @click="handleDeleteRow(row)"
              />
            </div>
          </div>

          <!-- 机房级提示（room.note）：el-alert info light 一行 -->
          <el-alert
            v-if="room?.note"
            :title="`备注：${room.note}`"
            type="info"
            :closable="false"
            class="room-note-alert"
          />

          <!-- 空排提示 -->
          <div v-if="row.cabinets.length === 0" class="empty-row-tip">
            该排暂无机柜，点击「添加机柜」创建
          </div>

          <!-- 整排浅灰卡片：机柜组并排（横向滚动），每组 = 组头 + 柜内机架卡片 -->
          <div v-else class="row-board">
            <div v-for="cab in row.cabinets" :key="cab.id" class="cab-group">
              <!-- 机柜组头：机柜名 + 状态圆点 + ⋯ 菜单（点击展开） -->
              <div class="cab-head">
                <span class="cab-name">{{ cab.name }}</span>
                <span
                  class="cab-dot"
                  :class="cab.power_on ? 'cab-dot-on' : 'cab-dot-off'"
                  :title="cab.power_on ? '通电' : '未通电'"
                />
                <el-dropdown class="cab-more" trigger="click" @command="(cmd: string) => onCabinetCommand(cab, cmd)">
                  <button type="button" class="cab-more-btn" title="更多操作">
                    <el-icon><MoreFilled /></el-icon>
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="power">
                        {{ cab.power_on ? '断电' : '通电' }}
                      </el-dropdown-item>
                      <el-dropdown-item command="edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="delete">删除</el-dropdown-item>
                      <el-dropdown-item command="add-rack" divided>添加机架</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>

              <!-- 柜内机架卡片（空机柜 = 2 列占位卡：U位空列 + 「暂无机架」）；
                   ADR-029：断电（power_on=false）时整列（组头以下）叠加灰化 class（纯视觉） -->
              <div class="cab-racks" :class="{ 'cab-power-off': !cab.power_on }">
                <div v-if="cab.racks.length === 0" class="rack-card">
                  <div class="rack-head">
                    <span class="rack-empty-u"></span>
                    <span class="rack-empty-text">暂无机架</span>
                  </div>
                  <div class="rack-body-empty" :style="{ minHeight: `${rowMaxU * 34}px` }"></div>
                </div>
                <div v-for="rack in cab.racks" :key="rack.id" class="rack-card">
                  <!-- 机架头：机架名 + 占用/容量；hover 浮现编辑/删除图标 -->
                  <div class="rack-head">
                    <span class="rack-name" :title="rack.name">{{ rack.name }}</span>
                    <span class="rack-cap">{{ rackOccupiedCount(rack) }}/{{ rack.capacity_u }}</span>
                    <span class="rack-actions">
                      <button type="button" class="rack-act-btn" title="编辑机架" @click="openEditRack(rack)">
                        <el-icon><Edit /></el-icon>
                      </button>
                      <button
                        type="button"
                        class="rack-act-btn rack-act-del"
                        title="删除机架"
                        @click="handleDeleteRack(rack)"
                      >
                        <el-icon><Delete /></el-icon>
                      </button>
                    </span>
                  </div>
                  <!-- 机架卡体：U 位号列 + 设备格，行序 capacity_u → 1（ADR-028：多 U 设备合并为跨行色块） -->
                  <div class="rack-body">
                    <div
                      v-for="u in rackUList(rack)"
                      :key="u"
                      class="rack-row"
                      :class="{ 'row-in-block': borderHidden(rack, u) }"
                    >
                      <div class="u-num">{{ u }}</div>
                      <div class="u-slot">
                        <!-- 块首格（区间上端）：渲染跨 u_size 行的合并色块，点击跳设备详情 -->
                        <div
                          v-if="viewOf(rack, u).kind === 'block-top' && viewOf(rack, u).block"
                          class="u-block u-block-multi"
                          :class="cellClass(viewOf(rack, u).block!)"
                          :style="{ height: `${viewOf(rack, u).block!.size * 34}px` }"
                          :title="viewOf(rack, u).block!.remark || '点击查看详情'"
                          @click="goRental(viewOf(rack, u).block!.rental_id)"
                        >
                          <div class="u-block-text">
                            <div class="u-block-model">{{ viewOf(rack, u).block!.model || '—' }}</div>
                            <div v-if="viewOf(rack, u).block!.ip" class="u-block-ip">
                              {{ viewOf(rack, u).block!.ip }}
                            </div>
                          </div>
                        </div>
                        <!-- 块内其余格：透明占位（色块已跨行覆盖，点击穿透到色块） -->
                        <!-- 空格：hover 显示 "+"，点击打开放入设备对话框 -->
                        <div
                          v-else-if="viewOf(rack, u).kind === 'empty'"
                          class="u-slot-empty"
                          title="点击放入设备"
                          @click="openPlaceDevice(cab, rack, u)"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 未定位 U 的在架设备提示（ADR-024：point-map 响应 unlocated 字段） -->
          <div v-if="unlocated.length" class="unlocated-box">
            <div class="unlocated-title">以下设备已关联机架但未指定 U 位：</div>
            <div class="unlocated-list">
              <el-tag
                v-for="d in unlocated"
                :key="d.rental_id"
                size="small"
                class="unlocated-tag"
                @click="goRental(d.rental_id)"
              >
                {{ d.machine_model || d.rental_id }}
              </el-tag>
            </div>
          </div>
        </el-tab-pane>
        <!-- 仓库（未上架设备） -->
        <el-tab-pane name="warehouse">
          <template #label>仓库（{{ warehoused.length }}）</template>

          <div class="warehouse-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>上架请切换到排 tab（如 A排），点击点位图空格</span>
          </div>

          <el-table :data="warehoused" stripe style="width: 100%">
            <template #empty>
              <div class="table-empty">
                <el-empty description="暂无未上架设备" :image-size="64" />
              </div>
            </template>
            <el-table-column label="机器型号" min-width="180">
              <template #default="{ row }">
                <span class="col-name-link" @click="goRental(row.rental_id)">
                  {{ row.machine_model || '—' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="当前位置" min-width="180">
              <template #default="{ row }">
                <span v-if="formatRackLocation(row) !== '—'">{{ formatRackLocation(row) }}</span>
                <span v-else class="col-muted">—</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="safeStatusTagType(row.status)" size="small">
                  {{ safeStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click="goRental(row.rental_id)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 排 新建/编辑 对话框 -->
    <el-dialog
      v-model="rowDialogVisible"
      :title="editingRow ? `编辑排 ${editingRow.name}` : '添加排'"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-form ref="rowFormRef" :model="rowForm" :rules="rowRules" label-position="top">
        <el-form-item label="排名称" prop="name">
          <el-input v-model="rowForm.name" placeholder="如 A排" maxlength="128" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="rowForm.note"
            type="textarea"
            :rows="2"
            placeholder="可选"
            maxlength="256"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rowDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="rowSubmitting" @click="handleRowSubmit">
          {{ editingRow ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 机柜 新建/编辑 对话框 -->
    <el-dialog
      v-model="cabinetDialogVisible"
      :title="editingCabinet ? `编辑机柜 ${editingCabinet.name}` : '添加机柜'"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-form ref="cabinetFormRef" :model="cabinetForm" :rules="cabinetRules" label-position="top">
        <el-form-item label="机柜名称" prop="name">
          <el-input
            v-model="cabinetForm.name"
            :disabled="!!editingCabinet"
            placeholder="如 A01"
            maxlength="128"
          />
        </el-form-item>
        <el-form-item label="通电状态">
          <el-switch
            v-model="cabinetForm.power_on"
            active-text="通电"
            inactive-text="未通电"
            inline-prompt
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cabinetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="cabinetSubmitting" @click="handleCabinetSubmit">
          {{ editingCabinet ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 机架 新建/编辑 对话框 -->
    <el-dialog
      v-model="rackDialogVisible"
      :title="editingRack ? `编辑机架 ${editingRack.name}` : '添加机架'"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-form ref="rackFormRef" :model="rackForm" :rules="rackRules" label-position="top">
        <el-form-item label="机架名称" prop="name">
          <el-input
            v-model="rackForm.name"
            :disabled="!!editingRack"
            placeholder="如 A10-24U"
            maxlength="128"
          />
        </el-form-item>
        <el-form-item label="U 位容量" prop="capacity_u">
          <el-input-number v-model="rackForm.capacity_u" :min="1" :max="1024" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rackDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="rackSubmitting" @click="handleRackSubmit">
          {{ editingRack ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 放入设备对话框（ADR-024 点选 U 位上架） -->
    <el-dialog
      v-model="placeVisible"
      title="放入设备"
      width="640px"
      :close-on-click-modal="false"
    >
      <div v-if="targetRack && placeCabinet" class="place-body">
        <div class="place-target">
          <div class="muted">目标位置（U{{ targetU }} = 设备底部）</div>
          <div class="place-target-value">
            {{ placeCabinet.name }}/{{ targetRack.name }} · U{{ targetU }}
          </div>
        </div>
        <!-- ADR-028 上架预校验：占用区间预览 + 越界/重叠红字提示（确认按钮同步禁用） -->
        <div v-if="selectedDevice" class="place-preview">
          <template v-if="placeOutOfBounds">
            <span class="place-error">
              上方空间不足（需 U{{ targetU }}~U{{ placeTopU }}，机架仅 {{ targetRack.capacity_u }}U）
            </span>
          </template>
          <template v-else-if="placeOverlap">
            <span class="place-error">所选区间与现有设备重叠</span>
          </template>
          <template v-else>
            <span class="place-ok">
              将占用 U{{ targetU }}~U{{ placeTopU }}（{{ selectedSize }}U 设备）
            </span>
          </template>
        </div>
        <el-input
          v-model="deviceSearch"
          placeholder="按型号搜索"
          clearable
          class="place-search"
        />
        <el-table
          v-loading="deviceLoading"
          :data="deviceList"
          row-key="id"
          highlight-current-row
          style="width: 100%"
          @current-change="onDeviceRowChange"
        >
          <template #empty>
            <el-empty description="暂无未上架设备" :image-size="48" />
          </template>
          <el-table-column label="机器型号" min-width="180">
            <template #default="{ row }">
              <span>{{ row.machine_model || '—' }}</span>
            </template>
          </el-table-column>
          <!-- ADR-028：设备 U 数（brief 缺 u_size 按 1 兜底） -->
          <el-table-column label="U数" width="70" align="center">
            <template #default="{ row }">
              <span>{{ (row.u_size ?? 1) }}U</span>
            </template>
          </el-table-column>
          <el-table-column label="当前位置" min-width="150">
            <template #default="{ row }">
              <span v-if="formatRackLocation(row) !== '—'">{{ formatRackLocation(row) }}</span>
              <span v-else class="col-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="safeStatusTagType(row.status)" size="small">
                {{ safeStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="placeVisible = false">取消</el-button>
        <!-- ADR-028：越界/重叠时禁用确认（后端 400/409 兜底） -->
        <el-button type="primary" :loading="placeSubmitting" :disabled="placeDisabled" @click="handlePlace">
          确认放入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
<style scoped>
/* 卡头右侧：机房元信息 + 「添加排」按钮（与机房名同一水平线） */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.room-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.room-address {
  color: var(--text-secondary, #606266);
  font-size: 13px;
}
.room-note {
  color: #909399;
  font-size: 13px;
}
.room-tabs {
  margin-top: 4px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
/* 紧凑统计条（ADR-027：替代深蓝横幅）：灰字 12px，数字 600 */
.row-stats {
  font-size: 12px;
  color: #909399;
  font-variant-numeric: tabular-nums;
}
.row-stats b {
  font-weight: 600;
  color: #606266;
}
.toolbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.room-note-alert {
  margin-bottom: 12px;
}
/* 主题 primary 按钮（「添加排」/「添加机柜」）：统一蓝底白字
   显式声明文字色，避免被自定义样式或主题变量覆盖成白底白字 */
.toolbar .el-button--primary,
.header-right .el-button--primary {
  --el-button-text-color: #fff;
  --el-button-hover-text-color: #fff;
  --el-button-active-text-color: #fff;
  --el-button-disabled-text-color: #fff;
  color: #fff;
  background-color: var(--primary-color, #2563eb);
  border-color: var(--primary-color, #2563eb);
}
.toolbar .el-button--primary:hover,
.header-right .el-button--primary:hover {
  background-color: var(--primary-hover, #1d4ed8);
  border-color: var(--primary-hover, #1d4ed8);
}
.muted {
  color: #909399;
  font-size: 13px;
}

/* 空排提示 */
.empty-row-tip {
  padding: 24px;
  text-align: center;
  color: #909399;
  font-size: 13px;
  background: #fafbfc;
  border: 1px dashed #e5e7eb;
  border-radius: 8px;
}

/* ============================================================
   点位图（ADR-027 视觉重设计）：整排浅灰卡片 → 机柜组（组头 + 机架卡片）
   ============================================================ */
/* 整排容器：浅灰底卡片，机架"立"在浅灰底上 */
.row-board {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #f3f5f7;
  border-radius: 12px;
  overflow-x: auto;
}
/* 机柜组：组头 + 柜内机架卡片（组头与机架卡拼成一张视觉卡片） */
.cab-group {
  flex: none;
}
/* 机柜组头：浅灰圆角顶，机柜名 + 状态点 + ⋯ 菜单（表头第一层，30px） */
.cab-head {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 8px;
  background: #f7f8fa;
  border: 1px solid #e8eaed;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
}
.cab-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 状态圆点：通电绿 / 未通电灰（8px，title 提示） */
.cab-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.cab-dot-on {
  background: #34c759;
}
.cab-dot-off {
  background: #c7ccd1;
}
/* ⋯ 更多按钮：常态可见、点击展开下拉（内网环境不依赖 hover） */
.cab-more {
  margin-left: auto;
  flex: none;
}
.cab-more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #909399;
  cursor: pointer;
}
.cab-more-btn:hover {
  background: #e8eaed;
  color: #606266;
}
/* 柜内机架卡片行：列间距 12px */
.cab-racks {
  display: flex;
  gap: 12px;
}
/* 机架卡片：白底 + 1px #e8eaed 边框 + 圆角底（与组头拼成完整圆角卡） */
.rack-card {
  flex: none;
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 0 0 8px 8px;
  overflow: hidden;
}
/* 机架头：浅灰，机架名 + 占用/容量；hover 浮现编辑/删除图标（表头第二层，34px，合计 ~64px） */
.rack-head {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 8px;
  background: #f7f8fa;
  border-bottom: 1px solid #e8eaed;
}
.rack-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rack-cap {
  font-size: 11px;
  color: #909399;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
/* 机架编辑/删除：hover 卡片时右上角浮现（16px 图标，非 hover 不占交互） */
.rack-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}
.rack-card:hover .rack-actions {
  opacity: 1;
  pointer-events: auto;
}
.rack-act-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: #909399;
  font-size: 16px;
  cursor: pointer;
}
.rack-act-btn:hover {
  color: var(--primary-color, #2563eb);
  background: #eef3fe;
}
.rack-act-del:hover {
  color: #f56c6c;
  background: #fef0f0;
}
/* 空机柜占位：2 列结构（U位空列 + 「暂无机架」10px 灰字），卡体浅灰底 */
.rack-empty-u {
  width: 44px;
  min-width: 44px;
}
.rack-empty-text {
  font-size: 10px;
  color: #9aa3ad;
  white-space: nowrap;
}
/* 占位卡体固定 172px（= 44 U位列 + 128 设备格），保证占位卡与正常机架卡（174px 含边框）等宽 */
.rack-body-empty {
  width: 172px;
  background: #fafbfc;
}
/* 机架卡体行：行高 34px，行分隔 1px #f0f1f3 */
.rack-row {
  display: flex;
  height: 34px;
  border-bottom: 1px solid #f0f1f3;
}
.rack-row:last-child {
  border-bottom: none;
}
/* U 位号列：44px，#fafbfc 底，10px #9aa3ad 水平居中（ADR-027 验收补丁：右对齐→居中） */
.u-num {
  width: 44px;
  min-width: 44px;
  background: #fafbfc;
  border-right: 1px solid #f0f1f3;
  font-size: 10px;
  line-height: 34px;
  color: #9aa3ad;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
/* 设备格：128px */
.u-slot {
  position: relative;
  width: 128px;
  min-width: 128px;
}
/* 已占用格：色块完全铺满整格（inset 0，无圆角避免露白边）+ 左侧 2px 状态条 */
.u-block {
  position: absolute;
  inset: 0;
  display: flex;
  overflow: hidden;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s, filter 0.2s;
}
/* ADR-028 多 U 合并色块：跨 u_size 行（高度 = size×34，铺满无 margin 补偿），
   z-index 保证覆盖后续行透明占位格（视觉与点击均落在块上）；
   inset: 0 完全铺满整格宽度（right:auto 会 shrink-to-fit 导致文字窄的块露白） */
.u-block-multi {
  inset: 0;
  z-index: 1;
}
/* 合并块内部的行分隔线隐藏 */
.rack-row.row-in-block {
  border-bottom: none;
}
.u-block::before {
  content: '';
  flex: none;
  width: 2px;
}
.u-block-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  padding: 0 5px;
}
.u-block-model {
  max-width: 100%;
  font-size: 11px;
  line-height: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}
.u-block-ip {
  max-width: 100%;
  font-size: 10px;
  line-height: 11px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}
/* 四色状态体系（ADR-028 裁决，2026-10-27 再调整：对齐设备列表 el-tag 色）：
   租赁中=橙 / 故障=红 / 空闲中=绿 / 已断电=灰黑 */
/* 租赁中：橙系（= 列表 el-tag type="warning" 同色系；底 #fdf3e3 / 条 #e6a23c EP warning 标准色 / 型号 #8a5a12 / IP #b8905c） */
.u-block-rented {
  background: #fdf3e3;
}
.u-block-rented::before {
  background: #e6a23c;
}
.u-block-rented .u-block-model {
  color: #8a5a12;
}
.u-block-rented .u-block-ip {
  color: #b8905c;
}
.u-block-rented:hover {
  background: #f9e6c4;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}
/* 故障：红系（底 #fdecec / 条 #e06c6c / 型号 #a33 / IP #c98a8a） */
.u-block-fault {
  background: #fdecec;
}
.u-block-fault::before {
  background: #e06c6c;
}
.u-block-fault .u-block-model {
  color: #a33;
}
.u-block-fault .u-block-ip {
  color: #c98a8a;
}
.u-block-fault:hover {
  background: #f9dcdc;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}
/* 空闲中：绿系（底 #e7f4e4 / 条 #34c759 / 型号 #2b6b23 / IP #7a8a76） */
.u-block-idle {
  background: #e7f4e4;
}
.u-block-idle::before {
  background: #34c759;
}
.u-block-idle .u-block-model {
  color: #2b6b23;
}
.u-block-idle .u-block-ip {
  color: #7a8a76;
}
.u-block-idle:hover {
  background: #d6edc9;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}
/* 已断电：灰黑系（深灰近黑，非纯黑；底 #f0f1f3 / 条 #6b7280 / 型号 #3d4450 / IP #8a919c） */
.u-block-off {
  background: #f0f1f3;
}
.u-block-off::before {
  background: #6b7280;
}
.u-block-off .u-block-model {
  color: #3d4450;
}
.u-block-off .u-block-ip {
  color: #8a919c;
}
.u-block-off:hover {
  background: #e2e4e8;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}
/* 空格：白底无字；hover 整格浅绿底 + 中央浮现 "+"（12px 绿） */
.u-slot-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s;
}
.u-slot-empty::after {
  content: '+';
  font-size: 12px;
  color: #34c759;
  opacity: 0;
  transition: opacity 0.15s;
}
.u-slot-empty:hover {
  background: #f0f9ee;
}
.u-slot-empty:hover::after {
  opacity: 1;
}

/* ADR-029：机柜断电 → 整列（组头以下）灰化叠加（纯视觉，不改设备 status 数据与 4 色语义）：
   设备色块灰化压暗（保留原色相可辨），空格格区轻灰底；power_on=true 时 class 移除立即还原 */
.cab-power-off .u-block {
  filter: grayscale(1) opacity(0.55);
}
.cab-power-off .u-slot-empty {
  background: #f7f8fa;
  filter: grayscale(1) opacity(0.55);
}
.cab-power-off .u-slot-empty:hover {
  background: #f0f2f5;
}

/* 未定位 U 的在架设备提示 */
.unlocated-box {
  margin-top: 12px;
  padding: 10px 12px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 6px;
}
.unlocated-title {
  font-size: 13px;
  color: #e6a23c;
  margin-bottom: 8px;
}
.unlocated-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.unlocated-tag {
  cursor: pointer;
}

/* 仓库 tab */
.warehouse-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 6px;
  color: #409eff;
  font-size: 13px;
}
.col-name-link {
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
.col-muted {
  color: #c0c4cc;
}

/* 放入设备对话框 */
.place-target {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 12px;
}
.place-target .muted {
  font-size: 13px;
}
.place-target-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}
/* ADR-028 上架预校验：占用区间预览 / 越界重叠红字 */
.place-preview {
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 13px;
}
.place-ok {
  color: #2b6b23;
  font-weight: 600;
}
.place-error {
  color: #f56c6c;
  font-weight: 600;
}
.place-search {
  margin-bottom: 12px;
}
</style>
