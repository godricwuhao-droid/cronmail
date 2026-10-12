<script setup lang="ts">
/**
 * 机房管理 - 详情页 / U 位点阵图（ADR-022，替代 ADR-021 卡片式点位图）
 *
 * 功能：
 *  - U 位点阵图：多机架并排表格（列=机架，行=U 位，1 在最下），
 *    格内显示 型号/用途/内网IP，按状态着色（已断电红 / 租赁中·空闲中绿 / 空格灰），
 *    点击有设备格跳设备详情
 *  - 添加机架 / 编辑 capacity_u / 删除机架（409 展示后端 detail）
 *  - 未定位 U 的在架设备在点阵图下方单独提示
 *  - 仓库 tab：未上架设备（全局）表格 + 「上架」选本机房机架 + U 位（可空）
 *    → PUT /api/rentals/{id} 提交 machine_room_id + rack_id + u_position
 *  - 数据全部来自 GET /api/machine-rooms/{id}/points
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Delete, Edit, OfficeBuilding, Plus } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
import {
  createRack,
  deleteRack,
  getMachineRoomPoints,
  updateRack,
  type MachineRoom,
  type RackCell,
  type RackPoint,
  type RoomDeviceBrief,
} from '@/api/modules/machine-room'
import { updateRental } from '@/api/modules/rental'
import { safeStatusLabel, safeStatusTagType } from '@/lib/rental'

const route = useRoute()
const router = useRouter()

const roomId = computed(() => route.params.id as string)

// ============================================================
// 点位图数据
// ============================================================
const loading = ref(false)
const room = ref<MachineRoom | null>(null)
const racks = ref<RackPoint[]>([])
const warehoused = ref<RoomDeviceBrief[]>([])
const activeTab = ref('points')

async function loadPoints() {
  loading.value = true
  try {
    const data = await getMachineRoomPoints(roomId.value)
    room.value = data.room
    racks.value = data.racks
    warehoused.value = data.warehoused
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// U 位点阵图（ADR-022）
// ============================================================
/** 所有机架 capacity_u 最大值（点阵图行数） */
const maxU = computed(() => racks.value.reduce((m, r) => Math.max(m, r.capacity_u), 0))

/** 点阵图行：U 位自上而下 最大 → 1（1 在最下，与机房惯例一致） */
const gridRows = computed<Array<{ u: number; cells: RackCell[] }>>(() => {
  const rows: Array<{ u: number; cells: RackCell[] }> = []
  for (let u = maxU.value; u >= 1; u--) {
    rows.push({
      u,
      cells: racks.value.map((r) =>
        r.u_cells.find((c) => c.u === u) ?? {
          u,
          rental_id: null,
          machine_model: null,
          remark: null,
          private_ip: null,
          status: null,
        },
      ),
    })
  }
  return rows
})

/** 机架已定位 U 的设备数（u_cells 中非空格数） */
function rackOccupiedCount(rack: RackPoint) {
  return rack.u_cells.filter((c) => c.rental_id != null).length
}

/** 单元格状态类名：已断电→红 / 租赁中·空闲中→绿 / 空→灰 */
function cellClass(cell: RackCell): string {
  if (!cell.rental_id) return 'u-cell-empty'
  if (cell.status === '已断电') return 'u-cell-off'
  return 'u-cell-on'
}

/**
 * 未定位 U 的在架设备：
 * devices 摘要（rack_location 前缀匹配到机架）中，未出现在该机架 u_cells 里的设备
 */
const unlocatedDevices = computed<RoomDeviceBrief[]>(() =>
  racks.value.flatMap((r) => {
    const placed = new Set(
      r.u_cells.filter((c) => c.rental_id != null).map((c) => c.rental_id),
    )
    return r.devices.filter((d) => !placed.has(d.rental_id))
  }),
)

// ============================================================
// 机架：新建 / 编辑 / 删除
// ============================================================
const rackDialogVisible = ref(false)
const editingRack = ref<RackPoint | null>(null)
const rackSubmitting = ref(false)
const rackFormRef = ref<FormInstance>()

const rackForm = reactive({
  name: '',
  capacity_u: 42,
})

const rackRules: FormRules = {
  name: [{ required: true, message: '请输入机架名称', trigger: 'blur' }],
  capacity_u: [{ required: true, message: '请输入 U 位容量', trigger: 'blur' }],
}

function openCreateRack() {
  editingRack.value = null
  rackForm.name = ''
  rackForm.capacity_u = 42
  rackDialogVisible.value = true
}

