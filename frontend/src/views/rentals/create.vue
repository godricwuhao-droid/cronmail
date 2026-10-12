<script setup lang="ts">
/**
 * 设备 - 创建 / 编辑（共用页面）
 *
 * 复用规则：
 *  - 路由 /rentals/create → 新建模式
 *  - 路由 /rentals/:id/edit → 编辑模式
 *
 * 表单仅保留硬件信息，客户/日期/计费/联系人由合同管理。
 * 编辑模式下展示从合同继承的信息（el-descriptions 只读）。
 *
 * UI 参考 device-input-temp.html 风格：
 *  - 分区标题：16px / 600 字重 / 左侧蓝色竖条装饰
 *  - 表单控件：统一圆角、边框、focus 蓝色阴影
 *  - 标签：14px / #595959 / 500 字重，必填红色星号
 *  - 数据盘：列表式展示，字符串输入
 *  - 底部按钮：右对齐，顶部分割线
 */
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Document, InfoFilled } from '@element-plus/icons-vue'
import {
  createRental,
  getRental,
  updateRental,
  type RentalCreatePayload,
  type RentalDetail,
  type RentalUpdatePayload,
} from '@/api/modules/rental'
import {
  getMachineRooms,
  getMachineRoomPoints,
  type MachineRoom,
  type RackPoint,
} from '@/api/modules/machine-room'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const rentalId = computed(() => (route.params.id as string) || '')

// ============================================================
// 表单数据（仅硬件信息）
// ============================================================
interface RentalForm {
  machine_model: string
  cpu_model: string
  memory_gb: number
  gpu_info: string
  system_disk: string
  data_disks: string[]
  os_version: string
  bandwidth_mbps: number
  rack_location: string
  /** 所属机房 ID（ADR-021），null 表示未上架/在库 */
  machine_room_id: number | null
  /** 机架 ID（ADR-022），null 表示未上架到具体机架 */
  rack_id: number | null
  /** U 位（ADR-022，1~机架 capacity_u），null 表示不指定 U 位 */
  u_position: number | null
  private_ip: string
  public_ips_text: string
  ssh_port: number
  root_username: string
  root_password: string
  remark: string
  status: string
}

const form = reactive<RentalForm>({
  machine_model: '',
  cpu_model: '',
  memory_gb: 64,
  gpu_info: '',
  system_disk: '480GB SATA SSD',
  data_disks: ['2000GB NVMe SSD'],
  os_version: '',
  bandwidth_mbps: 1000,
  rack_location: '',
  machine_room_id: null,
  rack_id: null,
  u_position: null,
  private_ip: '',
  public_ips_text: '',
  ssh_port: 22,
  root_username: 'root',
  root_password: '',
  remark: '',
  status: '空闲中',
})

// ============================================================
// 所属机房下拉（ADR-021，可空 = 未上架/在库）
// ============================================================
const roomOptions = ref<MachineRoom[]>([])
async function loadRoomOptions() {
  try {
    const res = await getMachineRooms()
    roomOptions.value = res.items
  } catch (e) {
    // 错误已统一处理
  }
}

// ============================================================
// 机架 / U 位联动（ADR-022：机房 → 机架 → U 位）
// ============================================================
const rackOptions = ref<RackPoint[]>([])
/** 机架列表按机房缓存，避免机房来回切换重复请求 */
const rackCache = new Map<number, RackPoint[]>()

async function loadRackOptions(roomId: number) {
  const cached = rackCache.get(roomId)
  if (cached) {
    rackOptions.value = cached
    return
  }
  try {
    const res = await getMachineRoomPoints(roomId)
    rackCache.set(roomId, res.racks)
    rackOptions.value = res.racks
  } catch (e) {
    // 错误已统一处理
  }
}

/** 当前选中机架（取 capacity_u 约束 U 位范围） */
const selectedRack = computed(
  () => rackOptions.value.find((r) => r.id === form.rack_id) ?? null,
)

/** 回填标记：编辑/复制回填期间不让联动 watch 清空机架/U 位 */
let restoring = false

/** 机房变更：清空机架与 U 位，加载新机房机架列表 */
watch(
  () => form.machine_room_id,
  (roomId, oldRoomId) => {
    if (roomId === oldRoomId) return
    if (!restoring) {
      form.rack_id = null
      form.u_position = null
      rackOptions.value = []
    }
    if (roomId != null) {
      loadRackOptions(roomId)
    }
  },
)

/** 机架变更：清空 U 位（容量不同） */
watch(
  () => form.rack_id,
  (rackId, oldRackId) => {
    if (rackId === oldRackId) return
    if (!restoring) {
      form.u_position = null
    }
  },
)

