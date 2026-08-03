import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false },
      // TODO: 后端认证上线后恢复登录页，暂时重定向到首页
      redirect: '/dashboard',
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '数据报表' }},
        { path: 'rental-dashboard', name: 'RentalDashboard', component: () => import('@/views/RentalDashboard.vue'), meta: { title: '租赁概览' }},
        { path: 'customers', name: 'Customers', component: () => import('@/views/customers/CustomerList.vue'), meta: { title: '客户管理' }},
        { path: 'customers/:id', name: 'CustomerDetail', component: () => import('@/views/customers/CustomerDetail.vue'), meta: { title: '客户详情' }},
        { path: 'customers/:id/contacts', name: 'Contacts', component: () => import('@/views/customers/ContactList.vue'), meta: { title: '联系人管理' }},
        { path: 'contracts', name: 'Contracts', redirect: '/contracts/compute' },
        { path: 'contracts/compute', name: 'ComputeContracts', component: () => import('@/views/contracts/compute/ComputeContractList.vue'), meta: { title: '算力租赁合同' }},
        { path: 'contracts/compute/:id', name: 'ComputeContractDetail', component: () => import('@/views/contracts/compute/ComputeContractDetail.vue'), meta: { title: '合同详情' }},
        { path: 'contracts/compute/create', name: 'ComputeContractCreate', component: () => import('@/views/contracts/compute/ComputeContractForm.vue'), meta: { title: '新建合同' }},
        { path: 'contracts/compute/:id/edit', name: 'ComputeContractEdit', component: () => import('@/views/contracts/compute/ComputeContractForm.vue'), meta: { title: '编辑合同' }},
        { path: 'contracts/compute/:id/attachments', name: 'ComputeContractAttachments', component: () => import('@/views/contracts/compute/ComputeContractAttachments.vue'), meta: { title: '合同附件' }},
        { path: 'contracts/satellite', name: 'SatelliteContracts', component: () => import('@/views/contracts/satellite/SatelliteContractList.vue'), meta: { title: '卫星数据合同' }},
        { path: 'contracts/satellite/:id', name: 'SatelliteContractDetail', component: () => import('@/views/contracts/satellite/SatelliteContractDetail.vue'), meta: { title: '合同详情' }},
        { path: 'contracts/satellite/create', name: 'SatelliteContractCreate', component: () => import('@/views/contracts/satellite/SatelliteContractForm.vue'), meta: { title: '新建合同' }},
        { path: 'contracts/satellite/:id/edit', name: 'SatelliteContractEdit', component: () => import('@/views/contracts/satellite/SatelliteContractForm.vue'), meta: { title: '编辑合同' }},
        { path: 'contracts/satellite/:id/attachments', name: 'SatelliteContractAttachments', component: () => import('@/views/contracts/satellite/SatelliteContractAttachments.vue'), meta: { title: '合同附件' }},
        { path: 'contracts/service', name: 'ServiceContracts', component: () => import('@/views/contracts/service/ServiceContractList.vue'), meta: { title: '算力服务合同' }},
        { path: 'contracts/service/:id', name: 'ServiceContractDetail', component: () => import('@/views/contracts/service/ServiceContractDetail.vue'), meta: { title: '合同详情' }},
        { path: 'contracts/service/create', name: 'ServiceContractCreate', component: () => import('@/views/contracts/service/ServiceContractForm.vue'), meta: { title: '新建合同' }},
        { path: 'contracts/service/:id/edit', name: 'ServiceContractEdit', component: () => import('@/views/contracts/service/ServiceContractForm.vue'), meta: { title: '编辑合同' }},
        { path: 'contracts/service/:id/attachments', name: 'ServiceContractAttachments', component: () => import('@/views/contracts/service/ServiceContractAttachments.vue'), meta: { title: '合同附件' }},
        { path: 'projects/fengyun', name: 'FengyunProjects', component: () => import('@/views/projects/fengyun/FengyunProjectList.vue'), meta: { title: '蜂云时代项目' }},
        { path: 'projects/fengyun/:id', name: 'FengyunProjectDetail', component: () => import('@/views/projects/fengyun/FengyunProjectDetail.vue'), meta: { title: '项目详情' }},
        { path: 'projects/fengyun/create', name: 'FengyunProjectCreate', component: () => import('@/views/projects/fengyun/FengyunProjectForm.vue'), meta: { title: '新建项目' }},
        { path: 'projects/fengyun/:id/edit', name: 'FengyunProjectEdit', component: () => import('@/views/projects/fengyun/FengyunProjectForm.vue'), meta: { title: '编辑项目' }},
        { path: 'projects/fengyun/:id/attachments', name: 'FengyunProjectAttachments', component: () => import('@/views/projects/fengyun/FengyunProjectAttachments.vue'), meta: { title: '项目附件' }},
        { path: 'projects/tianshu', name: 'TianshuProjects', component: () => import('@/views/projects/tianshu/TianshuProjectList.vue'), meta: { title: '安徽天枢项目' }},
        { path: 'projects/tianshu/:id', name: 'TianshuProjectDetail', component: () => import('@/views/projects/tianshu/TianshuProjectDetail.vue'), meta: { title: '项目详情' }},
        { path: 'projects/tianshu/create', name: 'TianshuProjectCreate', component: () => import('@/views/projects/tianshu/TianshuProjectForm.vue'), meta: { title: '新建项目' }},
        { path: 'projects/tianshu/:id/edit', name: 'TianshuProjectEdit', component: () => import('@/views/projects/tianshu/TianshuProjectForm.vue'), meta: { title: '编辑项目' }},
        { path: 'projects/tianshu/:id/attachments', name: 'TianshuProjectAttachments', component: () => import('@/views/projects/tianshu/TianshuProjectAttachments.vue'), meta: { title: '项目附件' }},
        { path: 'projects/qianxing', name: 'QianxingProjects', component: () => import('@/views/projects/qianxing/QianxingProjectList.vue'), meta: { title: '千星控股项目' }},
        { path: 'projects/qianxing/:id', name: 'QianxingProjectDetail', component: () => import('@/views/projects/qianxing/QianxingProjectDetail.vue'), meta: { title: '项目详情' }},
        { path: 'projects/qianxing/create', name: 'QianxingProjectCreate', component: () => import('@/views/projects/qianxing/QianxingProjectForm.vue'), meta: { title: '新建项目' }},
        { path: 'projects/qianxing/:id/edit', name: 'QianxingProjectEdit', component: () => import('@/views/projects/qianxing/QianxingProjectForm.vue'), meta: { title: '编辑项目' }},
        { path: 'projects/qianxing/:id/attachments', name: 'QianxingProjectAttachments', component: () => import('@/views/projects/qianxing/QianxingProjectAttachments.vue'), meta: { title: '项目附件' }},
        { path: 'devices', name: 'Devices', component: () => import('@/views/devices/DeviceList.vue'), meta: { title: '设备管理' }},
        { path: 'devices/:id', name: 'DeviceDetail', component: () => import('@/views/devices/DeviceDetail.vue'), meta: { title: '设备详情' }},
        { path: 'devices/create', name: 'DeviceCreate', component: () => import('@/views/devices/DeviceForm.vue'), meta: { title: '创建设备' }},
        { path: 'devices/:id/edit', name: 'DeviceEdit', component: () => import('@/views/devices/DeviceForm.vue'), meta: { title: '编辑设备' }},
        { path: 'templates', name: 'Templates', component: () => import('@/views/templates/TemplateList.vue'), meta: { title: '邮件模板' }},
        { path: 'templates/create', name: 'TemplateCreate', component: () => import('@/views/templates/TemplateForm.vue'), meta: { title: '创建模板' }},
        { path: 'templates/:id/edit', name: 'TemplateEdit', component: () => import('@/views/templates/TemplateForm.vue'), meta: { title: '编辑模板' }},
        { path: 'logs', name: 'Logs', component: () => import('@/views/logs/LogList.vue'), meta: { title: '发送日志' }},
        { path: 'system/smtp', name: 'SystemSmtp', component: () => import('@/views/system/SmtpConfig.vue'), meta: { title: 'SMTP配置' }},
        { path: 'system/colleagues', name: 'SystemColleagues', component: () => import('@/views/system/ColleagueList.vue'), meta: { title: '同事管理' }},
        { path: 'system/config', name: 'SystemConfig', component: () => import('@/views/system/SystemConfig.vue'), meta: { title: '系统配置' }},
        { path: 'system/dingtalk', name: 'SystemDingtalk', component: () => import('@/views/system/DingtalkConfig.vue'), meta: { title: '钉钉通知' }},
        { path: 'system/attachments', name: 'SystemAttachments', component: () => import('@/views/system/AttachmentCategories.vue'), meta: { title: '附件分类' }},
      ],
    },
  ],
})

// TODO: 后端认证上线后恢复登录守卫
// router.beforeEach((to, _from, next) => {
//   const token = localStorage.getItem('token')
//   if (to.path !== '/login' && !token) {
//     next('/login')
//   } else if (to.path === '/login' && token) {
//     next('/')
//   } else {
//     next()
//   }
// })

export default router