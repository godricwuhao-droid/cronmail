# CronMail Frontend

CronMail 邮件平台前端，基于 Vue 3 + TypeScript + Vite + Element Plus。

## 技术栈

- **框架**：Vue 3 (`<script setup>`)
- **语言**：TypeScript (strict)
- **构建工具**：Vite 5
- **UI 库**：Element Plus
- **图标**：`@element-plus/icons-vue`
- **路由**：Vue Router 4
- **HTTP**：Axios（`baseURL: /api`，开发期由 Vite 代理到 `http://localhost:8000`）

## 目录结构

```
src/
├── api/              # API 请求层
│   ├── index.ts      # Axios 实例与拦截器
│   └── modules/      # 按业务模块拆分的 API（待补充）
├── router/           # 路由配置
├── layouts/          # 布局组件
│   └── MainLayout.vue
├── views/            # 页面组件
│   ├── dashboard/    # 仪表盘
│   ├── customers/    # 客户管理
│   ├── rentals/      # 租赁管理
│   ├── templates/    # 邮件模板
│   ├── logs/         # 发送日志
│   └── system/       # 系统配置（SMTP / 同事）
├── styles/           # 全局样式
├── App.vue
└── main.ts
```

## 本地开发

```bash
# 安装依赖
npm install

# 启动 dev server（默认 http://localhost:5173）
npm run dev

# 类型检查 + 生产构建
npm run build
```

> 注意：dev server 会把 `/api/*` 请求代理到 `http://localhost:8000`，需要后端服务同时运行。

## 路由表

| Path | 名称 | 说明 |
| --- | --- | --- |
| `/` | - | 重定向到 `/dashboard` |
| `/dashboard` | Dashboard | 仪表盘 |
| `/customers` | CustomerList | 客户管理 |
| `/rentals` | RentalList | 租赁管理 |
| `/rentals/create` | RentalCreate | 新建租赁 |
| `/rentals/:id` | RentalDetail | 租赁详情 |
| `/rentals/:id/edit` | RentalEdit | 编辑租赁 |
| `/templates` | TemplateList | 邮件模板 |
| `/templates/create` | TemplateCreate | 新建模板 |
| `/templates/:id/edit` | TemplateEdit | 编辑模板 |
| `/logs` | EmailLogList | 发送日志 |
| `/system/smtp` | SmtpConfig | SMTP 配置 |
| `/system/colleagues` | ColleagueList | 内部同事管理 |
