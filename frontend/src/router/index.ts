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
    redirect: '/data-report/overview',
    children: [
      // ---------- 数据报表 ----------
      {
        path: 'data-report',
        redirect: '/data-report/overview',
        children: [
          {
            path: 'overview',
            name: 'DataOverview',
            component: () => import('@/views/data-report/overview.vue'),
            meta: { title: '运营概览', icon: 'DataAnalysis', parent: 'data-report' },
          },
          {
            path: 'rental-overview',
            name: 'RentalOverview',
            component: () => import('@/views/data-report/rental-overview.vue'),
            meta: { title: '租赁概览', icon: 'TrendCharts', parent: 'data-report' },
          },
        ],
      },

      // ---------- 兼容旧路由 /dashboard 重定向 ----------
      {
        path: 'dashboard',
        redirect: '/data-report/rental-overview',
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

      // ---------- 合同管理（重定向到算力租赁） ----------
      {
        path: 'contracts',
        redirect: '/contracts/compute-leasing',
      },

      // ---------- 算力租赁合同（原 /contracts 内容，路径迁移至此） ----------
      {
        path: 'contracts/compute-leasing',
        name: 'ContractList',
        component: () => import('@/views/contracts/index.vue'),
        meta: { title: '算力租赁', icon: 'Monitor', parent: 'contracts' },
      },
      {
        path: 'contracts/compute-leasing/create',
        name: 'ContractCreate',
        component: () => import('@/views/contracts/create.vue'),
        meta: { title: '新建合同', icon: 'Monitor', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/compute-leasing/:id',
        name: 'ContractDetail',
        component: () => import('@/views/contracts/detail.vue'),
        meta: { title: '合同详情', icon: 'Monitor', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/compute-leasing/:id/edit',
        name: 'ContractEdit',
        component: () => import('@/views/contracts/create.vue'),
        meta: { title: '编辑合同', icon: 'Monitor', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/compute-leasing/:id/attachments',
        name: 'ComputeLeasingAttachments',
        component: () => import('@/views/attachments/AttachmentsPage.vue'),
        meta: { title: '附件管理', icon: 'Monitor', hidden: true, parent: 'contracts' },
      },

      // ---------- 卫星数据合同 ----------
      {
        path: 'contracts/satellite-data',
        name: 'SatelliteContractList',
        component: () => import('@/views/satellite-contracts/index.vue'),
        meta: { title: '卫星数据', icon: 'DataAnalysis', parent: 'contracts' },
      },
      {
        path: 'contracts/satellite-data/create',
        name: 'SatelliteContractCreate',
        component: () => import('@/views/satellite-contracts/form.vue'),
        meta: { title: '新建卫星数据合同', icon: 'DataAnalysis', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/satellite-data/:id',
        name: 'SatelliteContractDetail',
        component: () => import('@/views/satellite-contracts/detail.vue'),
        meta: { title: '卫星数据合同详情', icon: 'DataAnalysis', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/satellite-data/:id/edit',
        name: 'SatelliteContractEdit',
        component: () => import('@/views/satellite-contracts/form.vue'),
        meta: { title: '编辑卫星数据合同', icon: 'DataAnalysis', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/satellite-data/:id/attachments',
        name: 'SatelliteDataAttachments',
        component: () => import('@/views/attachments/AttachmentsPage.vue'),
        meta: { title: '附件管理', icon: 'DataAnalysis', hidden: true, parent: 'contracts' },
      },

      // ---------- 算力服务合同 ----------
      {
        path: 'contracts/compute-service',
        name: 'ServiceContractList',
        component: () => import('@/views/service-contracts/index.vue'),
        meta: { title: '算力服务', icon: 'Cpu', parent: 'contracts' },
      },
      {
        path: 'contracts/compute-service/create',
        name: 'ServiceContractCreate',
        component: () => import('@/views/service-contracts/form.vue'),
        meta: { title: '新建算力服务合同', icon: 'Cpu', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/compute-service/:id',
        name: 'ServiceContractDetail',
        component: () => import('@/views/service-contracts/detail.vue'),
        meta: { title: '算力服务合同详情', icon: 'Cpu', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/compute-service/:id/edit',
        name: 'ServiceContractEdit',
        component: () => import('@/views/service-contracts/form.vue'),
        meta: { title: '编辑算力服务合同', icon: 'Cpu', hidden: true, parent: 'contracts' },
      },
      {
        path: 'contracts/compute-service/:id/attachments',
        name: 'ComputeServiceAttachments',
        component: () => import('@/views/attachments/AttachmentsPage.vue'),
        meta: { title: '附件管理', icon: 'Cpu', hidden: true, parent: 'contracts' },
      },

      // ---------- 项目管理 ----------
      {
        path: 'projects',
        redirect: '/projects/fengyun',
        children: [
          {
            path: ':company',
            name: 'ProjectList',
            component: () => import('@/views/projects/index.vue'),
            meta: { title: '项目管理', icon: 'FolderOpened', parent: 'projects' },
          },
          {
            path: ':company/create',
            name: 'ProjectCreate',
            component: () => import('@/views/projects/form.vue'),
            meta: { title: '新建合同', icon: 'FolderOpened', hidden: true, parent: 'projects' },
          },
          {
            path: ':company/:id',
            name: 'ProjectDetail',
            component: () => import('@/views/projects/detail.vue'),
            meta: { title: '合同详情', icon: 'FolderOpened', hidden: true, parent: 'projects' },
          },
          {
            path: ':company/:id/edit',
            name: 'ProjectEdit',
            component: () => import('@/views/projects/form.vue'),
            meta: { title: '编辑合同', icon: 'FolderOpened', hidden: true, parent: 'projects' },
          },
          {
            path: ':company/:id/attachments',
            name: 'ProjectAttachments',
            component: () => import('@/views/projects/AttachmentsPage.vue'),
            meta: { title: '附件管理', icon: 'FolderOpened', hidden: true, parent: 'projects' },
          },
        ],
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
          {
            path: 'attachment-categories',
            name: 'AttachmentCategories',
            component: () => import('@/views/system/attachment-categories.vue'),
            meta: { title: '附件分类管理', icon: 'FolderOpened' },
          },
        ],
      },
    ],
  },

  // 404 兜底
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/data-report/overview',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
