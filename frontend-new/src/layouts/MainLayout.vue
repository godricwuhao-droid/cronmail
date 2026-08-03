<template>
  <div class="main-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar__logo">
        <svg class="sidebar__logo-icon" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="32" height="32" rx="8" fill="white"/>
          <path d="M8 10L16 16L24 10" stroke="#1677FF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <rect x="7" y="10" width="18" height="12" rx="2" stroke="#1677FF" stroke-width="2"/>
        </svg>
        <span v-show="!isCollapsed" class="sidebar__logo-text">CronMail</span>
      </div>

      <nav class="sidebar__nav">
        <!-- 数据报表 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            数据报表
          </div>
          <router-link to="/dashboard" class="sidebar__item" :class="{ active: route.path === '/dashboard' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="13" rx="1"/><rect width="7" height="5" x="14" y="17" rx="1"/><rect width="7" height="13" x="14" y="3" rx="1"/><rect width="7" height="9" x="3" y="3" rx="1"/></svg>
            <span v-show="!isCollapsed">运营概览</span>
          </router-link>
          <router-link to="/rental-dashboard" class="sidebar__item" :class="{ active: route.path === '/rental-dashboard' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3"/><path d="m15 9 6-6"/></svg>
            <span v-show="!isCollapsed">租赁概览</span>
          </router-link>
        </div>

        <!-- 客户管理 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            客户管理
          </div>
          <router-link to="/customers" class="sidebar__item" :class="{ active: route.path.startsWith('/customers') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/></svg>
            <span v-show="!isCollapsed">客户列表</span>
          </router-link>
        </div>

        <!-- 合同管理 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
            合同管理
          </div>
          <router-link to="/contracts/compute" class="sidebar__item" :class="{ active: route.path.startsWith('/contracts/compute') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/></svg>
            <span v-show="!isCollapsed">算力租赁</span>
          </router-link>
          <router-link to="/contracts/satellite" class="sidebar__item" :class="{ active: route.path.startsWith('/contracts/satellite') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 7l9 9-5 5-9-9 5-5z"/><path d="M8 12l-1 3 3 1 3-3-3-1z"/><path d="M15 5l3-3"/><path d="M2 17l4 4"/><path d="M2 7l5 5"/></svg>
            <span v-show="!isCollapsed">卫星数据</span>
          </router-link>
          <router-link to="/contracts/service" class="sidebar__item" :class="{ active: route.path.startsWith('/contracts/service') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>
            <span v-show="!isCollapsed">算力服务</span>
          </router-link>
        </div>

        <!-- 项目管理 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c1.5 0 2.5 1 2 3-1.5 7-7 10-10 10-3.5 0-6.5-3-8-10-.5-2 .5-3 2-3h14z"/><path d="M12 2a4 4 0 0 1 0 8 4 4 0 0 1 0-8z"/></svg>
            项目管理
          </div>
          <router-link to="/projects/fengyun" class="sidebar__item" :class="{ active: route.path.startsWith('/projects/fengyun') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            <span v-show="!isCollapsed">蜂云时代</span>
          </router-link>
          <router-link to="/projects/tianshu" class="sidebar__item" :class="{ active: route.path.startsWith('/projects/tianshu') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            <span v-show="!isCollapsed">安徽天枢</span>
          </router-link>
          <router-link to="/projects/qianxing" class="sidebar__item" :class="{ active: route.path.startsWith('/projects/qianxing') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            <span v-show="!isCollapsed">千星控股</span>
          </router-link>
        </div>

        <!-- 设备管理 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>
            设备管理
          </div>
          <router-link to="/devices" class="sidebar__item" :class="{ active: route.path.startsWith('/devices') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>
            <span v-show="!isCollapsed">设备列表</span>
          </router-link>
        </div>

        <!-- 邮件模板 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
            邮件管理
          </div>
          <router-link to="/templates" class="sidebar__item" :class="{ active: route.path.startsWith('/templates') }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>
            <span v-show="!isCollapsed">邮件模板</span>
          </router-link>
          <router-link to="/logs" class="sidebar__item" :class="{ active: route.path === '/logs' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span v-show="!isCollapsed">发送日志</span>
          </router-link>
        </div>

        <!-- 系统配置 -->
        <div class="sidebar__group">
          <div class="sidebar__group-title" v-show="!isCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
            系统配置
          </div>
          <router-link to="/system/smtp" class="sidebar__item" :class="{ active: route.path === '/system/smtp' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
            <span v-show="!isCollapsed">SMTP配置</span>
          </router-link>
          <router-link to="/system/colleagues" class="sidebar__item" :class="{ active: route.path === '/system/colleagues' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            <span v-show="!isCollapsed">同事管理</span>
          </router-link>
          <router-link to="/system/config" class="sidebar__item" :class="{ active: route.path === '/system/config' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span v-show="!isCollapsed">系统配置</span>
          </router-link>
          <router-link to="/system/dingtalk" class="sidebar__item" :class="{ active: route.path === '/system/dingtalk' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.1 3.39A10 10 0 0 1 20.6 11a10 10 0 0 1-2.1 5.8L9.1 3.39Z"/><path d="m14.8 19.6.9 2.4 2.5-.9"/><path d="M2.5 11a10 10 0 0 1 5.2-8.6L2.5 11Z"/></svg>
            <span v-show="!isCollapsed">钉钉通知</span>
          </router-link>
          <router-link to="/system/attachments" class="sidebar__item" :class="{ active: route.path === '/system/attachments' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 7h2a4 4 0 0 1 0 8h-2"/><path d="M3 8v8a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V8a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3z"/></svg>
            <span v-show="!isCollapsed">附件分类</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar__toggle" @click="isCollapsed = !isCollapsed">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ rotated: isCollapsed }"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Header -->
      <header class="header">
        <div class="header__left">
          <h1 class="header__title">{{ pageTitle }}</h1>
        </div>
        <div class="header__right">
          <div class="header__user" @click="showUserMenu = !showUserMenu" @click.away="showUserMenu = false">
            <div class="avatar" style="background: var(--color-primary);">
              {{ (authStore.user?.name || authStore.user?.username || 'U')[0].toUpperCase() }}
            </div>
            <div class="header__user-info">
              <div class="header__user-name">{{ authStore.user?.name || authStore.user?.username || '用户' }}</div>
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
          </div>
          <div v-if="showUserMenu" class="user-menu">
            <div class="user-menu__item" @click="handleLogout">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
              退出登录
            </div>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="main-content__body">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isCollapsed = ref(false)