/** U 位超出所选机架容量时截断并提示 */
watch(
  () => form.u_position,
  (u) => {
    const rack = selectedRack.value
    if (rack && u != null && u > rack.capacity_u) {
      ElMessage.warning(`U 位超出机架 ${rack.name} 容量（1~${rack.capacity_u}）`)
      form.u_position = rack.capacity_u
    }
  },
)

// ============================================================
// 数据盘动态行
// ============================================================
const newDiskText = ref('')

function addDisk() {
  const text = newDiskText.value.trim()
  if (!text) {
    ElMessage.warning('请输入数据盘信息')
    return
  }
  form.data_disks.push(text)
  newDiskText.value = ''
}

function removeDisk(idx: number) {
  form.data_disks.splice(idx, 1)
}

// ============================================================
// 加载详情（编辑模式）
// ============================================================
const detail = ref<RentalDetail | null>(null)
const loadingDetail = ref(false)

async function loadDetail() {
  if (!rentalId.value) return
  loadingDetail.value = true
  try {
    const data = await getRental(rentalId.value)
    detail.value = data
    restoring = true
    form.machine_model = data.machine_model ?? ''
    form.cpu_model = data.cpu_model ?? ''
    form.memory_gb = data.memory_gb ?? 0
    form.gpu_info = data.gpu_info ?? ''
    form.system_disk = data.system_disk ?? ''
    form.data_disks = data.data_disks ?? []
    form.os_version = data.os_version ?? ''
    form.bandwidth_mbps = data.bandwidth_mbps ?? 1000
    form.rack_location = data.rack_location ?? ''
    form.machine_room_id = data.machine_room_id ?? null
    form.rack_id = data.rack_id ?? null
    form.u_position = data.u_position ?? null
    form.private_ip = data.private_ip ?? ''
    form.public_ips_text = (data.public_ips ?? []).join(',')
    form.ssh_port = data.ssh_port
    form.root_username = data.root_username ?? ''
    form.root_password = data.root_password ?? ''
    form.remark = data.remark ?? ''
    form.status = data.status ?? '空闲中'
    // 回填机架下拉选项（watch 因值未变化不会触发，这里手动加载）
    if (form.machine_room_id != null) {
      loadRackOptions(form.machine_room_id)
    }
    // 等联动 watch 回调执行完再放开回填标记
    await nextTick()
    restoring = false
  } catch (e) {
    // 错误已统一处理
    restoring = false
  } finally {
    loadingDetail.value = false
  }
}

// ============================================================
// 校验
// ============================================================
const formRef = ref<FormInstance>()
const rules: FormRules = {
  machine_model: [{ required: true, message: '请输入机器型号', trigger: 'blur' }],
  cpu_model: [{ required: true, message: '请输入 CPU 型号', trigger: 'blur' }],
  memory_gb: [{ required: true, message: '请输入内存大小', trigger: 'blur' }],
  system_disk: [{ required: true, message: '请输入系统盘信息', trigger: 'blur' }],
  os_version: [{ required: true, message: '请输入操作系统', trigger: 'blur' }],
  private_ip: [{ required: true, message: '请输入内网IP', trigger: 'blur' }],
  ssh_port: [{ required: true, message: '请输入 SSH 端口', trigger: 'blur' }],
  root_username: [{ required: true, message: '请输入 root 账号', trigger: 'blur' }],
  root_password: [{ required: true, message: '请输入 root 密码', trigger: 'blur' }],
}

// ============================================================
// 提交
// ============================================================
const submitting = ref(false)

function buildPayload(): RentalCreatePayload | RentalUpdatePayload {
  const public_ips = form.public_ips_text
    .split(/[,，\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  return {
    machine_model: form.machine_model,
    cpu_model: form.cpu_model,
    memory_gb: form.memory_gb,
    gpu_info: form.gpu_info,
    system_disk: form.system_disk,
    data_disks: form.data_disks,
    os_version: form.os_version,
    bandwidth_mbps: form.bandwidth_mbps,
    rack_location: form.rack_location,
    machine_room_id: form.machine_room_id || null,
    // 显式传 null 表示解绑机架 / 清除 U 位（编辑模式清空选择时生效）
    rack_id: form.rack_id,
    u_position: form.u_position,
    private_ip: form.private_ip,
    public_ips,
    ssh_port: form.ssh_port,
    root_username: form.root_username,
    root_password: form.root_password,
    remark: form.remark,
    status: form.status,
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.error('请检查表单填写')
    return
  }
  submitting.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await updateRental(rentalId.value, payload as RentalUpdatePayload)
      ElMessage.success('保存成功')
      router.replace({ name: 'RentalDetail', params: { id: rentalId.value } })
    } else {
      const created = await createRental(payload as RentalCreatePayload)
      ElMessage.success('创建成功')
      router.replace({ name: 'RentalDetail', params: { id: created.id } })
    }
  } catch (e) {
    // 409 U 位冲突 / 400 机架校验：统一拦截器不展示 409 的 detail，这里手动提示
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409 || status === 400) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail) ElMessage.error(detail)
    }
    // 其余错误已统一处理
  } finally {
    submitting.value = false
  }
}

