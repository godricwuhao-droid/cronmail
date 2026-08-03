<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">千星控股项目</h1></div>
    <div class="page-toolbar">
      <div class="page-toolbar-left"><el-input v-model="keyword" placeholder="搜索项目名称" clearable style="width: 280px" @change="loadData" /></div>
      <div class="page-toolbar-right"><el-button type="primary" @click="router.push('/projects/qianxing/create')"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>新建项目</el-button></div>
    </div>
    <div class="content-card" style="padding: 0;">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="项目名称" min-width="200" />
        <el-table-column prop="customer_name" label="客户" width="140" />
        <el-table-column prop="status" label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '进行中' : '已完成' }}</el-tag></template></el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/projects/qianxing/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="router.push(`/projects/qianxing/${row.id}/edit`)">编辑</el-button>
            <el-button link type="primary" @click="router.push(`/projects/qianxing/${row.id}/attachments`)">附件</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="loadData" @current-change="loadData" /></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProjectContracts, deleteProjectContract } from '@/api/project'
const router = useRouter()
const list = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
onMounted(() => loadData())
const loadData = async () => { loading.value = true; try { const res: any = await getProjectContracts('qianxing', { page: page.value, page_size: pageSize.value, keyword: keyword.value }); list.value = res.items || res; total.value = res.total || 0 } catch { /* ignore */ } finally { loading.value = false } }
const handleDelete = async (id: string) => { try { await deleteProjectContract('qianxing', id); ElMessage.success('删除成功'); loadData() } catch { /* ignore */ } }
</script>
<style scoped lang="scss">.pagination-wrapper { padding: 16px 20px; display: flex; justify-content: flex-end; border-top: 1px solid var(--color-border-light); }</style>