<template>
  <div class="layout">
    <!-- 全宽顶栏：左品牌，右状态 -->
    <header class="topbar">
      <div class="topbar-brand">
        <el-icon class="topbar-logo" :size="22"><Promotion /></el-icon>
        <span class="topbar-brand-name">资产运营管理平台</span>
      </div>
      <div class="topbar-acts">
        <span class="topbar-status">
          <el-icon :size="14"><CircleCheckFilled /></el-icon>
          系统运行中
        </span>
      </div>
    </header>

    <div class="layout-body">
      <!-- 侧边栏（无 Logo） -->
      <aside class="sidebar">
        <el-menu
          :key="defaultOpeneds.join(',') || 'root'"
          :default-active="activeMenu"
          :default-openeds="defaultOpeneds"
          router
          background-color="transparent"
          text-color="#3F5573"
          active-text-color="#2563EB"
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
            <el-menu-item index="/contracts/compute-leasing">算力租赁</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/rentals">
            <el-icon><Document /></el-icon>
            <template #title><span>设备管理</span></template>
          </el-menu-item>
          <el-menu-item index="/machine-rooms">
            <el-icon><OfficeBuilding /></el-icon>
            <template #title><span>机房管理</span></template>
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
          </el-sub-menu>
        </el-menu>
      </aside>

      <!-- 内容区 -->
      <main class="main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  UserFilled,
  Document,
  Message,
  Tickets,
  Notebook,
  Setting,
  Promotion,
  CircleCheckFilled,
  DataAnalysis,
  OfficeBuilding,
} from '@element-plus/icons-vue'

const route = useRoute()

/** 侧边栏菜单项 index 列表（用于路由高亮匹配） */
const menuIndexes = [
  '/data-report/overview',
  '/data-report/rental-overview',
  '/customers',
  '/contracts/compute-leasing',
  '/rentals',
  '/machine-rooms',
  '/templates',
  '/logs',
  '/system/smtp',
  '/system/dingtalk',
  '/system/colleagues',
  '/system/config',
  '/system/attachment-categories',
]

const activeMenu = computed(() => {
  const path = route.path
  if (menuIndexes.includes(path)) return path
  const matched = menuIndexes
    .filter((idx) => path === idx || path.startsWith(idx + '/'))
    .sort((a, b) => b.length - a.length)[0]
  return matched || path
})

/** 当前路由所在分组自动展开 */
const defaultOpeneds = computed(() => {
  const path = route.path
  const openeds: string[] = []
  if (path.startsWith('/data-report')) openeds.push('data-report')
  if (path.startsWith('/contracts')) openeds.push('contracts')
  if (path.startsWith('/system')) openeds.push('system')
  return openeds
})
</script>

<style scoped>
.layout {
  height: 100vh;
  overflow: hidden;
  background: var(--bg-color);
}

.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 200;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: linear-gradient(180deg, #eef4fb 0%, #f5f8fc 45%, #eef3f9 100%);
  border-bottom: none;
  box-shadow: none;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.topbar-logo {
  color: var(--primary-color);
  flex-shrink: 0;
}

.topbar-brand-name {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--primary-color);
  line-height: 1.2;
}

.topbar-acts {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: auto;
  min-height: unset;
  padding: 4px 9px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.2;
  color: #2563EB;
  background: #D3E0FB;
  border: none;
  white-space: nowrap;
}

.topbar-status .el-icon {
  color: #2563EB;
  font-size: 14px;
}

.layout-body {
  display: flex;
  height: 100vh;
  padding-top: 56px;
  box-sizing: border-box;
}

.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: linear-gradient(180deg, #eef4fb 0%, #f5f8fc 45%, #eef3f9 100%);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0 16px;
}

.main {
  flex: 1;
  min-width: 0;
  overflow: auto;
  background: var(--bg-color);
  padding: 24px;
  box-sizing: border-box;
}
</style>