function cancel() {
  if (isEdit.value && rentalId.value) {
    router.push({ name: 'RentalDetail', params: { id: rentalId.value } })
  } else {
    router.push({ name: 'RentalList' })
  }
}

// ============================================================
// 复制模式：从 query.copy_from 读取已有设备，预填表单
// ============================================================
async function loadCopyFrom(copyId: string) {
  try {
    const d = await getRental(copyId)
    restoring = true
    form.machine_model = d.machine_model ?? ''
    form.cpu_model = d.cpu_model ?? ''
    form.memory_gb = d.memory_gb ?? 0
    form.gpu_info = d.gpu_info ?? ''
    form.system_disk = d.system_disk ?? ''
    form.data_disks = d.data_disks ?? []
    form.os_version = d.os_version ?? ''
    form.bandwidth_mbps = d.bandwidth_mbps ?? 1000
    form.rack_location = d.rack_location ?? ''
    form.machine_room_id = d.machine_room_id ?? null
    // 机架/U 位不复制：同机架同 U 位唯一占用，直接复制会 409，由用户重新指定
    form.rack_id = null
    form.u_position = null
    form.private_ip = d.private_ip ?? ''
    form.public_ips_text = (d.public_ips ?? []).join(',')
    form.ssh_port = d.ssh_port ?? 22
    form.root_username = d.root_username ?? 'root'
    // 密码敏感：不预填
    form.root_password = ''
    form.remark = d.remark ?? ''
    form.status = d.status ?? '空闲中'
    if (form.machine_room_id != null) {
      loadRackOptions(form.machine_room_id)
    }
    await nextTick()
    restoring = false
    ElMessage.success('已复制设备信息，请修改后保存')
  } catch {
    restoring = false
    ElMessage.error('加载复制数据失败')
  }
}

// ============================================================
// 辅助：计费方式中文
// ============================================================
function billingLabel(model?: string) {
  const m: Record<string, string> = {
    monthly: '按月',
    yearly: '按年',
  }
  return m[model || ''] || model || '-'
}

onMounted(async () => {
  loadRoomOptions()
  if (isEdit.value) {
    await loadDetail()
  } else {
    // 复制模式：/rentals/create?copy_from=<id>
    const copyId = route.query.copy_from as string | undefined
    if (copyId) {
      await loadCopyFrom(copyId)
    }
  }
})
</script>

