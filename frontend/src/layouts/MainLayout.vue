<template>
  <el-container style="height: 100vh">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" style="background: linear-gradient(180deg, #0d1b3e 0%, #1a3270 40%, #1a5cb0 100%); transition: width 0.2s; overflow-y: auto; overflow-x: hidden;">
      <div class="sidebar-logo">
        <span v-if="!isCollapse" class="logo-text">资产运营管理平台</span>
        <span v-else class="logo-icon">
          <el-icon :size="22"><Promotion /></el-icon>
        </span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="isCollapse"
        background-color="transparent"
        text-color="rgba(255,255,255,0.72)"
        active-text-color="#ffffff"
        style="border-right: none;"
      >
        <el-sub-menu index="data-report">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>数据报表</span>
          </template>
          <el-menu-item index="/data-report/overview">运营概览</el-menu-item>
          <el-menu-item index="/data-report/rental-overview">租赁概览</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/customers">
          <el-icon><UserFilled /></el-icon>
          <template #title><span>客户管理</span></template>
        </el-menu-item>
        <el-sub-menu index="contracts">
          <template #title>
            <el-icon><Notebook /></el-icon>
            <span>合同管理</span>
          </template>
          <el-menu-item index="/contracts/compute-leasing">
            <el-icon><Monitor /></el-icon>
            <span>算力租赁</span>
          </el-menu-item>
          <el-menu-item index="/contracts/satellite-data">
            <el-icon><DataAnalysis /></el-icon>
            <span>卫星数据</span>
          </el-menu-item>
          <el-menu-item index="/contracts/compute-service">
            <el-icon><Cpu /></el-icon>
            <span>算力服务</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="projects">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>项目管理</span>
          </template>
          <el-menu-item index="/projects/fengyun">蜂云时代</el-menu-item>
          <el-menu-item index="/projects/tianshu">安徽天枢</el-menu-item>
          <el-menu-item index="/projects/qianxing">千星控股</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/rentals">
          <el-icon><Document /></el-icon>
          <template #title><span>设备管理</span></template>
        </el-menu-item>
        <el-menu-item index="/templates">
          <el-icon><Message /></el-icon>
          <template #title><span>邮件模板</span></template>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Tickets /></el-icon>
          <template #title><span>发送日志</span></template>
        </el-menu-item>
        <el-sub-menu index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统配置</span>
          </template>
          <el-menu-item index="/system/smtp">SMTP 配置</el-menu-item>
          <el-menu-item index="/system/dingtalk">钉钉通知</el-menu-item>
          <el-menu-item index="/system/colleagues">内部同事</el-menu-item>
          <el-menu-item index="/system/config">系统配置</el-menu-item>
          <el-menu-item index="/system/attachment-categories">附件分类管理</el-menu-item>
          <el-menu-item index="/system/attachment-categories-project" @click.prevent="goProjectAttachmentCategories">项目管理附件配置</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶栏 -->
      <el-header style="background: var(--header-bg); display: flex; align-items: center; justify-content: space-between; padding: 0 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); z-index: 10;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <el-button @click="isCollapse = !isCollapse" :icon="isCollapse ? Expand : Fold" text style="font-size: 18px;" />
          <div style="font-size: 13px; color: var(--text-secondary);">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="breadcrumbHomePath">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="parentTitle" :to="parentPath">{{ parentTitle }}</el-breadcrumb-item>
              <el-breadcrumb-item v-if="pageTitle">{{ pageTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
        <div>
          <el-tag type="success" size="small" effect="light">
            <el-icon style="vertical-align: -2px;"><CircleCheckFilled /></el-icon>
            <span style="margin-left: 4px;">系统运行中</span>
          </el-tag>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main style="background: var(--bg-color); padding: 24px;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UserFilled,
  Document,
  Message,
  Tickets,
  Notebook,
  Setting,
  Promotion,
  CircleCheckFilled,
  Fold,
  Expand,
  Monitor,
  DataAnalysis,
  Cpu,
  FolderOpened,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)

function goProjectAttachmentCategories() {
  router.push({ path: '/system/attachment-categories', query: { contract_type: 'project' } })
}

const activeMenu = computed(() => {
  // /system/* 路由时高亮 /system 父菜单
  if (route.path.startsWith('/system')) return 'system'
  // /contracts/* 路由时高亮 contracts 父菜单
  if (route.path.startsWith('/contracts')) return 'contracts'
  // /projects/* 路由时高亮 projects 父菜单
  if (route.path.startsWith('/projects')) return 'projects'
  // /data-report/* 路由时高亮 data-report 父菜单
  if (route.path.startsWith('/data-report')) return 'data-report'
  return route.path
})

/** 面包屑：父级标题（可点击跳转到列表页） */
const parentTitle = computed(() => {
  if (route.path.startsWith('/data-report/')) return '数据报表'
  if (route.path.startsWith('/customers/') && route.path.endsWith('contacts')) return '客户管理'
  if (route.path.startsWith('/contracts/compute-leasing')) return '算力租赁合同'
  if (route.path.startsWith('/contracts/satellite-data')) return '卫星数据合同'
  if (route.path.startsWith('/contracts/compute-service')) return '算力服务合同'
  if (route.path.startsWith('/contracts')) return '合同管理'
  if (route.path.startsWith('/projects')) return '项目管理'
  if (route.path.startsWith('/rentals/create')) return '设备管理'
  if (route.path.startsWith('/rentals/') && route.path.endsWith('edit')) return '设备管理'
  if (route.path.startsWith('/rentals/')) return '设备管理'
  if (route.path.startsWith('/templates/create')) return '模板管理'
  if (route.path.startsWith('/templates/') && route.path.endsWith('edit')) return '模板管理'
  if (route.path.startsWith('/system/')) return '系统配置'
  return ''
})

/** 面包屑：父级跳转路径 */
const parentPath = computed(() => {
  if (route.path.startsWith('/data-report/')) return '/data-report/overview'
  if (route.path.startsWith('/customers/')) return '/customers'
  if (route.path.startsWith('/contracts/compute-leasing')) return '/contracts/compute-leasing'
  if (route.path.startsWith('/contracts/satellite-data')) return '/contracts/satellite-data'
  if (route.path.startsWith('/contracts/compute-service')) return '/contracts/compute-service'
  if (route.path.startsWith('/contracts')) return '/contracts/compute-leasing'
  if (route.path.startsWith('/projects')) {
    // 返回对应公司的列表页
    const company = route.params.company || 'fengyun'
    return `/projects/${company}`
  }
  if (route.path.startsWith('/rentals/')) return '/rentals'
  if (route.path.startsWith('/templates/')) return '/templates'
  if (route.path.startsWith('/system/')) return '/system/smtp'
  return '/'
})

/** 面包屑「首页」链接：当存在 parentPath 时，首页指向列表页而非仪表盘 */
const breadcrumbHomePath = computed(() => {
  if (parentPath.value) return parentPath.value
  return { path: '/' }
})

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    '/data-report/overview': '运营概览',
    '/data-report/rental-overview': '租赁概览',
    '/customers': '客户管理',
    '/contracts/compute-leasing': '算力租赁合同',
    '/contracts/satellite-data': '卫星数据',
    '/contracts/compute-service': '算力服务',
    '/rentals': '设备管理',
    '/templates': '模板管理',
    '/logs': '发送日志',
    '/system/smtp': 'SMTP 配置',
    '/system/colleagues': '内部同事',
    '/system/config': '系统配置',
    '/system/dingtalk': '钉钉通知',
    '/system/attachment-categories': '附件分类管理',
  }
  if (route.path.startsWith('/customers/') && route.path.endsWith('contacts')) return '联系人管理'
  if (route.path.startsWith('/contracts/compute-leasing/create')) return '新建算力租赁合同'
  if (route.path.startsWith('/contracts/compute-leasing/') && route.path.endsWith('edit')) return '编辑算力租赁合同'
  if (route.path.startsWith('/contracts/compute-leasing/') && route.path.endsWith('attachments')) return '附件管理'
  if (route.path.startsWith('/contracts/compute-leasing/')) return '算力租赁合同详情'
  if (route.path.startsWith('/contracts/satellite-data/create')) return '新建卫星数据合同'
  if (route.path.startsWith('/contracts/satellite-data/') && route.path.endsWith('edit')) return '编辑卫星数据合同'
  if (route.path.startsWith('/contracts/satellite-data/') && route.path.endsWith('attachments')) return '附件管理'
  if (route.path.startsWith('/contracts/satellite-data/')) return '卫星数据合同详情'
  if (route.path.startsWith('/contracts/compute-service/create')) return '新建算力服务合同'
  if (route.path.startsWith('/contracts/compute-service/') && route.path.endsWith('edit')) return '编辑算力服务合同'
  if (route.path.startsWith('/contracts/compute-service/') && route.path.endsWith('attachments')) return '附件管理'
  if (route.path.startsWith('/contracts/compute-service/')) return '算力服务合同详情'
  if (route.path.startsWith('/projects/:company/create') || route.path.match(/\/projects\/[^/]+\/create/)) return '新建合同'
  if (route.path.match(/\/projects\/[^/]+\/[^/]+\/edit/)) return '编辑合同'
  if (route.path.match(/\/projects\/[^/]+\/[^/]+\/attachments/)) return '附件管理'
  if (route.path.match(/\/projects\/[^/]+\/[^/]+/)) return '合同详情'
  // /projects/fengyun 等列表页
  const projectCompanyMatch = route.path.match(/^\/projects\/(fengyun|tianshu|qianxing)$/)
  if (projectCompanyMatch) {
    const names: Record<string, string> = { fengyun: '蜂云时代', tianshu: '安徽天枢', qianxing: '千星控股' }
    return names[projectCompanyMatch[1]] || projectCompanyMatch[1]
  }
  if (route.path.startsWith('/rentals/create')) return '创建设备'
  if (route.path.startsWith('/rentals/') && route.path.endsWith('edit')) return '编辑设备'
  if (route.path.startsWith('/rentals/')) return '设备详情'
  if (route.path.startsWith('/templates/create')) return '新建模板'
  if (route.path.startsWith('/templates/')) return '模板编辑'
  return map[route.path] || ''
})
</script>

<style scoped>
.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  letter-spacing: 0.5px;
}
.logo-text {
  font-size: 18px;
  font-weight: 700;
}
.logo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
</style>