const showUserMenu = ref(false)

const pageTitle = computed(() => {
  return (route.meta.title as string) || 'CronMail'
})

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped lang="scss">
.main-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-page);
}

/* Sidebar */
.sidebar {
  width: 240px;
  background: var(--color-text-primary);
  color: rgba(255, 255, 255, 0.7);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
  transition: width var(--transition-base);
  overflow: hidden;

  &.collapsed {
    width: 64px;

    .sidebar__group-title {
      display: none;
    }
  }

  &__logo {
    height: 60px;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: 0 var(--spacing-xl);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0;

    &-icon {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
    }

    &-text {
      font-size: var(--font-size-lg);
      font-weight: var(--font-weight-bold);
      color: white;
      white-space: nowrap;
    }
  }

  &__nav {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-base) 0;
  }

  &__group {
    margin-bottom: var(--spacing-sm);
  }

  &__group-title {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-xl);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  &__item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-xl);
    margin: 1px var(--spacing-sm);
    border-radius: var(--radius-md);
    color: rgba(255, 255, 255, 0.7);
    text-decoration: none;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    transition: all var(--transition-fast);
    white-space: nowrap;

    svg {
      flex-shrink: 0;
      width: 18px;
      height: 18px;
    }

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: white;
    }

    &.active {
      background: var(--color-primary);
      color: white;
    }
  }

  &__toggle {
    position: absolute;
    top: 16px;
    right: -12px;
    width: 24px;
    height: 24px;
    background: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--color-text-tertiary);
    transition: all var(--transition-fast);
    z-index: 10;

    &:hover {
      color: var(--color-primary);
      border-color: var(--color-primary);
    }

    .rotated {
      transform: rotate(180deg);
    }
  }
}

/* Main Content */
.main-content {
  flex: 1;
  margin-left: 240px;
  transition: margin-left var(--transition-base);
  display: flex;
  flex-direction: column;
  min-height: 100vh;

  .sidebar.collapsed ~ & {
    margin-left: 64px;
  }
}

/* Header */
.header {
  height: 60px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-2xl);
  position: sticky;
  top: 0;
  z-index: 50;

  &__title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
  }

  &__right {
    display: flex;
    align-items: center;
    gap: var(--spacing-base);
    position: relative;
  }

  &__user {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
    padding: var(--spacing-xs) var(--spacing-xs);
    border-radius: var(--radius-md);
    transition: background var(--transition-fast);

    &:hover {
      background: var(--color-bg-hover);
    }
  }

  &__user-info {
    text-align: right;
  }

  &__user-name {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
  }
}

.user-menu {
  position: absolute;
  top: calc(100% + var(--spacing-sm));
  right: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 160px;
  overflow: hidden;
  z-index: 200;

  &__item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--color-bg-hover);
      color: var(--color-danger);
    }
  }
}

.main-content__body {
  flex: 1;
  padding: var(--spacing-xl) var(--spacing-2xl);
}

/* Responsive sidebar margin */
.sidebar.collapsed ~ .main-content {
  margin-left: 64px;
}
</style>