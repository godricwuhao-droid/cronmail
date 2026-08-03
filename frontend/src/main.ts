/**
 * 应用入口
 *
 * - 注册 Element Plus 全局组件与图标
 * - 注册 Vue Router
 * - 引入基础样式
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/global.css'

const app = createApp(App)

// 注册全部 Element Plus 图标为全局组件
for (const [name, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, comp as any)
}

app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.mount('#app')
