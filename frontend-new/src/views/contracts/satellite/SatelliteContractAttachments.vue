<template>
  <div class="page-container">
    <div class="page-header">
      <div class="flex items-center gap-base">
        <el-button @click="router.push(`/contracts/satellite/${contractId}`)"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>返回合同</el-button>
        <h1 class="page-title">合同附件</h1>
      </div>
    </div>
    <div class="page-toolbar"><div class="page-toolbar-right">
      <el-button type="primary" @click="uploadRef?.click()"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>上传附件</el-button>
      <input ref="uploadRef" type="file" style="display:none" @change="handleUpload" />
    </div></div>
    <div class="content-card" style="padding: 0;">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column prop="file_size" label="大小" width="100"><template #default="{ row }">{{ formatSize(row.file_size) }}</template></el-table-column>
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="created_at" label="上传时间" width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDownload(row)">下载</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && list.length === 0" class="empty-state">
        <svg class="empty-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M15 7h2a4 4 0 0 1 0 8h-2"/><path d="M3 8v8a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V8a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3z"/></svg>
        <div class="empty-state__title">暂无附件</div>
        <div class="empty-state__description">上传合同相关附件文件</div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAttachments, uploadAttachment, deleteAttachment } from '@/api/attachment'
const route = useRoute()
const router = useRouter()
const contractId = route.params.id as string
const list = ref<any[]>([])
const loading = ref(false)
const uploadRef = ref<HTMLInputElement>()
onMounted(() => loadData())
const loadData = async () => { loading.value = true; try { const res: any = await getAttachments({ related_type: 'satellite_contract', related_id: contractId, page_size: 100 }); list.value = res.items || res } catch { /* ignore */ } finally { loading.value = false } }
const handleUpload = async (e: Event) => { const file = (e.target as HTMLInputElement).files?.[0]; if (!file) return; const formData = new FormData(); formData.append('file', file); formData.append('related_type', 'satellite_contract'); formData.append('related_id', contractId); try { await uploadAttachment(formData); ElMessage.success('上传成功'); loadData() } catch { /* ignore */ }; if (uploadRef.value) uploadRef.value.value = '' }
const handleDownload = (row: any) => { window.open(row.file_url, '_blank') }
const handleDelete = async (id: string) => { try { await deleteAttachment(id); ElMessage.success('删除成功'); loadData() } catch { /* ignore */ } }
const formatSize = (bytes?: number) => { if (!bytes) return '-'; if (bytes < 1024) return bytes + ' B'; if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'; return (bytes / 1048576).toFixed(1) + ' MB' }
</script>
<style scoped lang="scss">.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center; }
.empty-state__icon { width: 64px; height: 64px; margin-bottom: 16px; color: var(--color-text-placeholder); }
.empty-state__title { font-size: var(--font-size-md); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); margin-bottom: 4px; }
.empty-state__description { font-size: var(--font-size-base); color: var(--color-text-tertiary); }</style>