<template>
  <div class="page-container" v-loading="loadingDetail">
    <div class="top-bar">
      <el-button @click="cancel">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><Document /></el-icon>
          {{ isEdit ? '编辑设备' : '创建设备' }}
        </span>
      </div>

      <div class="dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>
          <template v-if="isEdit">
            仅可编辑硬件与登录信息；客户、日期、计费等由关联合同管理。
          </template>
          <template v-else>
            填写设备硬件与网络信息；客户与计费在关联合同后自动继承。
          </template>
        </span>
      </div>

      <!-- 编辑模式：展示从合同继承的信息 -->
      <div v-if="isEdit && detail?.contract_info" class="dialog-section">
        <div class="dialog-section-title">关联合同信息（只读）</div>
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="合同名称">
            <el-link
              type="primary"
              :underline="false"
              @click="router.push({ name: 'ContractDetail', params: { id: detail.contract_info!.id } })"
            >
              {{ detail.contract_info.name }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="客户">
            {{ detail.customer?.name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="到期时间">
            {{ detail.contract_info.end_date }}
          </el-descriptions-item>
          <el-descriptions-item label="计费方式">
            {{ billingLabel(detail.contract_info.billing_model) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="rental-form"
        @submit.prevent
      >
        <!-- 1. 基础信息 -->
        <div class="dialog-section">
          <div class="dialog-section-title">基础信息</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="机器型号" prop="machine_model">
                <el-input v-model="form.machine_model" placeholder="如 8卡4090" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="设备状态">
                <el-select v-model="form.status" placeholder="选择状态" style="width: 100%">
                  <el-option label="空闲中" value="空闲中" />
                  <el-option label="已断电" value="已断电" />
                  <el-option label="租赁中" value="租赁中" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="CPU 型号" prop="cpu_model">
                <el-input v-model="form.cpu_model" placeholder="如 AMD EPYC 7K62 48C 2.60GHz * 2" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="内存 (GB)" prop="memory_gb">
                <el-input-number
                  v-model="form.memory_gb"
                  :min="1"
                  :max="65536"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="GPU">
                <el-input v-model="form.gpu_info" placeholder="如 8×NVIDIA 4090 24G" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 2. 存储 -->
        <div class="dialog-section">
          <div class="dialog-section-title">存储</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="系统盘" prop="system_disk">
                <el-input v-model="form.system_disk" placeholder="如 480GB SATA SSD" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="数据盘">
                <div class="storage-list">
                  <div
                    v-for="(disk, idx) in form.data_disks"
                    :key="idx"
                    class="storage-item"
                  >
                    <span class="storage-text">{{ disk }}</span>
                    <el-button
                      link
                      type="danger"
                      class="btn-link-small"
                      @click="removeDisk(idx)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
                <div class="storage-add-row">
                  <el-input
                    v-model="newDiskText"
                    placeholder="如 2000GB NVMe SSD"
                    @keyup.enter="addDisk"
                  />
                  <el-button type="primary" @click="addDisk">+ 添加</el-button>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 3. 网络 -->
        <div class="dialog-section">
          <div class="dialog-section-title">网络</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="内网IP" prop="private_ip">
                <el-input v-model="form.private_ip" placeholder="如 192.168.100.124" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="公网IP">
                <el-input
                  v-model="form.public_ips_text"
                  placeholder="多个用逗号分隔，如 1.2.3.4,1.2.3.5"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="SSH 端口" prop="ssh_port">
                <el-input-number
                  v-model="form.ssh_port"
                  :min="1"
                  :max="65535"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="带宽 (Mbps)">
                <el-input-number
                  v-model="form.bandwidth_mbps"
                  :min="1"
                  :max="100000"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 4. 系统 -->
        <div class="dialog-section">
          <div class="dialog-section-title">系统</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="操作系统" prop="os_version">
                <el-input v-model="form.os_version" placeholder="如 ubuntu22.04 server TLS" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="所属机房">
                <el-select
                  v-model="form.machine_room_id"
                  placeholder="未上架（在库）"
                  clearable
                  filterable
                  style="width: 100%"
                >
                  <el-option
                    v-for="r in roomOptions"
                    :key="r.id"
                    :label="r.name"
                    :value="r.id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="机架">
                <el-select
                  v-model="form.rack_id"
                  :placeholder="form.machine_room_id == null ? '请先选择所属机房' : '选择机架（可空）'"
                  :disabled="form.machine_room_id == null"
                  clearable
                  filterable
                  style="width: 100%"
                >
                  <el-option
                    v-for="r in rackOptions"
                    :key="r.id"
                    :label="`${r.name}（${r.capacity_u} U）`"
                    :value="r.id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="U 位">
                <el-input-number
                  v-model="form.u_position"
                  :min="1"
                  :max="selectedRack ? selectedRack.capacity_u : undefined"
                  :disabled="form.rack_id == null"
                  :placeholder="form.rack_id == null ? '请先选择机架' : '可空 = 不指定 U 位'"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="机架位置（兼容旧数据）">
                <el-input
                  v-model="form.rack_location"
                  placeholder="旧版自由文本位置，新设备建议用上方机架 + U 位"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 5. 凭证 -->
        <div class="dialog-section">
          <div class="dialog-section-title">凭证</div>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="root 账号" prop="root_username">
                <el-input v-model="form.root_username" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="root 密码" prop="root_password">
                <el-input
                  v-model="form.root_password"
                  type="password"
                  show-password
                  placeholder="保存时会加密存储"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 备注 -->
        <div class="dialog-section">
          <div class="dialog-section-title">备注</div>
          <el-form-item label="备注">
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="3"
              placeholder="可选"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </div>
      </el-form>

      <div class="form-actions">
        <el-button @click="cancel">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.top-bar {
  margin-bottom: 0;
}
.rental-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
}
.rental-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
.storage-list {
  width: 100%;
}
.storage-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
}
.storage-item + .storage-item {
  margin-top: 6px;
}
.storage-add-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  width: 100%;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}
</style>
