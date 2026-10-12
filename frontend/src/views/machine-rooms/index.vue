<script setup lang="ts">
/**
 * 机房管理 - 列表页（ADR-021）
 *
 * 功能：
 *  - 机房列表（名称/编码/地址/机架数/设备数/操作），支持名称/编码模糊搜索
 *  - 新建/编辑对话框（name/code/address/note）
 *  - 删除：confirmDelete 二次确认；409（机房下仍有设备）展示后端 detail
 *  - 机架数/设备数：列表接口不返回，逐机房并行调 points 接口补齐（机房数量少，可接受）
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { OfficeBuilding, Search, Refresh, RefreshLeft } from '@element-plus/icons-vue'
import { confirmDelete } from '@/lib/confirm'
import {
  createMachineRoom,
  deleteMachineRoom,
  getMachineRoomPoints,
  getMachineRooms,
  updateMachineRoom,
  type MachineRoom,
} from '@/api/modules/machine-room'

const router = useRouter()

// ============================================================
// 列表状态
// ============================================================
const loading = ref(false)
const list = ref<MachineRoom[]>([])
const searchText = ref('')

/** 机架数/设备数（points 接口补齐，key 为机房 id） */
const counts = ref<Record<number, { rack_count: number; device_count: number }>>({})

let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchList, 300)
}

function clearFilters() {
  searchText.value = ''
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params: { search?: string } = {}
    const trimmed = searchText.value.trim()
    if (trimmed) params.search = trimmed
    const res = await getMachineRooms(params)
    list.value = res.items
    // 并行补齐机架数/设备数（失败静默，不影响列表展示）
    counts.value = {}
    const results = await Promise.all(
      res.items.map(async (room) => {
        try {
          const points = await getMachineRoomPoints(room.id, { __silent: true })
          return [
            room.id,
            {
              rack_count: points.racks.length,
              device_count: points.racks.reduce((sum, r) => sum + r.devices.length, 0),
            },
          ] as const
        } catch {
          return null
        }
      }),
    )
    for (const item of results) {
      if (item) counts.value[item[0]] = item[1]
    }
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// 新建 / 编辑
// ============================================================
const dialogVisible = ref(false)
const editingRoom = ref<MachineRoom | null>(null)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  code: '',
  address: '',
  note: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入机房名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入机房编码', trigger: 'blur' }],
}

function openCreate() {
  editingRoom.value = null
  form.name = ''
  form.code = ''
  form.address = ''
  form.note = ''
  dialogVisible.value = true
}

function openEdit(row: MachineRoom) {
  editingRoom.value = row
  form.name = row.name
  form.code = row.code
  form.address = row.address ?? ''
  form.note = row.note ?? ''
  dialogVisible.value = true
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
    const payload = {
      name: form.name.trim(),
      code: form.code.trim(),
      address: form.address.trim() || null,
      note: form.note.trim() || null,
    }
    if (editingRoom.value) {
      await updateMachineRoom(editingRoom.value.id, payload)
      ElMessage.success('机房已更新')
    } else {
      await createMachineRoom(payload)
      ElMessage.success('机房已创建')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已统一处理
  } finally {
    submitting.value = false
  }
}

// ============================================================
// 删除（409 时展示后端 detail）
// ============================================================
async function handleDelete(row: MachineRoom) {
  if (!(await confirmDelete(`确定删除机房「${row.name}」？删除后其下机架一并删除。`))) return
  try {
    await deleteMachineRoom(row.id, { __silent: true })
    ElMessage.success('机房已删除')
    fetchList()
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

function goDetail(row: MachineRoom) {
  router.push({ name: 'MachineRoomDetail', params: { id: row.id } })
}

onMounted(fetchList)
</script>

<template>
  <div class="page-container">
    <div class="page-panel">
      <div class="card-header">
        <span class="title">
          <el-icon><OfficeBuilding /></el-icon>
          机房管理
        </span>
        <div class="header-actions">
          <el-button type="primary" @click="openCreate">+ 新建机房</el-button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="toolbar">
        <el-input
          v-model="searchText"
          placeholder="按名称 / 编码搜索"
          clearable
          style="width: 260px"
          @input="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button :icon="Refresh" :disabled="loading" @click="fetchList">刷新</el-button>
        <el-button :icon="RefreshLeft" :disabled="!searchText" @click="clearFilters">重置</el-button>
      </div>

      <!-- 表格 -->
      <el-table v-loading="loading" :data="list" stripe style="width: 100%">
        <template #empty>
          <div class="table-empty">
            <el-empty :description="searchText ? '未找到匹配机房' : '暂无机房'" :image-size="72" />
          </div>
        </template>
        <el-table-column label="名称" min-width="180">
          <template #default="{ row }">
            <span class="col-name-link" @click="goDetail(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.address">{{ row.address }}</span>
            <span v-else class="col-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="机架数" width="100" align="center">
          <template #default="{ row }">
            {{ counts[row.id]?.rack_count ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column label="设备数" width="100" align="center">
          <template #default="{ row }">
            {{ counts[row.id]?.device_count ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.note">{{ row.note }}</span>
            <span v-else class="col-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" link type="primary" @click="goDetail(row)">点位图</el-button>
              <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建 / 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingRoom ? '编辑机房' : '新建机房'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="机房名称" prop="name">
          <el-input v-model="form.name" placeholder="如 上海一号机房" maxlength="128" />
        </el-form-item>
        <el-form-item label="机房编码" prop="code">
          <el-input v-model="form.code" placeholder="如 SH-01" maxlength="64" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" placeholder="如 上海市浦东新区" maxlength="256" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="3"
            placeholder="可选"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingRoom ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
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
</style>
