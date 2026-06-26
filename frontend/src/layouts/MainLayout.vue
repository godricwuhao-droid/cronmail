<template>
  <el-container style="height: 100vh">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" style="background: var(--sidebar-bg); transition: width 0.2s; overflow: hidden;">
      <div class="sidebar-logo">
        <span v-if="!isCollapse" class="logo-text">CronMail</span>
        <span v-else class="logo-icon">
          <el-icon :size="22"><Promotion /></el-icon>
        </span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="isCollapse"
        background-color="#001529"
        text-color="rgba(255,255,255,0.65)"
        active-text-color="#fff"
        style="border-right: none;"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title><span>运营概览</span></template>
        </el-menu-item>
        <el-menu-item index="/customers">
          <el-icon><UserFilled /></el-icon>
          <template #title><span>客户管理</span></template>
        </el-menu-item>
        <el-menu-item index="/contracts">
          <el-icon><Notebook /></el-icon>
          <template #title><span>合同管理</span></template>
        </el-menu-item>
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
import { useRoute } from 'vue-router'
import {
  Odometer,
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
} from '@element-plus/icons-vue'

const route = useRoute()
const isCollapse = ref(false)

const activeMenu = computed(() => {
  // /system/* 路由时高亮 /system 父菜单
  if (route.path.startsWith('/system')) return 'system'
  return route.path
})

/** 面包屑：父级标题（可点击跳转到列表页） */
const parentTitle = computed(() => {
  if (route.path.startsWith('/customers/') && route.path.endsWith('contacts')) return '客户管理'
  if (route.path.startsWith('/contracts/create')) return '合同管理'
  if (route.path.startsWith('/contracts/') && route.path.endsWith('edit')) return '合同管理'
  if (route.path.startsWith('/contracts/')) return '合同管理'
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
  if (route.path.startsWith('/customers/')) return '/customers'
  if (route.path.startsWith('/contracts/')) return '/contracts'
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
    '/dashboard': '运营概览',
    '/customers': '客户管理',
    '/contracts': '合同管理',
    '/rentals': '设备管理',
    '/templates': '模板管理',
    '/logs': '发送日志',
    '/system/smtp': 'SMTP 配置',
    '/system/colleagues': '内部同事',
    '/system/config': '系统配置',
    '/system/dingtalk': '钉钉通知',
  }
  if (route.path.startsWith('/customers/') && route.path.endsWith('contacts')) return '联系人管理'
  if (route.path.startsWith('/contracts/create')) return '创建合同'
  if (route.path.startsWith('/contracts/') && route.path.endsWith('edit')) return '编辑合同'
  if (route.path.startsWith('/contracts/')) return '合同详情'
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