function openEditRack(rack: RackPoint) {
  editingRack.value = rack
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
      // 编辑仅开放 capacity_u（改机架名会破坏 rack_location 前缀匹配）
      await updateRack(roomId.value, editingRack.value.id, { capacity_u: rackForm.capacity_u })
      ElMessage.success('机架已更新')
    } else {
      await createRack(roomId.value, { name: rackForm.name.trim(), capacity_u: rackForm.capacity_u })
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
    await deleteRack(roomId.value, rack.id, { __silent: true })
    ElMessage.success('机架已删除')
    loadPoints()
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

// ============================================================
// 仓库：上架（选本机房机架 → PUT /api/rentals/{id} 传 machine_room_id）
// ============================================================
const rackUpVisible = ref(false)
const rackUpDevice = ref<RoomDeviceBrief | null>(null)
const rackUpRackId = ref<number | ''>('')
/** U 位（ADR-022，可空 = 不指定 U 位） */
const rackUpU = ref<number | null>(null)
const rackUpSubmitting = ref(false)

/** 上架对话框中选中的机架 */
const rackUpSelectedRack = computed(() =>
  racks.value.find((r) => r.id === rackUpRackId.value) ?? null,
)

function openRackUp(device: RoomDeviceBrief) {
  if (racks.value.length === 0) {
    ElMessage.warning('本机房暂无机架，请先添加机架')
    return
  }
  rackUpDevice.value = device
  rackUpRackId.value = ''
  rackUpU.value = null
  rackUpVisible.value = true
}

/** 换机架：清空 U 位（容量不同） */
function handleRackUpRackChange() {
  rackUpU.value = null
}

/** U 位超出所选机架容量时截断并提示 */
function handleRackUpUChange() {
  const rack = rackUpSelectedRack.value
  if (rack && rackUpU.value != null && rackUpU.value > rack.capacity_u) {
    ElMessage.warning(`U 位超出机架 ${rack.name} 容量（1~${rack.capacity_u}）`)
    rackUpU.value = rack.capacity_u
  }
}

async function handleRackUp() {
  if (!rackUpDevice.value || rackUpRackId.value === '') {
    ElMessage.warning('请选择目标机架')
    return
  }
  rackUpSubmitting.value = true
  try {
    await updateRental(rackUpDevice.value.rental_id, {
      machine_room_id: Number(roomId.value),
      rack_id: rackUpRackId.value,
      u_position: rackUpU.value,
    })
    ElMessage.success(rackUpU.value == null ? '上架成功（未指定 U 位）' : '上架成功')
    rackUpVisible.value = false
    loadPoints()
  } catch (e) {
    // 409 U 位冲突：统一拦截器不展示 detail，这里手动提示
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      ElMessage.error(detail || 'U 位已被占用')
    }
    // 其余错误已统一处理
  } finally {
    rackUpSubmitting.value = false
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
      <!-- 机房信息头 -->
      <div class="card-header">
        <span class="title">
          <el-icon><OfficeBuilding /></el-icon>
          {{ room?.name || '机房详情' }}
        </span>
        <div class="room-meta">
          <el-tag v-if="room?.code" type="info" size="small">{{ room.code }}</el-tag>
          <span v-if="room?.address" class="room-address">{{ room.address }}</span>
          <span v-if="room?.note" class="room-note">{{ room.note }}</span>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="room-tabs">
        <!-- 点位图 -->
        <el-tab-pane label="点位图" name="points">
          <div class="toolbar">
            <el-button type="primary" :icon="Plus" @click="openCreateRack">添加机架</el-button>
            <span class="muted">
              共 {{ racks.length }} 个机架 ·
              {{ racks.reduce((sum, r) => sum + rackOccupiedCount(r), 0) }} 台已定位 U 位设备
            </span>
          </div>

          <el-empty v-if="!racks.length" description="暂无机架，点击「添加机架」创建" :image-size="72" />

          <!-- U 位点阵图（ADR-022）：列=机架，行=U 位（1 在最下），横向可滚动 -->
          <div v-else class="u-grid-wrap">
            <table class="u-grid">
              <thead>
                <tr>
                  <th class="u-grid-u-col">U 位</th>
                  <th v-for="rack in racks" :key="rack.id" class="u-grid-rack-col">
                    <div class="u-grid-rack-head">
                      <span class="u-grid-rack-name">{{ rack.name }}</span>
                      <span class="u-grid-rack-cap">
                        {{ rackOccupiedCount(rack) }} / {{ rack.capacity_u }}
                      </span>
                      <span class="u-grid-rack-acts">
                        <el-tooltip content="编辑 U 位容量" placement="top">
                          <el-button link :icon="Edit" @click="openEditRack(rack)" />
                        </el-tooltip>
                        <el-tooltip content="删除机架" placement="top">
                          <el-button link type="danger" :icon="Delete" @click="handleDeleteRack(rack)" />
                        </el-tooltip>
                      </span>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in gridRows" :key="row.u">
                  <td class="u-grid-u-col">{{ row.u }}</td>
                  <td v-for="(cell, idx) in row.cells" :key="racks[idx].id">
                    <div
                      v-if="cell.rental_id"
                      class="u-cell"
                      :class="cellClass(cell)"
                      @click="goRental(cell.rental_id!)"
                    >
                      <div class="u-cell-model">{{ cell.machine_model || '—' }}</div>
                      <div class="u-cell-remark">{{ cell.remark || '—' }}</div>
                      <div class="u-cell-ip">{{ cell.private_ip || '—' }}</div>
                    </div>
                    <div v-else class="u-cell u-cell-empty">
                      <span class="u-cell-u">{{ cell.u }}</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 未定位 U 的在架设备提示 -->
          <div v-if="unlocatedDevices.length" class="unlocated-box">
            <div class="unlocated-title">以下设备已关联机架但未指定 U 位：</div>
            <div class="unlocated-list">
              <el-tag
                v-for="d in unlocatedDevices"
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
        <el-tab-pane :label="`仓库（${warehoused.length}）`" name="warehouse">
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
                <span v-if="row.rack_location">{{ row.rack_location }}</span>
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
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button size="small" link type="primary" @click="openRackUp(row)">上架</el-button>
                  <el-button size="small" link type="primary" @click="goRental(row.rental_id)">详情</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

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
            placeholder="如 A-01（设备机架位置以此名为前缀匹配）"
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

    <!-- 仓库上架对话框 -->
    <el-dialog v-model="rackUpVisible" title="上架设备" width="440px" :close-on-click-modal="false">
      <div v-if="rackUpDevice" class="rack-up-body">
        <div class="rack-up-device">
          <div>
            <div class="muted">机器型号</div>
            <div>{{ rackUpDevice.machine_model || '—' }}</div>
          </div>
          <div>
            <div class="muted">当前位置</div>
            <div>{{ rackUpDevice.rack_location || '—' }}</div>
          </div>
        </div>
        <el-form label-position="top">
          <el-form-item label="目标机架" required>
            <el-select
              v-model="rackUpRackId"
              placeholder="选择本机房机架"
              style="width: 100%"
              @change="handleRackUpRackChange"
            >
              <el-option
                v-for="rack in racks"
                :key="rack.id"
                :label="`${rack.name}（${rackOccupiedCount(rack)}/${rack.capacity_u} U）`"
                :value="rack.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="U 位（可空 = 不指定 U 位）">
            <el-input-number
              v-model="rackUpU"
              :min="1"
              :max="rackUpSelectedRack ? rackUpSelectedRack.capacity_u : undefined"
              :disabled="rackUpRackId === ''"
              placeholder="留空表示不指定"
              style="width: 100%"
              @change="handleRackUpUChange"
            />
          </el-form-item>
        </el-form>
        <el-alert
          type="info"
          :closable="false"
          title="指定 U 位后设备将显示在点阵图对应格子中；同机架同 U 位只能放一台设备"
        />
      </div>
      <template #footer>
        <el-button @click="rackUpVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="rackUpSubmitting"
          :disabled="rackUpRackId === ''"
          @click="handleRackUp"
        >
          确认上架
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.room-meta {
  display: flex;
  align-items: center;
  gap: 10px;
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
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.muted {
  color: #909399;
  font-size: 13px;
}

/* U 位点阵图（ADR-022） */
.u-grid-wrap {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.u-grid {
  border-collapse: separate;
  border-spacing: 0;
  min-width: 100%;
}
.u-grid th,
.u-grid td {
  border-right: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  padding: 0;
  vertical-align: middle;
}
.u-grid th:last-child,
.u-grid td:last-child {
  border-right: none;
}
.u-grid tbody tr:last-child td {
  border-bottom: none;
}
.u-grid-u-col {
  position: sticky;
  left: 0;
  z-index: 2;
  width: 56px;
  min-width: 56px;
  background: #fafbfc;
  text-align: center;
  font-size: 12px;
  color: #909399;
  font-variant-numeric: tabular-nums;
  border-right: 1px solid #e5e7eb;
}
.u-grid thead .u-grid-u-col {
  z-index: 3;
  font-weight: 600;
  color: #606266;
  padding: 8px 4px;
}
.u-grid-rack-col {
  min-width: 140px;
  width: 140px;
}
.u-grid-rack-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #fafbfc;
}
.u-grid-rack-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}
.u-grid-rack-cap {
  font-size: 12px;
  color: #909399;
  font-variant-numeric: tabular-nums;
}
.u-grid-rack-acts {
  margin-left: auto;
  display: flex;
  gap: 2px;
}
.u-cell {
  min-height: 48px;
  padding: 4px 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1px;
  overflow: hidden;
}
/* 空格：浅灰底，只显 U 号小字 */
.u-cell-empty {
  background: #f5f7fa;
  align-items: flex-end;
}
.u-cell-u {
  font-size: 11px;
  color: #c0c4cc;
  font-variant-numeric: tabular-nums;
}
/* 已断电：红底 */
.u-cell-off {
  background: #fde2e2;
  cursor: pointer;
  transition: background 0.15s;
}
.u-cell-off:hover {
  background: #fbcfcf;
}
/* 租赁中 / 空闲中：绿底 */
.u-cell-on {
  background: #e1f3d8;
  cursor: pointer;
  transition: background 0.15s;
}
.u-cell-on:hover {
  background: #d0eac4;
}
.u-cell-model {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.u-cell-remark {
  font-size: 11px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.u-cell-ip {
  font-size: 11px;
  color: #909399;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
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

/* 上架对话框 */
.rack-up-device {
  display: flex;
  gap: 24px;
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}
.rack-up-device .muted {
  font-size: 12px;
  margin-bottom: 2px;
}
</style>
