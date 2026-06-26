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
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Box,
  Coin,
  Connection,
  Monitor,
  Lock,
} from '@element-plus/icons-vue'
import {
  createRental,
  getRental,
  updateRental,
  type DataDisk,
  type RentalCreatePayload,
  type RentalDetail,
  type RentalUpdatePayload,
} from '@/api/modules/rental'

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
  system_disk_gb: number
  data_disks: DataDisk[]
  os_version: string
  bandwidth_mbps: number
  rack_location: string
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
  system_disk_gb: 480,
  data_disks: [{ size_gb: 1000, type: 'NVMe SSD' }],
  os_version: '',
  bandwidth_mbps: 1000,
  rack_location: '',
  private_ip: '',
  public_ips_text: '',
  ssh_port: 22,
  root_username: 'root',
  root_password: '',
  remark: '',
  status: '空闲中',
})

// ============================================================
// 数据盘动态行
// ============================================================
function addDisk() {
  form.data_disks.push({ size_gb: 1000, type: 'SATA SSD' })
}
function removeDisk(idx: number) {
  if (form.data_disks.length <= 1) {
    ElMessage.warning('至少保留一块数据盘')
    return
  }
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
    form.machine_model = data.machine_model ?? ''
    form.cpu_model = data.cpu_model ?? ''
    form.memory_gb = data.memory_gb ?? 0
    form.gpu_info = data.gpu_info ?? ''
    form.system_disk_gb = data.system_disk_gb ?? 0
    form.data_disks = data.data_disks && data.data_disks.length
      ? data.data_disks
      : [{ size_gb: 1000, type: 'NVMe SSD' }]
    form.os_version = data.os_version ?? ''
    form.bandwidth_mbps = data.bandwidth_mbps ?? 1000
    form.rack_location = data.rack_location ?? ''
    form.private_ip = data.private_ip ?? ''
    form.public_ips_text = (data.public_ips ?? []).join(',')
    form.ssh_port = data.ssh_port
    form.root_username = data.root_username ?? ''
    form.root_password = data.root_password ?? ''
    form.remark = data.remark ?? ''
    form.status = data.status ?? '空闲中'
  } catch (e) {
    // 错误已统一处理
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
  system_disk_gb: [{ required: true, message: '请输入系统盘大小', trigger: 'blur' }],
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
    system_disk_gb: form.system_disk_gb,
    data_disks: form.data_disks,
    os_version: form.os_version,
    bandwidth_mbps: form.bandwidth_mbps,
    rack_location: form.rack_location,
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
    // 错误已统一处理
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
    form.machine_model = d.machine_model ?? ''
    form.cpu_model = d.cpu_model ?? ''
    form.memory_gb = d.memory_gb ?? 0
    form.gpu_info = d.gpu_info ?? ''
    form.system_disk_gb = d.system_disk_gb ?? 0
    form.data_disks = d.data_disks && d.data_disks.length
      ? d.data_disks.map((x) => ({ size_gb: x.size_gb, type: x.type }))
      : [{ size_gb: 1000, type: 'NVMe SSD' }]
    form.os_version = d.os_version ?? ''
    form.bandwidth_mbps = d.bandwidth_mbps ?? 1000
    form.rack_location = d.rack_location ?? ''
    form.private_ip = d.private_ip ?? ''
    form.public_ips_text = (d.public_ips ?? []).join(',')
    form.ssh_port = d.ssh_port ?? 22
    form.root_username = d.root_username ?? 'root'
    // 密码敏感：不预填
    form.root_password = ''
    form.remark = d.remark ?? ''
    form.status = d.status ?? '空闲中'
    ElMessage.success('已复制设备信息，请修改后保存')
  } catch {
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
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            {{ isEdit ? '编辑设备' : '创建设备' }}
          </span>
          <el-button link @click="cancel">返回</el-button>
        </div>
      </template>

      <!-- 编辑模式：展示从合同继承的信息 -->
      <template v-if="isEdit && detail?.contract_info">
        <div class="contract-info-card">
          <el-descriptions
            title="关联合同信息（只读，由合同管理）"
            :column="4"
            border
            size="small"
          >
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
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        class="rental-form"
        @submit.prevent
      >
        <!-- 1. 基础信息 -->
        <div class="section-title">
          <el-icon><Box /></el-icon>
          基础信息
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="机器型号" prop="machine_model">
              <el-input v-model="form.machine_model" placeholder="如 Dell PowerEdge R740" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="CPU 型号" prop="cpu_model">
              <el-input v-model="form.cpu_model" placeholder="如 2×Intel Xeon Gold 6248R 48C" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="内存 (GB)" prop="memory_gb">
              <el-input-number
                v-model="form.memory_gb"
                :min="1"
                :max="65536"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="GPU">
              <el-input v-model="form.gpu_info" placeholder="如 8×NVIDIA A100 80GB" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备状态">
              <el-select v-model="form.status" placeholder="选择状态" style="width: 100%">
                <el-option label="空闲中" value="空闲中" />
                <el-option label="已断电" value="已断电" />
                <el-option label="租赁中" value="租赁中" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 2. 存储 -->
        <div class="section-title">
          <el-icon><Coin /></el-icon>
          存储
        </div>
        <el-form-item label="系统盘 (GB)" prop="system_disk_gb">
          <el-input-number
            v-model="form.system_disk_gb"
            :min="0"
            :max="1000000"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="数据盘">
          <div class="disk-list">
            <div v-for="(d, idx) in form.data_disks" :key="idx" class="disk-row">
              <el-input-number
                v-model="d.size_gb"
                :min="0"
                :max="1000000"
                style="width: 180px"
              />
              <span style="margin: 0 8px">GB ·</span>
              <el-input
                v-model="d.type"
                placeholder="类型，如 NVMe SSD"
                style="width: 220px"
              />
              <el-button
                link
                type="danger"
                style="margin-left: 8px"
                @click="removeDisk(idx)"
              >
                删除
              </el-button>
            </div>
            <el-button @click="addDisk" style="margin-top: 4px">+ 添加数据盘</el-button>
          </div>
        </el-form-item>

        <!-- 3. 网络 -->
        <div class="section-title">
          <el-icon><Connection /></el-icon>
          网络
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="内网IP" prop="private_ip">
              <el-input v-model="form.private_ip" placeholder="如 10.0.0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="公网IP">
              <el-input
                v-model="form.public_ips_text"
                placeholder="多个用逗号分隔，如 1.2.3.4,1.2.3.5"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="SSH 端口" prop="ssh_port">
              <el-input-number
                v-model="form.ssh_port"
                :min="1"
                :max="65535"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
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

        <!-- 4. 系统 -->
        <div class="section-title">
          <el-icon><Monitor /></el-icon>
          系统
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="操作系统" prop="os_version">
              <el-input v-model="form.os_version" placeholder="如 Ubuntu 22.04 LTS" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="机架位置">
              <el-input v-model="form.rack_location" placeholder="如 A01-05-U12" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 5. 凭证 -->
        <div class="section-title">
          <el-icon><Lock /></el-icon>
          凭证
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="root 账号" prop="root_username">
              <el-input v-model="form.root_username" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
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

        <!-- 备注 -->
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
      </el-form>

      <!-- 操作按钮 -->
      <div class="step-actions">
        <el-button @click="cancel">取消</el-button>
        <div class="spacer" />
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-header .title {
  font-size: 16px;
  font-weight: 600;
}
.rental-form {
  max-width: 1100px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 18px 0 12px;
  padding-left: 10px;
  border-left: 3px solid var(--primary-color);
  display: flex;
  align-items: center;
  gap: 6px;
}
.section-title .el-icon {
  color: var(--primary-color);
  font-size: 16px;
}
.disk-list {
  width: 100%;
}
.disk-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.step-actions {
  display: flex;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
.spacer {
  flex: 1;
}
.contract-info-card {
  margin-bottom: 20px;
}
</style>
