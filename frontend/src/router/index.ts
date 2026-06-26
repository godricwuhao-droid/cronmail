/**
 * 路由配置
 *
 * 所有业务页面都挂在 MainLayout 下，children 中各路由通过侧边栏菜单访问。
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      // ---------- 仪表盘 ----------
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' },
      },

      // ---------- 客户管理 ----------
      {
        path: 'customers',
        name: 'CustomerList',
        component: () => import('@/views/customers/index.vue'),
        meta: { title: '客户管理', icon: 'User' },
      },
      {
        // 客户下的联系人管理
        path: 'customers/:id/contacts',
        name: 'ContactList',
        component: () => import('@/views/customers/contacts.vue'),
        meta: { title: '联系人管理', icon: 'User', hidden: true },
      },

      // ---------- 合同管理（位于客户/租赁之间：合同归属客户，租赁归属合同） ----------
      {
        path: 'contracts',
        name: 'ContractList',
        component: () => import('@/views/contracts/index.vue'),
        meta: { title: '合同管理', icon: 'Notebook' },
      },
      {
        path: 'contracts/create',
        name: 'ContractCreate',
        component: () => import('@/views/contracts/create.vue'),
        meta: { title: '新建合同', icon: 'Notebook', hidden: true },
      },
      {
        path: 'contracts/:id',
        name: 'ContractDetail',
        component: () => import('@/views/contracts/detail.vue'),
        meta: { title: '合同详情', icon: 'Notebook', hidden: true },
      },
      {
        path: 'contracts/:id/edit',
        name: 'ContractEdit',
        component: () => import('@/views/contracts/create.vue'),
        meta: { title: '编辑合同', icon: 'Notebook', hidden: true },
      },

      // ---------- 设备管理 ----------
      {
        path: 'rentals',
        name: 'RentalList',
        component: () => import('@/views/rentals/index.vue'),
        meta: { title: '设备管理', icon: 'Document' },
      },
      {
        path: 'rentals/create',
        name: 'RentalCreate',
        component: () => import('@/views/rentals/create.vue'),
        meta: { title: '创建设备', icon: 'Document', hidden: true },
      },
      {
        path: 'rentals/:id',
        name: 'RentalDetail',
        component: () => import('@/views/rentals/detail.vue'),
        meta: { title: '设备详情', icon: 'Document', hidden: true },
      },
      {
        path: 'rentals/:id/edit',
        name: 'RentalEdit',
        component: () => import('@/views/rentals/create.vue'),
        meta: { title: '编辑设备', icon: 'Document', hidden: true },
      },

      // ---------- 邮件模板 ----------
      {
        path: 'templates',
        name: 'TemplateList',
        component: () => import('@/views/templates/index.vue'),
        meta: { title: '邮件模板', icon: 'Message' },
      },
      {
        path: 'templates/create',
        name: 'TemplateCreate',
        component: () => import('@/views/templates/edit.vue'),
        meta: { title: '新建模板', icon: 'Message', hidden: true },
      },
      {
        path: 'templates/:id/edit',
        name: 'TemplateEdit',
        component: () => import('@/views/templates/edit.vue'),
        meta: { title: '编辑模板', icon: 'Message', hidden: true },
      },

      // ---------- 发送日志 ----------
      {
        path: 'logs',
        name: 'EmailLogList',
        component: () => import('@/views/logs/index.vue'),
        meta: { title: '发送日志', icon: 'Tickets' },
      },

      // ---------- 系统配置（菜单含子菜单） ----------
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/system/index.vue'),
        meta: { title: '系统配置', icon: 'Setting' },
        redirect: '/system/smtp',
        children: [
          {
            path: 'smtp',
            name: 'SmtpConfig',
            component: () => import('@/views/system/smtp.vue'),
            meta: { title: 'SMTP配置', icon: 'Promotion' },
          },
          {
            path: 'colleagues',
            name: 'ColleagueList',
            component: () => import('@/views/system/colleagues.vue'),
            meta: { title: '内部同事管理', icon: 'UserFilled' },
          },
          {
            path: 'config',
            name: 'SystemConfig',
            component: () => import('@/views/system/config.vue'),
            meta: { title: '系统配置', icon: 'Tools' },
          },
          {
            path: 'dingtalk',
            name: 'DingTalkConfig',
            component: () => import('@/views/system/dingtalk.vue'),
            meta: { title: '钉钉通知', icon: 'ChatDotRound' },
          },
        ],
      },
    ],
  },

  // 404 兜底
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
