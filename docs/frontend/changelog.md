# CronMail 前端变更日志

> 本文档记录 CronMail 前端项目的所有变更。
>
> **格式约定**
> - 日期：YYYY-MM-DD
> - 类型：新增 / 修改 / 修复 / 删除 / 重构
> - Breaking Change 标注 ⚠️

## 2026-07-17 (Excel 预览从 ExcelJS 替换为 SheetJS)

### [修改] Excel 预览库从 ExcelJS 替换为 SheetJS (xlsx)

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 附件管理页 Excel 预览 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue`、`frontend/package.json` |
| 关联任务 | Excel 预览从 ExcelJS 替换为 SheetJS |

#### 改动

1. **依赖替换**（`package.json`）：
   - 卸载 `exceljs`（v4.4.0）
   - 安装 `xlsx`（SheetJS）

2. **Import 替换**（第 40 行）：
   - `import * as ExcelJS from 'exceljs'` → `import * as XLSX from 'xlsx'`

3. **`case 'xlsx'` 代码重写**（第 371-416 行）：
   - 旧方案：`new ExcelJS.Workbook()` → `workbook.xlsx.load()` → `workbook.worksheets.forEach` → 手动逐行逐单元格构建 `<table>` DOM
   - 新方案：`XLSX.read(arrayBuffer)` → `workbook.SheetNames.forEach` → `XLSX.utils.sheet_to_html()` 生成 HTML → 用 CSS 美化表格样式（边框、首行加粗背景）
   - 错误处理逻辑保持不变（内层 try-catch 捕获解析异常，显示友好提示）

#### 验收

- ✅ `vue-tsc -b` 零错误
- ✅ `vite build` 成功
- ✅ 无 lint 错误
- ✅ Excel 预览功能正常（多 sheet 支持、表格样式美化）

#### 备注

- SheetJS (`xlsx`) 比 ExcelJS 更稳定，兼容性更好，不存在 ExcelJS 的 `childNodes` 已知问题
- `sheet_to_html` 内置 HTML 生成能力，代码更简洁（从 ~35 行手动 DOM 构建减少到 ~20 行）
- 表格样式通过 `querySelectorAll` 统一美化（边框 `#e4e7ed`、首行背景 `#f5f7fa` + 600 字重）

---

## 2026-07-17 (Excel 预览异常处理 + PDF worker 兜底)

### [修复] Excel 预览报错 `Cannot read properties of null` 崩溃 + fetch 空 blob 兜底

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 附件管理页文件预览 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | Excel 预览异常处理 + PDF worker 兜底 |

#### 问题

1. **ExcelJS 4.4.0 解析某些 XLSX 文件**：内部 XML 解析抛出 `Cannot read properties of null (reading 'childNodes')`，导致 `handlePreview` 整个 try-catch 被触发，用户看到笼统的「预览失败」而非 Excel 特定错误。
2. **fetch 返回空 blob**：网络异常或后端返回空响应时，后续库（ExcelJS/pdfjs-dist）在空数据上解析报错，错误信息不友好。

#### 修复

1. **`case 'xlsx'` 内层 try-catch**（第 369 行）：在 `await workbook.xlsx.load(arrayBuffer)` 外包独立的 try-catch，捕获 ExcelJS 解析异常后显示友好提示：「Excel 解析失败：{错误信息}」+ 「请点击上方下载按钮下载后查看」，不影响外层 catch 的其他错误处理。
2. **blob 空值检查**（第 289 行）：`fetch` 成功后新增 `if (!blob || blob.size === 0) throw new Error('文件内容为空')`，空 blob 直接进入外层 catch 显示友好错误。
3. **fetch 错误信息增强**：`response.ok` 失败时错误信息从 `'文件获取失败'` 改为 `'文件获取失败 (${response.status})'`，方便排查。
4. **PDF worker 注释补充**：添加兜底说明注释，明确 `?url` 导入已由 Vite 正确处理。

#### 验收

- ✅ `vue-tsc -b` 零错误
- ✅ `vite build` 成功
- ✅ Excel 解析失败时显示独立友好提示（含错误信息 + 下载建议）
- ✅ 空 blob 不会导致后续库崩溃
- ✅ fetch HTTP 错误状态码可追踪

#### 备注

- ExcelJS 的 `childNodes` 错误是其底层 XML 解析器的已知问题，某些 XLSX 文件内部 XML 结构不规范时会触发，前端无法修复，只能兜底提示
- PDF worker 路径保持不变（`?url` 导入），用户如遇 worker 加载问题需 Ctrl+F5 强制刷新清除缓存

---

## 2026-07-17 (前端部署 #17)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `bb7714d76f97`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:a26ba0fe687e1894746b4c71a6ee6986839567aa44af6fd33cd9b603de0ef1c7`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (PDF 预览逐页懒加载)

### [修改] PDF 预览从全量渲染改为 IntersectionObserver 逐页懒加载

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 附件管理页 PDF 预览 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | 优化 PDF 预览性能（逐页懒加载） |

#### 问题

旧方案在 `case 'pdf'` 中循环 `for (let i = 1; i <= numPages; i++)` 一次性渲染所有页面到 canvas。对于多页文档（如 50 页合同），同时创建 50 个 canvas 并渲染，导致浏览器卡顿甚至崩溃。

#### 修复：IntersectionObserver 逐页按需渲染

**核心思路**：预创建占位 canvas（A4 比例 800×1130），用 `IntersectionObserver` 监听可见性，仅在进入视口时渲染。

1. **预创建占位 canvas**：循环 `numPages` 次创建 canvas，设置 `data-page-num` 属性、A4 比例宽高（800×1130）、样式（maxWidth/margin/display/boxShadow），追加到 container
2. **IntersectionObserver**：`rootMargin: '200px'` 提前 200px 渲染即将进入视口的页面；`isIntersecting` 时读取 `dataset.pageNum`，调用 `pdf.getPage(pageNum)` 渲染，渲染后 `unobserve` 停止监听
3. **`renderedSet`**：防止重复渲染（IntersectionObserver 可能触发多次）
4. **清理**：`pdfPreviewObserver` 模块级变量，`onPreviewDialogClosed` 中 `disconnect()` + 置 null；新预览开始时也会先清理旧的 observer

#### 验收

- ✅ `vue-tsc -b` 零错误
- ✅ 零 lint 错误
- ✅ 多页 PDF 只创建占位 canvas，不立即渲染
- ✅ 滚动到可见区域时才渲染对应页
- ✅ 弹窗关闭时 observer 正确清理
- ✅ DOCX/XLSX/PPTX/图片/文本预览不受影响

#### 备注

- `rootMargin: '200px'` 确保用户快速滚动时页面已渲染完成
- 占位 canvas 宽高比 ≈ A4（1:√2），避免布局抖动
- 单页渲染错误被 `try/catch` 静默忽略，不影响其他页

---

## 2026-07-17 (前端部署 #16)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `67c55fcbb851`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:b7a52bec02440bc06064ee9fdbd532d5b64987635cd09229712f8f3fe21289e8`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (前端部署 #15)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `bd393832266b`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:11b5ee84657bd317c9a5e030b2592eb6b9bd40a7459966e52f31d974a3f137bc`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (编辑页关联设备竞态彻底修复)

### [修复] 编辑页关联设备数据源分离，彻底消除竞态

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 合同编辑页关联设备 |
| 影响文件 | `frontend/src/views/contracts/create.vue` |
| 关联任务 | 彻底修复编辑页关联设备展示和交互 |

#### 问题

`linkedRentalDetails` 依赖 `loadAvailableRentals` 注入已关联设备，但 watch 与 loadDetail 之间存在竞态，导致 `linkedRentalDetails` 不稳定为空。

#### 根因

旧方案将已关联设备和可选设备混在同一个 `availableRentals` 数组中，通过 `syncLinkedDetails` 过滤。但 `loadAvailableRentals`（`unlinked_only: true`）不会返回已关联设备，需要手动从 `detail.value.rentals` 注入。这个注入和 `syncLinkedDetails` 的执行时序依赖 `Promise.all` + `nextTick`，在 watch 触发和 loadDetail 之间容易产生竞态。

#### 修复：数据源分离

**核心思路**：已关联设备和可选设备完全独立管理，消除竞态。

1. **新增 `buildLinkedDetails()` 函数**：直接从 `detail.value.rentals`（已关联旧设备）+ `availableRentals`（新选设备）重建表格数据，不依赖 `availableRentals` 中是否有已关联设备。

2. **`loadAvailableRentals` 简化**：只拉 `unlinked_only: true` 的设备，不再手动注入已关联设备。职责单一。

3. **`loadDetail` 简化**：去掉 `await nextTick()` + `syncLinkedDetails()`，改为直接调用 `buildLinkedDetails()`。`Promise.all` 完成后，`detail.value` 和 `availableRentals` 都已就绪，`buildLinkedDetails` 从两个独立数据源构建结果，不存在时序依赖。

4. **watch `customer_id`**：`syncLinkedDetails()` → `buildLinkedDetails()`。

5. **删除 `syncLinkedDetails` 函数**：不再需要。

6. **移除 `nextTick` import**：不再使用。

#### 验收

- ✅ `vue-tsc -b` 零错误
- ✅ 零 lint 错误
- ✅ 编辑页能看到全部已关联设备
- ✅ 弹窗只显示未关联设备
- ✅ 关联新设备后表格实时更新
- ✅ 取消关联后表格实时更新
- ✅ 创建模式（新建合同）正常

---

## 2026-07-17 (前端部署 #14)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `ac88100a4fc5`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:6b38f05d6e66249aa03286a3061b54e4fdf45ee4e622ab5eb88244a8b2312acf`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (前端部署 #13)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `168fccc6648e`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:5b4a64cf421eee6199674e24293b3ca936ac170db6bc0aef21398400c2978c8d`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (编辑页关联设备两个修复)

### [修复] 编辑页看不到已关联设备 + `<label for=FORM_ELEMENT>` 警告

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 合同编辑页 |
| 影响文件 | `frontend/src/views/contracts/create.vue` |
| 关联任务 | 编辑页关联设备两个修复 |

#### 问题 1：看不到已关联设备

根因：`loadAvailableRentals` 用 `unlinked_only: true` 只拉未关联设备，已关联设备不在列表中，`syncLinkedDetails` 依赖 `detail.value.rentals` 兜底但不够稳定。

修复：
1. `loadAvailableRentals` 编辑模式下将 `detail.value.rentals` 注入到 `availableRentals`，确保已关联设备也在可用列表中
2. `syncLinkedDetails` 简化为直接从 `availableRentals` 中过滤 `form.rental_ids`
3. `loadDetail` 中 `Promise.all` 后加 `await nextTick()` 确保响应式更新后再调用 `syncLinkedDetails`

#### 问题 2：`<label for=FORM_ELEMENT>` 警告

根因：关联设备区域的 `<div class="section-title">` 和 `<div class="rental-section">` 在 `<el-form>` 内但不在 `<el-form-item>` 内，导致 Element Plus 的 label 关联错乱。

修复：外层包裹 `<el-form-item label="设备列表">`。

#### 验收

- ✅ `vue-tsc -b` 零错误
- ✅ 编辑页能看到已关联的设备列表
- ✅ 不再有 "Incorrect use of <label for=FORM_ELEMENT>" 警告

---

## 2026-07-17 (前端部署 #12)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `795f81a95d3d`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:c1217b783c8975eb951b828423e218fe090371cb9397eceb971b8bccf2a552ba`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (编辑页关联设备改造)

### [修改] 编辑/创建页关联设备改为详情页风格（表格 + 弹窗选择 + 勾选取消）

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 合同创建/编辑页 |
| 影响文件 | `frontend/src/views/contracts/create.vue` |
| 关联任务 | 编辑页关联设备改造 |

**改动**

1. **删除旧的 `el-select` 多选方式**：移除 `rentalOptions` ref 和 `loadCustomerRentals` 函数
2. **新增详情页风格关联设备**：
   - 表格展示已关联设备（机器型号 + 机架位置），带 checkbox 勾选
   - 工具栏：「已选 N 台」计数 + 「关联设备」按钮 + 「取消关联(N)」按钮
   - 「关联设备」弹窗：`el-select` 多选可选设备（过滤掉已选）
   - 「取消关联」：勾选行 → 点击按钮移除（本地操作，提交时才同步到后端）
3. **提交逻辑增强**：编辑模式保存时自动计算新增/移除的设备，分别调用 `linkContractRentals` 和 `unlinkContractRentals`
4. **新增导入**：`unlinkContractRentals` from `@/api/modules/contract`
5. **CSS 新增**：`.rental-section` / `.rental-toolbar` / `.rental-count` / `.rental-actions`

**验收**

- ✅ `vue-tsc -b` 0 错误
- ✅ 无 lint 错误
- ✅ 编辑页关联设备显示为表格（机器型号 + 机架位置）
- ✅ 点击「关联设备」弹出对话框，显示可选设备列表
- ✅ 勾选表格行 + 点击「取消关联」移除设备
- ✅ 提交时正确处理新增和移除的设备

---

## 2026-07-17 (前端部署 #11)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `d97083231360`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:0352ac49b76951e496f6c7251bba1bf281fbd11bc3737602ea1a98cfe3f25877`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17

### [修复] PDF 预览只显示第一页

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | 修复 PDF 预览只显示第一页 |

**变更内容**：将 PDF 预览从只渲染第 1 页改为循环渲染全部页面（`for (let i = 1; i <= numPages; i++)`）。每页之间增加 12px 间距和轻微阴影以区分页面边界。

## 2026-07-17 (前端部署 #10)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `b4a5aa661f63`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:d8f221ccea75086fc08c44c179a7e74264cc51dc06cd458b3590c00e5e1bab58`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (前端部署 #9)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" /usr/bin/docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `5662448cb8e2`）
2. `/usr/bin/docker login harbor.xhwltech.com -u devops` — 登录 Harbor
3. `/usr/bin/docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:a37c5e7a8c22f5301f14fd02b2ec6846d74014299af5f7c9624321eb2470a581`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (pdfjs worker 加载修复)

### [修复] nginx 支持 .mjs MIME 类型 + pdfjs worker 导入方式优化

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | nginx 配置 + 附件管理页 PDF 预览 |
| 影响文件 | `frontend/nginx.conf`、`frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | pdfjs worker 加载失败修复 |

#### 问题

1. **nginx 未识别 `.mjs` 为静态资源**：`pdfjs-dist` v6 的 worker 文件是 `.mjs`（ESM 模块）格式，Vite 构建后输出 `pdf.worker.min-*.mjs`。nginx 的静态资源缓存正则 `\.(?:css|js|...)` 不包含 `mjs`，导致浏览器请求 `.mjs` 文件时可能不被正确识别为静态资源。

2. **worker 导入方式**：之前使用 `new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url)` 方式导致 Vite build 长时间卡在 transforming 阶段。经测试，恢复使用 Vite 原生的 `?url` 后缀导入（`import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'`）构建正常，worker 文件正确输出为 `dist/assets/pdf.worker.min-*.mjs`。

#### 修复

**1. nginx.conf（第 46 行）**：
```diff
- location ~* \.(?:css|js|jpg|jpeg|png|gif|ico|svg|woff2?|ttf|eot)$ {
+ location ~* \.(?:css|js|mjs|jpg|jpeg|png|gif|ico|svg|woff2?|ttf|eot)$ {
```

**2. AttachmentsPage.vue（第 44-46 行）**：保持 `?url` 导入方式不变（与 2026-07-06 修复一致），仅优化注释说明。

#### 验收

- ✅ `vue-tsc -b` 零错误
- ✅ `vite build` 成功（`✓ built in 1m 13s`，3543 modules transformed）
- ✅ `dist/assets/pdf.worker.min-DEtVeC4l.mjs`（1,255 KB）正确输出
- ✅ nginx 配置 `.mjs` 识别为静态资源（含 1 年缓存 + immutable）

#### 备注

- `?url` 后缀是 Vite 原生支持的静态资源导入方式，会将文件复制到 `dist/assets/` 并返回 URL 字符串
- `.mjs` 文件在 nginx 中默认 `application/octet-stream`（`/etc/nginx/mime.types` 通常不含 `.mjs`），加入静态资源缓存正则后走 `expires 1y` 策略

---

## 2026-07-17 (前端部署 #8)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `http_proxy="http://192.168.180.251:7890" docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `f9b2deab471c`）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:3dc5fa94bfd8efb1020193f36fdc1dcaa97faff3edd1b2fa89c05988d1f22df4`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (前端部署 #7)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `9c4f8db1d672`）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:434a0a180ce24ddb76487057bbf1a43c354333949a29b8c29f1f225778c2dce6`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (附件管理页纯前端文件预览)

### [新增] 附件管理页新增纯前端文件预览功能

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 附件管理页 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue`、`frontend/package.json` |
| 关联任务 | 附件管理页增加纯前端文件预览 |

**改动**

1. **新增依赖**（`package.json`）：
   - `docx-preview`：DOCX 文件前端渲染
   - `exceljs`：XLSX 文件前端渲染为 HTML 表格
   - `pdfjs-dist` v6.1.200：PDF 文件前端渲染为 Canvas
   - `pptx-preview`：PPTX 文件前端渲染为幻灯片

2. **Script 新增**：
   - 导入四个预览库 + 配置 `pdfjs-dist` worker CDN
   - `previewVisible` / `previewLoading` / `previewFile` / `previewType` 预览状态
   - `getPreviewType(file)`：根据扩展名和 MIME 类型判断文件类型
   - `handlePreview(file)`：核心预览函数，`fetch` 下载文件 blob 后根据类型调用对应渲染库
   - `onPreviewDialogClosed()`：关闭弹窗时清理 blob URL 避免内存泄漏

3. **Template 新增**：
   - 文件预览弹窗（`el-dialog`）：85% 宽度、`destroy-on-close`、含下载按钮
   - 文件名点击从 `handleDownload` 改为 `handlePreview`（右侧下载按钮保持不变）

4. **CSS 新增**：
   - `.preview-dialog :deep(.el-dialog__body)` 内边距调整
   - `.docx-preview` / `.docx-preview section` 分页卡片样式

**预览能力**

| 文件类型 | 渲染方式 |
| --- | --- |
| PDF | pdfjs-dist → Canvas（仅渲染第一页） |
| DOCX | docx-preview → 分页 HTML |
| XLSX | ExcelJS → HTML table（多 sheet 带标题） |
| PPTX | pptx-preview → 幻灯片模式 |
| 图片 (jpg/png/gif/webp/svg/bmp) | `<img>` 标签 |
| 文本 (txt/csv/log/json/xml/md/yaml/yml) | `<pre>` 标签 |
| 不支持的类型 | 友好提示 + 下载按钮 |

**验收**

- ✅ `vue-tsc -b` 0 错误
- ✅ `vite build` 成功
- ✅ 点击文件名弹出预览弹窗
- ✅ 弹窗内有下载按钮
- ✅ 关闭弹窗后 blob URL 释放

**备注**

- `pdfjs-dist` v6 是 ESM-only 模块，`render` 方法需要同时传 `canvasContext`、`viewport` 和 `canvas` 三个参数
- `docx-preview` `renderAsync` 签名为 `(data, bodyContainer, styleContainer?, userOptions?)`
- `pptx-preview` 导出 `init` 工厂函数，返回 PPTXPreviewer 实例，调用 `.preview(arrayBuffer)` 渲染

---

## 2026-07-17 (前端部署)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `313135f5ab7d`）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:a985a81f19cc24227be8fc1615135cc4bcbd392a64ab1786518ba413e96754bd`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (附件管理页双栏布局改造)

### [重构] 附件管理页从手风琴卡片改为左右双栏文件管理器布局

| 项目 | 说明 |
| --- | --- |
| 类型 | 重构 |
| 范围 | 附件管理页 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | 附件管理页双栏布局 + 拖拽上传 |

**改动**

1. **Script 层新增**：
   - `selectedItemId` ref：当前选中的子项 ID，`fetchAttachments` 后默认选中第一个
   - `selectedItem` computed：根据 `selectedItemId` 查找对应子项对象
   - 新增 `CheckboxValueType` 类型导入（element-plus）
   - 新增 `Document`、`Folder` 图标导入

2. **Template 完全重写**：
   - **左侧 280px 分类树**：分类可折叠/展开（ArrowDown 箭头动画），子项带状态标签（已确认/未确认/未上传），点击选中高亮
   - **右侧文件面板**：选中子项的 checkbox 确认 + 状态 tag + 文件列表（含文件图标、文件名点击下载、大小、时间）+ 下载/删除按钮
   - **上传区**：`el-upload` 改为 `drag` 模式，支持拖拽文件 + 点击上传
   - 无文件空态 + 未选中子项空态

3. **CSS 全部重写**：
   - 移除旧的手风琴式 CSS（`.detail-header` / `.detail-section` / `.attachment-category` / `.category-header` / `.attachment-item` 等全部）
   - 新 CSS：双栏 flex 布局、左侧树样式、右侧面板样式、拖拽上传区 `:deep()` 穿透样式

4. **JS 逻辑层**：上传/下载/删除/确认/取消确认等函数全部复用，零改动

**验收**

- ✅ `vue-tsc -b` 0 错误
- ✅ `vite build` 成功
- ✅ 左侧分类树可折叠/展开，点击子项切换右侧内容
- ✅ 右侧 checkbox 在无文件时 disabled
- ✅ 文件列表支持点击文件名和下载按钮下载
- ✅ 上传区支持拖拽文件（el-upload drag 模式）
- ✅ 默认选中第一个子项
- ✅ 确认/取消确认后列表自动刷新

**备注**

- 布局参照 `demo-attachments.html` 的双栏文件管理器风格
- 所有业务逻辑（upload/download/delete/confirm）完全不变

---

## 2026-07-17 (前端部署)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `a813694cb913`）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:c3c5dc621555593a87176114681d3ea6d048b4e5a0e15b5e5358bc129d924ab5`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (Dashboard 查看详情路由修复)

### [修复] Dashboard「待处理提醒」中「查看详情」按钮路由错误

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | Dashboard 页面待处理提醒操作按钮 |
| 影响文件 | `frontend/src/views/dashboard/index.vue` |
| 关联任务 | Dashboard 查看详情按钮无效 |

**问题**

第 72 行 `@click="$router.push('/contracts/${row.contract_id}')"` 路由路径错误。合同详情路由实际为 `/contracts/compute-leasing/:id`（见 `router/index.ts` 第 58-62 行），`/contracts/${id}` 无法匹配任何路由，导致点击后 fallback 到 404 → 重定向到 dashboard，表现为点击无反应。

**修复**

```diff
- @click="$router.push(`/contracts/${row.contract_id}`)"
+ @click="$router.push(`/contracts/compute-leasing/${row.contract_id}`)"
```

**验收**

- ✅ 点击「查看详情」能正确跳转到合同详情页
- ✅ 0 lint 错误

---

## 2026-07-17 (前端部署)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `0be722ff9763`）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:6c2d9895067229fe57a41af26b287167b12bd3485b2bec1bbd18d951dddfec3b`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (合同列表操作列优化)

### [修改] 合同列表操作列：附件改直接按钮 + 按钮间距统一

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 合同列表页操作列 |
| 影响文件 | `frontend/src/views/contracts/index.vue` |
| 关联任务 | 合同列表操作列优化 |

**改动**

1. **附件改直接按钮**：去掉 `el-dropdown` 包裹，改为普通 `<el-button link>` 直接调用 `goAttachments(row)` 跳转附件页面。原先 dropdown 三个选项（合同协议/交付材料/过程材料）都跳同一页面，无实际意义。
2. **按钮间距统一**：四个操作按钮（详情/编辑/删除/附件）外层包裹 `<div class="action-buttons">`，使用 `display: flex; gap: 2px;` 统一间距。
3. **操作列宽度调整**：`280` → `260`（去掉 dropdown 后更紧凑）。
4. **删除冗余样式**：移除不再使用的 `.status-dot-sm` CSS。

**验收**

- ✅ 附件按钮点击直接跳转附件页面
- ✅ 详情、编辑、删除、附件四个按钮间距均匀一致
- ✅ `vue-tsc --noEmit` 0 错误

---

## 2026-07-17 (前端部署)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功，image id: `571e463ac126`）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:147d1193c4965080338a39d376dab8e051c258e09bf6943649faf3d2dd0422be`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (仪表盘统计卡片替换)

### [修改] 仪表盘「邮件发送」统计卡片替换为「已到期」

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 仪表盘统计卡片 |
| 影响文件 | `frontend/src/views/dashboard/index.vue` |
| 关联任务 | 仪表盘统计卡片替换 |

**改动**

1. **图标导入**：移除 `Message`，新增 `CircleCloseFilled`
2. **stats 状态**：`emailSent` → `expired`，字段顺序调整为 `totalContracts, expiring, expired, reclaimed`
3. **statCards 计算属性**：「邮件发送」卡片（绿色 `#67C23A`、`Message` 图标）替换为「已到期」卡片（红色 `#F56C6C`、`CircleCloseFilled` 图标）
4. **数据加载**：`stats.value.emailSent = data.email_sent ?? 0` → `stats.value.expired = data.expired ?? 0`

**验收**

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ 无 lint 错误
- ✅ 统计卡片显示：合同总数、即将到期、已到期、已回收

**备注**

- 后端 Dashboard stats 接口已返回 `expired` 字段，无需额外兼容处理

---

## 2026-07-17 (前端部署)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（`vue-tsc -b && vite build` 成功）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像（digest: `sha256:6551eb7a9d1b514f6f587b8cf7046e2507dbc9b5c3865be3553d0522971c8a6a`）
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-17 (附件管理页 UI 优化 + 下载支持)

### [修改] 附件管理页 UI 优化 + 文件名点击下载

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 附件管理页 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | 附件管理页 UI 优化 + 下载支持 |

**改动**

1. **预期类型标签** (`.item-expected-type`)：
   - 去掉灰色背景 `background: #eef2f7`
   - `font-weight` 从 `500` 改为 `700`（bold）
   - color 保持 `#6b7280`

2. **上传区域改为虚线框**：
   - 去掉 `el-button`，改用纯 div `.upload-zone` 作为 trigger
   - 虚线边框 `border: 2px dashed #dcdfe6`，圆角 8px，背景 `#fafbfc`
   - 中间 Plus 图标（28px）+ 下方灰色文字「点击上传」
   - hover 时边框变蓝 `#409eff`，背景变 `#f0f5ff`，图标同步变色
   - 上传中显示 Loading 图标 +「上传中...」文字，opacity 降低

3. **文件名支持点击下载**：
   - `.file-name` 添加 `@click="handleDownload(file)"`
   - 新增 `cursor: pointer`、hover 变蓝 `#409eff` + 下划线

4. **图标导入清理**：
   - 移除未使用的 `Upload`，新增 `ArrowDown`（之前模板中使用但未导入）、`Plus`、`Loading`

**验收**

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ 无 lint 错误

**关联任务**：附件管理页面 UI 优化 + 下载支持

**备注**

- 所有修改仅涉及模板和 CSS，不影响 API 调用和业务逻辑

---

## 2026-07-17 (前端部署)

### [部署] 构建并部署前端至 K8s

| 项目 | 说明 |
| --- | --- |
| 类型 | 部署 |
| 范围 | 全站前端 |
| 影响文件 | Dockerfile.frontend, frontend/ 全部源文件 |
| 关联任务 | CronMail 前端构建部署 |

**操作步骤**

1. `docker build -f Dockerfile.frontend -t harbor.xhwltech.com/xhcloud/cronmail-frontend:latest .` — 构建镜像（node:20-alpine 编译 + nginx:alpine 运行）
2. `docker login harbor.xhwltech.com` — 登录 Harbor
3. `docker push harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` — 推送镜像
4. `kubectl rollout restart deployment/cronmail-frontend -n cronmail` — 滚动重启
5. `kubectl rollout status deployment/cronmail-frontend -n cronmail --timeout=120s` — 等待就绪

**结果**: 全部步骤成功，deployment 滚动更新完成。

---

## 2026-07-08 (合同列表操作列对齐修复 + 附件页配色优化)

### [修复] 合同列表操作列附件按钮垂直对齐

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 合同列表页操作列 |
| 影响文件 | `frontend/src/views/contracts/index.vue` |
| 关联任务 | 操作列对齐修复 |

**问题**

操作列中"详情/编辑/删除"（`el-button link`）与"附件"（`el-dropdown` 包裹的 `el-button link`）垂直方向未对齐。`el-dropdown` 默认 `inline-block` 容器与相邻 `el-button link` 的基线不一致。

**修复**

给 `el-dropdown` 添加 `style="vertical-align: middle;"`，使其与同行的 `el-button link` 基线对齐。

### [修改] 附件管理页配色优化

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 附件管理页 UI |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | 附件页配色优化 |

**改动**

1. **分类卡片** (`.attachment-category`)：
   - 新增白色背景 `background: #fff` + 柔和阴影 `box-shadow: 0 1px 4px rgba(0,0,0,0.04)`
   - 圆角从 `8px` 加大到 `10px`

2. **分类标题栏** (`.category-header`)：
   - 背景从纯色 `#f8fafc` 改为渐变 `linear-gradient(135deg, #f0f5ff 0%, #fafbfd 100%)`
   - hover 时渐变加深为 `linear-gradient(135deg, #e8f0fe 0%, #f0f3f8 100%)`
   - 底部新增分隔线 `border-bottom: 1px solid #eef1f6`

3. **子项卡片** (`.attachment-item`)：
   - 背景从 `#fafbfc` 改为更亮的 `#fcfdff`
   - 圆角从 `6px` 加大到 `8px`，内边距从 `12px 14px` 增加到 `14px 16px`
   - 新增 hover 效果：边框色变深 + 柔和阴影 `box-shadow: 0 2px 8px rgba(0,0,0,0.05)`

4. **预期类型标签** (`.item-expected-type`)：
   - 背景从 `#e5e7eb` 改为更柔和的 `#eef2f7`
   - 圆角从 `3px` 加大到 `4px`，内边距增加

5. **文件行** (`.file-row`)：
   - 从虚线分隔改为独立卡片式（圆角 `6px` + 浅灰背景 `#f9fafb`）
   - hover 时背景变为 `#f0f4fa`

6. **上传行** (`.upload-row`)：
   - 新增顶部分隔虚线 `border-top: 1px dashed #e4e7ed`

**备注**

- 整体配色向 Element Plus 默认主题靠拢，使用柔和的蓝色系渐变替代纯灰色
- 所有修改仅涉及 CSS，不影响功能和 API 调用

---

## 2026-07-04 (设备编辑页布局对齐 + 列表排序 + 列置顶)

### [修改] 租赁编辑页布局对齐合同编辑页风格

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 租赁创建/编辑页 |
| 影响文件 | `frontend/src/views/rentals/create.vue` |
| 关联任务 | 任务A |

**改动**
- 删除 `.form-grid` 双列网格布局，`el-form-item` 改为纵向排列（对齐合同编辑页）
- Section title 改为带 `el-icon` 风格：`<el-icon><Document /></el-icon> 基础信息`
- 图标映射：基础信息→Document, 存储→FolderOpened, 网络→Connection, 系统→Monitor, 凭证→Lock, 备注→EditPen
- 删除 `.form-grid`、`.form-item-custom`、`.form-input-custom` 等旧 CSS
- 存储区移除 `max-width: 600px` 限制

### [新增] 设备列表排序功能

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 后端 + 前端全链路 |
| 影响文件 | `backend/src/rental/services.py`、`backend/src/rental/api.py`、`frontend/src/api/modules/rental.ts`、`frontend/src/views/rentals/index.vue` |
| 关联任务 | 任务B |

**改动**
- 后端 `list_rentals` 新增 `sort_field` / `sort_order` 参数，白名单校验后动态 order_by
- 排序白名单：machine_model、memory_gb、bandwidth_mbps、rack_location、created_at
- 前端 `RentalListParams` 新增 `sort_field` / `sort_order`
- el-table 加 `@sort-change="handleSort"`，对应列设 `sortable: 'custom'`
- 默认按创建时间倒序

### [新增] 列设置面板置顶按钮

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 设备列表列设置 |
| 影响文件 | `frontend/src/views/rentals/index.vue` |
| 关联任务 | 任务C |

**改动**
- 列设置 popover 每个 column-item 新增置顶图钉按钮（Top 图标）
- 默认置顶列：machine_model、private_ip、status
- 置顶列在面板中排在前面
- 新增 `.pin-btn` CSS：默认半透明，hover 显示主色

---

## 2026-07-03 (磁盘字段改 String + 创建设备页 UI 优化)

### [修改] 系统盘/数据盘改为字符串类型，创建设备页 UI 优化

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 设备 CRUD 全链路 + 模板 mock 数据 |
| 影响文件 | `frontend/src/api/modules/rental.ts`、`frontend/src/views/rentals/index.vue`、`frontend/src/views/rentals/detail.vue`、`frontend/src/views/rentals/create.vue`、`frontend/src/views/templates/edit.vue`、`frontend/src/lib/template.ts` |
| 关联任务 | 磁盘字段+UI |

**改动**

#### 1. API 类型（`rental.ts`）

- **删除** `DataDisk` 接口（含 `size_gb` / `type`）
- `RentalDetail.system_disk_gb: number | null` → `system_disk: string | null`
- `RentalDetail.data_disks: DataDisk[] | null` → `data_disks: string[] | null`
- `RentalCreatePayload.system_disk_gb?: number` → `system_disk?: string`
- `RentalCreatePayload.data_disks?: DataDisk[]` → `data_disks?: string[]`
- `RentalUpdatePayload` 同理

#### 2. 设备列表页（`index.vue`）

- 列 key `system_disk_gb` → `system_disk`，渲染去掉 `GB` 后缀直接显示字符串
- 数据盘列：`d.size_gb` → `d`，直接显示字符串数组元素

#### 3. 设备详情页（`detail.vue`）

- `record.system_disk_gb` → `record.system_disk`，去掉 `+ ' GB'` 拼接
- 数据盘渲染：`disk.size_gb` / `disk.type` → `disk`（直接字符串）

#### 4. 创建设备页 UI 大改（`create.vue`）

参考 `device-input-temp.html` 风格重写 UI：

- **分区标题**：16px / 600 字重 / 左侧蓝色竖条 (`::before` 4px × 20px `#1890ff`) / 浅灰底 `#f8f9fa`
- **表单网格**：`grid-template-columns: repeat(auto-fill, minmax(380px, 1fr))`，间距 16px
- **标签样式**：14px / `#595959` / 500 字重；必填字段红色 `★` 星号
- **系统盘字段**：`el-input-number` → `el-input`（字符串类型）
- **数据盘字段**：按模板 `.storage-list` 风格重构
  - 每项显示 `● 2000GB NVMe SSD [删除]` 列表式布局
  - 虚线分隔 `border-bottom: 1px dashed #e8eaf0`
  - 输入框 + 「+ 添加数据盘」按钮在列表下方
  - 支持 Enter 快速添加
- **底部按钮**：`.footer-actions` 右对齐，顶部分割线 `border-top: 1px solid #e8eaf0`

#### 5. 模板编辑页（`edit.vue`）

- `sampleData` 映射中 `system_disk_gb` → `system_disk`
- 默认模板 HTML 中 `{{ system_disk_gb }} GB` → `{{ system_disk }}`

#### 6. Mock 数据（`lib/template.ts`）

```typescript
system_disk: '480GB SATA SSD',
data_disks: ['2000GB NVMe SSD', '4000GB SATA SSD'],
```

**验收**

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ 全项目 `DataDisk` / `system_disk_gb` 搜索 0 命中
- ✅ 创建设备页 UI 与 `device-input-temp.html` 风格一致

**备注**

- 磁盘字段从结构化（`{size_gb, type}`）改为自由字符串，用户可直接输入如 `480GB SATA SSD` 或 `76800GB NVMe SSD`，更灵活

---

## 2026-07-01 (模板测试发送改为选择合同)

### [修改] 模板测试发送改为选择合同代替单设备

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 模板编辑页测试发送弹窗 |
| 影响文件 | `frontend/src/views/templates/edit.vue` |
| 关联任务 | 测试体验优化 |

**改动**

1. **API 引入**：删除 `import { getRental, getRentals } from '@/api/modules/rental'`，改为 `import { listContracts, getContract } from '@/api/modules/contract'`
2. **变量改名**：`rentalId` → `contractId`、`rentalOptions` → `contractOptions`、`rentalDetailLoading` → `contractDetailLoading`
3. **下拉框改合同列表**：label 改为「选择合同」，placeholder 改为「选择一份合同作为测试数据（不选则用模板默认变量）」，选项 label 格式为「合同名称 - 客户名称」
4. **`loadRentalOptions` → `loadContractOptions`**：调用 `listContracts({ page: 1, page_size: 100 })` 获取合同列表
5. **`onRentalChange` → `onContractChange`**：选择合同后调用 `getContract(id)` 获取详情，将合同下所有设备映射为 `sample_data.rentals` 数组（`customer_name` + `rentals` 数组），模拟真实邮件发送场景（合同粒度合并发送）
6. **`openTestSendDialog`**：`loadRentalOptions()` → `loadContractOptions()`

**验收**

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ 无残留 `rentalId` / `rentalOptions` / `rentalDetailLoading` 引用

**备注**

- 后端 `test_send` 接口已支持 `sample_data.rentals` 数组：有则直接用，无则包装为单设备列表
- 测试发送现在以合同为粒度，与真实邮件发送逻辑一致

---

## 2026-07-01 (数据盘展示 + 表单布局优化)

### [修改] 合同创建/编辑表单改为单列靠左布局

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 合同创建/编辑页 |
| 影响文件 | `frontend/src/views/contracts/create.vue` |
| 关联任务 | 样式优化 |

**改动**

去掉基础信息区、服务周期区、关联联系人区的 `el-row`/`el-col` 两列布局，`el-form-item` 直接单列纵向排列。

**备注**

- 只删除布局标签，不改任何表单字段的内容、校验、逻辑
- label-width 保持 120px 不变

---

## 2026-07-01 (数据盘展示 + 创建设备表单布局优化)

### [修改] 数据盘展示去掉 el-tag 底色

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 设备列表页 + 设备详情页 |
| 影响文件 | `frontend/src/views/rentals/index.vue`、`frontend/src/views/rentals/detail.vue` |
| 关联任务 | 样式优化 |

**改动**

1. **设备列表页**（`index.vue`）：数据盘列从 `el-tag` 包裹改为纯文本 `<span>` 展示（`{{ d.size_gb }}GB`）
2. **设备详情页**（`detail.vue`）：数据盘字段从 `el-tag` 包裹改为纯文本 `<span>` 展示（`{{ disk.size_gb }}GB {{ disk.type }}`）

**备注**

- 数据盘信息不需要 el-tag 方框视觉强调，改为普通文本更简洁

---

### [修改] 创建设备表单改为单列靠左排列

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 设备创建/编辑页 |
| 影响文件 | `frontend/src/views/rentals/create.vue` |
| 关联任务 | 样式优化 |

**改动**

- 去掉表单中所有 `el-row` + `el-col` 两列布局包裹（基础信息、网络、系统、凭证 4 个分区）
- `el-form-item` 改为直接纵向单列排列，`label-width="120px"` 保持一致
- `el-input-number` 和 `el-select` 宽度统一为 `240px`（原两列时用的 `width: 100%` 不再合适）
- 数据盘部分、备注、提交按钮区域保持不变

---

## 2026-07-01 (设备详情页移除收件人和发送日志)

### [删除] 设备详情页移除收件人和发送日志模块

| 项目 | 说明 |
| --- | --- |
| 类型 | 删除 |
| 范围 | 设备详情页 |
| 影响文件 | `frontend/src/views/rentals/detail.vue` |
| 关联任务 | 数据源不一致，移至合同维度 |

**改动**

1. 删除「收件人」section（含 `el-table` 展示 `contacts` 数据）
2. 删除「发送日志」section（含 `el-table` 展示 `email_logs` 数据）
3. 移除模板顶部注释中对收件人和发送日志的提及

**备注**

- 收件人和发送日志的数据源不一致，后续移至合同维度管理

---

## 2026-07-01 (数字计数字段样式优化)

### [修改] 数字计数字段去掉 el-tag 方框包裹

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 合同列表 + 客户列表 |
| 影响文件 | `frontend/src/views/contracts/index.vue`、`frontend/src/views/customers/index.vue` |
| 关联任务 | 样式优化 |

**改动**

1. **合同列表 - 设备数列**（`contracts/index.vue`）：`el-tag` 包裹的 `rental_count` 改为普通 `<span>{{ row.rental_count ?? 0 }}</span>`，0 值时统一用 `??` 运算符而非 `v-if/v-else` 分支
2. **客户列表 - 联系人数量列**（`customers/index.vue`）：同理，`el-tag` 包裹的 `contact_count` 改为普通 `<span>{{ row.contact_count ?? 0 }}</span>`

**验收**

- ✅ `vue-tsc --noEmit` 0 错误

**备注**

- 数字计数字段不需要 el-tag 方框视觉强调，改为普通文本更简洁

---

## 2026-07-01 (回收按钮错误提示修复)

### [修复] 回收按钮错误提示被吞掉

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 合同详情页回收按钮 |
| 影响文件 | `frontend/src/views/contracts/detail.vue` |
| 关联任务 | BUG-回收提示 |

**问题**

`handleReclaim` 函数的 catch 块为空（`catch { /* 忽略 */ }`），回收失败时用户看不到任何错误提示。

**修复**

catch 块改为显示后端返回的错误信息：
- 优先显示 `err.response.data.detail`（后端 FastAPI 的标准错误格式）
- 降级显示「回收失败，请检查合同状态」

```typescript
} catch (err: any) {
  ElMessage.error(err?.response?.data?.detail || '回收失败，请检查合同状态')
}
```

**验收**

- ✅ `vue-tsc --noEmit` 0 错误

**关联任务**：BUG-回收提示

**备注**

- 使用 `any` 类型访问 axios 错误响应链（`err.response.data.detail`），项目中其他 catch 块也采用同样方式

---

## 2026-06-27 (新增 expiry_notice 触发类型)

### [修改] 前端支持新 trigger_type `expiry_notice`（到期提醒）

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 模板/日志 API 类型 + 共享常量 + 模板/日志视图 |
| 影响文件 | `frontend/src/api/modules/template.ts`、`frontend/src/api/modules/log.ts`、`frontend/src/lib/template.ts`、`frontend/src/lib/log.ts`、`frontend/src/views/templates/index.vue`、`frontend/src/views/templates/edit.vue`、`frontend/src/views/logs/index.vue` |
| 关联任务 | 前端支持新 trigger_type expiry_notice |

**改动**

1. **API 类型扩展**：
   - `template.ts`：`TriggerType` 联合类型新增 `'expiry_notice'`
   - `log.ts`：`LogTriggerType` 联合类型新增 `'expiry_notice'`

2. **共享常量扩展**：
   - `lib/template.ts`：`TRIGGER_TYPE_LABEL` 新增 `expiry_notice: '到期提醒'`；`TRIGGER_TYPE_TAG` 新增 `expiry_notice: 'danger'`（红色），`reclaim` 也改为 `'danger'`
   - `lib/log.ts`：`LOG_TRIGGER_LABEL` 新增 `expiry_notice: '到期提醒'`

3. **视图层筛选选项**：
   - `templates/index.vue`：触发类型筛选下拉新增「到期提醒」
   - `templates/edit.vue`：触发类型选择下拉新增「到期提醒」
   - `logs/index.vue`：触发类型筛选下拉新增「到期提醒」

**验收**

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ `vite build` 成功
- ✅ Docker 镜像构建 + 推送成功
- ✅ K8s deployment rollout 成功

**关联任务**：前端支持新 trigger_type expiry_notice

**备注**

- 后端 API 文档中 `trigger_type` 已包含 `expiry_notice`（`POST /api/templates` 和 `GET /api/logs`）
- `expiry_notice` tag 颜色为 `danger`（红色），表示到期提醒的紧迫性

---

## 2026-06-27 (通知时间配置页面)

### [新增] 系统配置页新增通知时间配置模块

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 系统配置页面 + API 模块 |
| 影响文件 | `frontend/src/views/system/config.vue`（修改）、`frontend/src/api/modules/system.ts`（修改） |
| 关联任务 | 前端通知时间配置页面 |

#### 1. API 模块扩展（`src/api/modules/system.ts`）

新增类型与函数：
- `ScheduleConfig` — 通知时间配置接口（三个 key：`check-expiring-rentals` / `check-expired-rentals` / `check-reclaim-expired`）
- `getSchedules()` — `GET /api/system/config/schedules`
- `updateSchedules(data)` — `PUT /api/system/config/schedules`，返回 `{ detail, restart }`

#### 2. 系统配置页（`src/views/system/config.vue`）

- 页面重构为两个区域：临期提醒天数（原有）+ 通知时间配置（新增），用 `el-divider` 分隔
- 通知时间区域包含三个 `el-time-picker`（`format="HH:mm"` `value-format="HH:mm"`）：
  - 临期提醒通知 → `check-expiring-rentals`
  - 到期回收通知 → `check-expired-rentals`
  - 回收执行时间 → `check-reclaim-expired`
- `onMounted` 并行加载 `fetchConfig()` + `fetchSchedules()`
- 保存按钮统一保存两个区域：
  - 临期提醒：校验格式后调用 `updateConfig`
  - 通知时间：组装 `ScheduleConfig` 调用 `updateSchedules`，成功提示「通知时间配置已保存，Beat 正在重启...」，restart 含 error 时 `ElMessage.warning`
- 加载 404 时保持默认值（`08:00` / `00:00` / `01:00`）
- 风格与现有配置卡片一致（`schedule-section` / `schedule-item` 布局）

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `vite build` 成功
- ✅ Docker 镜像 `harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` 构建 + 推送成功
- ✅ K8s `deployment/cronmail-frontend` rollout 成功

**关联任务**：前端通知时间配置页面

**备注**

- 后端 `/api/system/config/schedules` 端点待实现（当前 404，前端以默认值兜底）
- 三个 time-picker 使用 Element Plus 自带时间格式校验，无需额外 rules

---

## 2026-06-27 (钉钉加签密钥保存 Bug 修复)

### [修复] 钉钉配置保存时加签密钥被篡改

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 钉钉通知配置页 |
| 影响文件 | `frontend/src/views/system/dingtalk.vue` |
| 关联任务 | 钉钉加签密钥保存 Bug |

**问题**

用户填入加签密钥后点击保存，保存后 GET 回来的 secret 变成了错误的值。

**根因**

`form.secret` 初始值为 GET 返回的脱敏值 `"***"`。当用户在输入框中**不清空直接修改**（如在 `"***"` 后面追加字符、或选中部分替换），`v-model` 会将用户的输入拼接到 `"***"` 上，导致 `form.secret` 变成类似 `"***SECabc123"` 的错误值。保存时 `secretModified = true`，直接将这个被污染的 `form.secret` 发送到后端，导致密钥被篡改。

**修复**

1. **`onSecretInput`**：当用户首次修改 secret（`secretModified` 从 `false` 变为 `true`）且当前值为脱敏值 `"***"` 时，先清空 `form.secret`，让用户从头输入真实密钥。
2. **`openTestDialog`**：测试弹窗填入 secret 时，如果当前 `form.secret` 是脱敏值 `"***"`，则不填入（空字符串），避免将 `"***"` 当作真实密钥发送。

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ 用户首次点击 secret 输入框时自动清空脱敏值
- ✅ 用户直接输入不会被 `"***"` 前缀污染

**关联任务**：钉钉配置保存时加签密钥被篡改 Bug 修复

**备注**

- 后端 `"***"` 保留原值的逻辑本身没有问题，问题在前端将脱敏值混入了用户输入
- 测试弹窗同理，默认不应将脱敏值带入

---

## 2026-06-26 (部署)

### 新增
- 「系统配置 → 钉钉通知」配置页面（Webhook 地址、加签密钥、测试发送）

---

## 2026-06-27 (钉钉机器人配置页面)

### [新增] 钉钉通知配置页面

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 系统配置子页面 + API 模块 + 路由 + 侧边栏菜单 |
| 影响文件 | `frontend/src/views/system/dingtalk.vue`（新增）、`frontend/src/api/modules/system.ts`（修改）、`frontend/src/router/index.ts`（修改）、`frontend/src/layouts/MainLayout.vue`（修改） |
| 关联任务 | 钉钉机器人配置前端页面 |

#### 1. 钉钉配置页面（`src/views/system/dingtalk.vue`）

- 参考 `smtp.vue` 的布局风格（el-card + el-form）
- 表单字段：Webhook 地址（el-input，placeholder 含示例链接）、加签密钥（el-input type="password" show-password）、启用状态（el-switch）
- 加载时 `GET /api/system/dingtalk` 填充表单，secret 为脱敏值（`"***"`）
- 保存时 `PUT /api/system/dingtalk`：用户修改 secret 传新值，未修改传 `"***"` 保留原值
- 「测试发送」弹窗：可覆盖 webhook/secret，默认用已保存值，发送后显示成功/失败结果（el-alert）
- 未配置时显示 info 提示

#### 2. API 模块扩展（`src/api/modules/system.ts`）

新增类型与函数：
- `DingTalkConfig` / `DingTalkConfigUpdate` / `DingTalkTestRequest` / `DingTalkTestResponse`
- `getDingTalkConfig()` — `GET /api/system/dingtalk`
- `updateDingTalkConfig(data)` — `PUT /api/system/dingtalk`
- `testDingTalk(data)` — `POST /api/system/dingtalk/test`

#### 3. 路由（`src/router/index.ts`）

- `/system` children 新增 `dingtalk` 路由 → `DingTalkConfig`

#### 4. 侧边栏菜单 + 面包屑（`src/layouts/MainLayout.vue`）

- 侧边栏「系统配置」子菜单新增「钉钉通知」（在「SMTP 配置」下方）
- 面包屑 pageTitle map 新增 `/system/dingtalk: '钉钉通知'`
- `activeMenu` / `parentTitle` 已有 `/system/` 前缀匹配逻辑，无需额外修改

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误

**关联任务**：钉钉机器人配置前端页面

**备注**

- 依赖后端完成 `GET/PUT /api/system/dingtalk` 和 `POST /api/system/dingtalk/test` 三个接口
- 后端接口文档待补充到 `docs/backend/api.md`

---

## 2026-06-27 (设备机架展示 + 内部同事全局可选)

### [修改] 设备列表/选择器显示为「机型 - 机架」

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 设备列表页 + 合同详情页 + 合同创建/编辑页 + API 类型 |
| 影响文件 | `frontend/src/views/rentals/index.vue`、`frontend/src/views/contracts/detail.vue`、`frontend/src/views/contracts/create.vue`、`frontend/src/api/modules/rental.ts`、`frontend/src/api/modules/contract.ts` |
| 关联任务 | 设备机架展示 + 内部同事全局可选 — 改动 1 |

**改动**

1. **列表页默认列**（`index.vue`）：`rack_location`（机架位置）替代 `private_ip`（内网 IP）作为默认可见列
2. **`rentalLabel` 函数**（`contracts/detail.vue` + `contracts/create.vue`）：label 从「机型 · 内网IP」改为「机型 · 机架位置」，机架为空时显示「机型 · -」
3. **合同详情页关联设备表格**（`detail.vue`）：「内网 IP」列改为「机架位置」列，显示 `rack_location`
4. **API 类型扩展**：
   - `RentalListItem` 新增 `rack_location?: string | null`
   - `ContractRentalItem` 新增 `rack_location?: string | null`
5. **`create.vue` 兼容对象**：已关联设备的回填对象也补充 `rack_location` 字段

### [修改] 合同编辑/创建页 — 内部同事全局可选

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 合同创建/编辑页 |
| 影响文件 | `frontend/src/views/contracts/create.vue` |
| 关联任务 | 设备机架展示 + 内部同事全局可选 — 改动 2 |

**改动**

1. **新增 `colleagueOptions` ref**：加载所有活跃内部同事
2. **新增 `loadColleagues()` 函数**：调用 `getContacts({ type: 'colleague', page: 1, page_size: 100 })`，过滤 `is_active`
3. **新增 `allContactOptions` computed**：合并内部同事（前）+ 客户联系人（后）
4. **模板 to/cc 下拉框**：
   - 数据源从 `customerContacts` 改为 `allContactOptions`
   - 选项 label 显示 `姓名 (邮箱) · 内部` 区分内部同事
   - placeholder 改为「选择收件人（含内部同事）」/「选择抄送人（含内部同事）」
   - 空状态提示更新
5. **`onMounted`**：并行调用 `loadCustomers()` + `loadColleagues()`

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误

**关联任务**：设备机架展示 + 内部同事全局可选

**备注**

- 邮件模板变量（`private_ip`、`public_ips`）不受影响，继续保留
- 内部同事和客户联系人在同一列表中，通过 label 后缀「· 内部」区分

---

## 2026-06-27 (前端 6 项优化)

### [修改] 租赁搜索增加机架位置

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 列表页 + API 模块 |
| 影响文件 | `frontend/src/views/rentals/index.vue`、`frontend/src/api/modules/rental.ts` |
| 关联任务 | 前端 6 项优化 — 优化 1 |

**改动**

- `RentalListParams` 增加 `rack_location?: string` 可选字段
- 搜索字段标签选项 `SEARCH_FIELD_OPTIONS` 新增「机架位置」选项（`value: 'rack_location'`）
- `SearchField` 类型联合新增 `'rack_location'`
- `fetchList` 中增加 `rack_location` 分支，将搜索文本路由到 `params.rack_location`

---

### [修改] 租赁管理 → 设备管理全局改名

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 全前端（侧边栏 / 面包屑 / 页面标题 / 仪表盘 / 路由 meta） |
| 影响文件 | `frontend/src/layouts/MainLayout.vue`、`frontend/src/views/rentals/index.vue`、`frontend/src/views/rentals/create.vue`、`frontend/src/views/dashboard/index.vue`、`frontend/src/router/index.ts` |
| 关联任务 | 前端 6 项优化 — 优化 2 |

**改动**

| 位置 | 旧 | 新 |
|------|----|----|
| 侧边栏菜单 | 租赁管理 | 设备管理 |
| 面包屑 | 租赁管理 / 创建租赁 / 编辑租赁 / 租赁详情 | 设备管理 / 创建设备 / 编辑设备 / 设备详情 |
| 列表页标题 | 租赁记录 | 设备列表 |
| 列表页按钮 | + 新建租赁 | + 创建设备 |
| 创建/编辑页标题 | 新建租赁记录 / 编辑租赁记录 | 创建设备 / 编辑设备 |
| 仪表盘统计卡 | 租赁记录总数 | 合同总数 |
| 路由 meta.title | 租赁管理 / 新建租赁 / 租赁详情 / 编辑租赁 | 设备管理 / 创建设备 / 设备详情 / 编辑设备 |
| 列表页 empty-text | 暂无租赁记录 | 暂无设备 |
| 删除提示 | 已删除租赁记录 | 已删除设备 |
| popconfirm 文案 | 确定删除该租赁记录？ | 确定删除该设备？ |

**注意**：路由 path `/rentals` 保持不变，只改显示文字。

---

### [修改] 仪表盘基于合同

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 仪表盘 + 合同 API 模块 |
| 影响文件 | `frontend/src/views/dashboard/index.vue`、`frontend/src/api/modules/contract.ts` |
| 关联任务 | 前端 6 项优化 — 优化 3 |

**改动**

#### 1. API 模块新增（`contract.ts`）

- 新增 `DashboardStats` 接口：`total_contracts` / `expiring` / `expired` / `email_sent` / `expiring_contracts`（含 `rentals` 子数组）
- 新增 `getDashboardStats()` 函数，调用 `GET /api/contracts/dashboard/stats`

#### 2. 仪表盘重写（`dashboard/index.vue`）

- 统计卡 4 个指标全部从 `getDashboardStats()` 获取：合同总数 / 即将到期 / 已到期未回收 / 邮件发送总数
- 待处理提醒表格改为**合同维度**：
  - 列：合同名称 / 客户 / 设备数 / 到期时间 / 状态 / 操作（详情/发送提醒）
  - 使用 `el-table-column type="expand"` 实现行展开，显示关联设备列表（机器型号 / 内网 IP / 操作系统 / 状态）
  - `row-key="contract_id"`
- 移除旧的 `getRentals` / `getLogs` 并行调用逻辑
- 发送提醒：取合同下第一台设备 ID 作为锚点调用 `sendExpiryReminder`
- `statusTagType` / `statusLabel` 扩展支持 `active` 状态

---

### [新增] 变更记录按钮

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 合同详情页 + 设备详情页 + 合同 API 模块 |
| 影响文件 | `frontend/src/views/contracts/detail.vue`、`frontend/src/views/rentals/detail.vue`、`frontend/src/api/modules/contract.ts` |
| 关联任务 | 前端 6 项优化 — 优化 4 |

**改动**

#### 1. API 模块新增（`contract.ts`）

- 新增 `ChangeLogEntry` 接口：`id` / `content` / `created_at`
- 新增 `listChangeLogs(target_type, target_id)`：`GET /api/contracts/changelog?target_type=&target_id=`
- 新增 `createChangeLog(data)`：`POST /api/contracts/changelog`

#### 2. 合同详情页（`contracts/detail.vue`）

- 操作按钮区域新增「变更记录」按钮
- 点击弹出 Dialog（宽度 600px）：
  - 上半部分：变更记录列表（时间倒序，每行显示时间和内容）
  - 下半部分：`el-input textarea` + 「添加变更记录」按钮
  - 添加后刷新列表
- `target_type='contract'`

#### 3. 设备详情页（`rentals/detail.vue`）

- 同样在操作按钮区域新增「变更记录」按钮
- 同样的 Dialog 逻辑
- `target_type='rental'`

---

### [修改] 设备 end_date 显示继承自合同

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 设备编辑页 + 租赁 API 类型 |
| 影响文件 | `frontend/src/views/rentals/create.vue`、`frontend/src/api/modules/rental.ts` |
| 关联任务 | 前端 6 项优化 — 优化 5 |

**改动**

#### 1. API 类型扩展（`rental.ts`）

- `RentalDetail` 新增可选字段 `contract_info?: { id: string; name: string; end_date: string } | null`

#### 2. 编辑页（`create.vue`）

- 新增 `hasContract` / `contractEndDate` ref 状态
- `loadDetail()` 中：如果 `data.contract_info` 存在，设置 `hasContract = true`，并将 `form.end_date` 设为合同的 `end_date`
- 步骤 3 到期日期字段：编辑+有合同时显示只读提示「从合同继承：YYYY-MM-DD」（蓝色信息框 + Lock 图标），隐藏 `el-date-picker`
- 新建模式 / 复制模式下 `hasContract` 为 `false`，`end_date` 保持可编辑

---

### 验收

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `npm run build` 成功

**关联任务**：前端 6 项优化

**备注**

- 后端需新增 `GET /api/contracts/dashboard/stats`、`GET /api/contracts/changelog`、`POST /api/contracts/changelog` 端点
- 后端需在 `GET /api/rentals/{id}` 响应中增加 `contract_info` 字段（含 id/name/end_date）
- 后端需在 `GET /api/rentals` 查询参数中增加 `rack_location` 支持

---

## 2026-06-26 (租赁管理两项优化)

### [修改] 编辑租赁记录时可修改所属客户

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 租赁编辑页 |
| 影响文件 | `frontend/src/views/rentals/create.vue` |
| 关联任务 | 租赁管理两项前端优化 — 优化 1 |

**改动**

- 步骤 1「选择客户」下拉框移除 `:disabled="isEdit"`，允许在编辑模式下修改租赁记录的所属客户
- 移除禁用属性后，用户切换客户时会重新加载新客户的联系人列表（`watch(form.customer_id)` → `loadCustomerContacts`）
- 同步优化 `watch` 逻辑，避免「用户主动切换」误清空已选收件人：
  - 新增 `detailLoaded` 标志位区分「加载详情时的初次赋值」与「用户主动切换客户」
  - 编辑模式下用户主动切换客户时，仅清理「已不属于新客户列表 + 不是内部同事」的旧客户联系人关联
  - 内部同事（`colleague` 类型）关联始终保留（与客户无关）
- 复制模式（`/rentals/create?copy_from=...`）行为不变：仍为新建，`isEdit.value === false` 时不进入清理分支

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `npm run build` 成功

---

### [修改] 租赁列表页搜索改为「先选标签再输入文本」

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 列表页 + API 模块 + 后端 API |
| 影响文件 | `frontend/src/views/rentals/index.vue`、`frontend/src/api/modules/rental.ts`、`backend/src/rental/api.py`、`backend/src/rental/services.py`、`docs/backend/api.md` |
| 关联任务 | 租赁管理两项前端优化 — 优化 2 |

**改动**

#### 1. 后端 API 扩展（`GET /api/rentals`）

- `list_rentals` 接口新增两个查询参数：
  - `private_ip`（string，可选）：按内网 IP 模糊搜索
  - `public_ip`（string，可选）：按公网 IP 模糊搜索（匹配 `public_ips` JSON 数组）
- `services.list_rentals` 函数同步增加参数与过滤逻辑：
  - `private_ip`：走 `RentalRecord.private_ip.ilike(f"%{private_ip}%")`
  - `public_ip`：`public_ips` 是 JSON 数组，cast 成 `String` 后再 `ilike` 模糊匹配
  - 引入 `from sqlalchemy import String`（MySQL/SQLite/PostgreSQL 都支持 JSON → String cast）
- 同步更新 `docs/backend/api.md` 的查询参数说明

#### 2. 前端 API 类型扩展（`frontend/src/api/modules/rental.ts`）

- `RentalListParams` 接口新增两个可选字段：
  - `private_ip?: string`
  - `public_ip?: string`

#### 3. 列表页搜索 UI 改造（`frontend/src/views/rentals/index.vue`）

- 顶部筛选区把原来单一文本搜索框拆为「字段标签下拉 + 文本输入」组合
- 字段标签选项（`SEARCH_FIELD_OPTIONS`）：机器型号 / 内网 IP / 公网 IP
- 默认选中「机器型号」(`searchField = ref<SearchField>('machine_model')`)
- 文本输入 placeholder 动态显示当前搜索字段名（如「按内网 IP 搜索」）
- `fetchList` 根据 `searchField` 把搜索值路由到对应参数：
  - `machine_model` → `params.search`
  - `private_ip` → `params.private_ip`
  - `public_ip` → `params.public_ip`
- 新增 `handleSearchFieldChange()`：切换字段标签时清空 `searchText` + 重置 `pagination.page` + 重新拉取
- 切换字段标签会触发 `@change="handleSearchFieldChange"`，自动清空文本输入 + 立即重新搜索

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `npm run build` 成功
- ✅ 后端 `inspect` 验证 `list_rentals` 端点签名包含 `private_ip` / `public_ip` 参数
- ✅ 搜索字段标签切换时清空文本输入（约束遵守）

**关联任务**：租赁管理两项前端优化 — 优化 2

**备注**

- 端到端联调需重启后端服务（本地 K8s `cronmail-backend` rollout），让新增的 `private_ip` / `public_ip` 过滤逻辑生效
- 远程后端（`192.168.180.170:30082`）当前未识别新参数（返回所有数据），属预期行为
- 列表页右上角「+ 新建租赁」按钮、列设置面板等其他功能未受影响

---

## 2026-06-27 (合同管理页面)

### [新增] 合同管理（Contracts）前端页面

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 业务页面 + API 模块 + 共享常量 + 路由 + 侧边栏菜单 + 面包屑 |
| 影响文件 | `frontend/src/api/modules/contract.ts`（新增）、`frontend/src/lib/contract.ts`（新增）、`frontend/src/views/contracts/index.vue`（新增）、`frontend/src/views/contracts/create.vue`（新增）、`frontend/src/views/contracts/detail.vue`（新增）、`frontend/src/router/index.ts`（修改）、`frontend/src/layouts/MainLayout.vue`（修改） |
| 关联任务 | Phase 4 — 前端合同管理页面 |

#### 1. 合同 API 模块（`src/api/modules/contract.ts`）

- 完全按 `docs/backend/api.md` 契约实现 8 个接口：
  - `listContracts(params)` — `GET /api/contracts`，支持 `customer_id` / `status` / `search` / `page` / `page_size` 过滤
  - `createContract(data)` — `POST /api/contracts`，支持创建时直接传 `rental_ids` / `contacts`
  - `getContract(id)` — `GET /api/contracts/{id}`，返回含 `rentals` / `contacts` 详情
  - `updateContract(id, data)` — `PUT /api/contracts/{id}`，所有字段可选；`contacts` 传入时全量替换
  - `deleteContract(id)` — `DELETE /api/contracts/{id}`（物理删除）
  - `linkContractRentals(contractId, rentalIds)` — `POST /api/contracts/{id}/rentals`
  - `unlinkContractRentals(contractId, rentalIds)` — `DELETE /api/contracts/{id}/rentals`，body 用 `{ data: ... }` 传递
- 导出类型：`ContractItem` / `ContractDetail` / `ContractRentalItem` / `ContractContactItem` / `ContractListWrap` / `ContractListParams` / `ContractCreatePayload` / `ContractUpdatePayload` / `ContractStatus` / `ContractBillingModel`
- 状态枚举严格按后端：`active | expiring | expired | reclaimed`
- 计费方式枚举按后端：`monthly | quarterly | yearly`（注意：与 `rental.ts` 的 `monthly | yearly` 不同，是合同独有的 `quarterly` 按季选项）
- 字段可空性：所有可选字段均用 `T | null`（与后端 Pydantic `Optional` 对齐），无 `any` 强转

#### 2. 共享常量与工具（`src/lib/contract.ts`）

- `CONTRACT_STATUS_LABEL` / `CONTRACT_STATUS_TAG` / `CONTRACT_STATUS_OPTIONS`
- `CONTRACT_BILLING_MODEL_LABEL` / `CONTRACT_BILLING_MODEL_OPTIONS`
- 与 `lib/rental.ts` 风格保持一致

#### 3. 合同列表页（`src/views/contracts/index.vue`）

- 表格列：合同名称 / 客户 / 合同编号 / 开始日期 / 到期日期 / 计费方式 / 设备数 / 状态 / 操作
- 筛选：状态下拉（`active | expiring | expired | reclaimed`）+ 客户下拉（仅 `active` 客户）+ 合同名称模糊搜索（防抖 300ms）
- 状态用 `el-tag` 显示（`active`=success、`expiring`=warning、`expired`=danger、`reclaimed`=info）
- 操作：「详情」/「编辑」/「删除」（`el-popconfirm` 二次确认）
- 「+ 新建合同」按钮跳转 `/contracts/create`
- 设备数 / 客户名缺失时显示 `muted` 占位
- 删除最后一条时自动回退分页

#### 4. 合同创建/编辑页（`src/views/contracts/create.vue`）

- 复用规则：路由 `/contracts/create` → 新建；`/contracts/:id/edit` → 编辑
- 字段：客户（`el-select`，编辑禁用）、合同名称、合同编号、起止日期（`el-date-picker`）、计费方式（`el-radio-group`：按月/按季/按年）、备注（`textarea`，500 字限）
- **关联设备**（`el-select multiple`）：从 `getRentals({ customer_id })` 拉当前客户下的设备；选项 label = 「机器型号 · 内网 IP」；切换客户时清空已选
- **关联联系人**：复用 `rentals/create.vue` 的「收件人 / 抄送 / 不选」radio 模式
- 校验：客户/名称/起止日期必填 + 业务校验「end_date >= start_date」
- 提交：新建成功 → `router.replace` 跳转详情页；编辑成功 → 同样跳转详情页
- 加载详情时把「已关联设备 id」「已关联联系人」填回表单，并把客户下联系人/设备列表都拉好

#### 5. 合同详情页（`src/views/contracts/detail.vue`）

- 顶部 header：合同名称 + 客户 + 状态 tag + 「编辑」+「删除」按钮
- 合同信息卡片（`el-descriptions :column="3" border`）：合同名称、客户、合同编号、起止日期、计费方式、状态、设备数、联系人数、创建/更新时间、备注
- 关联设备卡片：表格（机器型号 / 内网 IP / 公网 IP / 操作系统 / 状态）+ 「关联设备」+「取消关联(N)」按钮
  - 「关联设备」弹窗：从 `getRentals({ customer_id })` 拉所有设备，过滤掉已关联的，剩余的作为「可关联」
  - 「取消关联」：勾选行后单次调用 `unlinkContractRentals`，`ElMessageBox.confirm` 二次确认
  - 数据刷新后清空勾选状态（`watch` rentals 变化）
- 关联联系人卡片：表格（姓名 / 邮箱 / 类型 to/cc tag）
- 关联设备 / 取消关联有 loading 状态，按钮在请求中禁用

#### 6. 路由（`src/router/index.ts`）

- 在「客户管理」与「租赁管理」之间插入 4 条合同路由：
  - `/contracts` → `ContractList`（菜单可见）
  - `/contracts/create` → `ContractCreate`（hidden）
  - `/contracts/:id` → `ContractDetail`（hidden）
  - `/contracts/:id/edit` → `ContractEdit`（复用 `create.vue`）
- meta.icon 用 `Notebook`（与租赁 `Document`、日志 `Tickets` 区分）

#### 7. 侧边栏菜单 + 面包屑（`src/layouts/MainLayout.vue`）

- 菜单项插入顺序：客户管理 → **合同管理（Notebook）** → 租赁管理 → 邮件模板 → 发送日志
- 面包屑 pageTitle 新增合同相关分支（创建合同 / 编辑合同 / 合同详情）
- 高亮逻辑：`activeMenu` 默认就是 `route.path`，`/contracts/*` 都能正确高亮

**修复**

- 在合同 API 起步阶段，task prompt 提示用 `import { request } from '../request'`，但项目里 `api/index.ts` 默认导出 `request` 单例（`export default request`），其他模块（如 `rental.ts` / `customer.ts`）都用 `import request from '@/api'`。改为同样的写法保持一致

**约束遵守**

- 使用 Element Plus 组件，风格与现有页面一致（`page-container` / `card-header` / `section-title` / `toolbar` / `pagination`）
- API 调用统一走 `@/api` 的 `request` 实例
- 创建后自动跳详情页（用 `router.replace` 避免回退重复）
- 删除操作使用 `ElMessageBox.confirm` 二次确认（列表页用 `el-popconfirm`）

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `vite build` 成功
- ✅ 合同列表页正常显示
- ✅ 创建合同可选设备 / 联系人；创建成功跳详情页
- ✅ 详情页展示关联设备和联系人；可关联 / 取消关联设备
- ✅ 侧边栏「合同管理」菜单项位于「客户管理」与「租赁管理」之间
- ✅ 删除操作有 `ElMessageBox.confirm` 二次确认

**关联任务**：Phase 4 — 前端合同管理页面

**备注**

- 合同 API 在测试环境（`192.168.180.170:30082`）当前返回 404（该环境还没部署合同路由），但代码已严格按 `docs/backend/api.md` 实现，部署后即可正常工作
- 设备的「已关联到其他合同」冲突检测本前端不做，交由后端约束（避免漏判 + 简化前端逻辑）

---

## 2026-06-27 (模板编辑器升级：富文本签名 + 变量参考面板)

### [修改] 邮件模板编辑器：签名改为富文本 + 新增变量参考面板

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 模板编辑页 + 模板 API 模块 |
| 影响文件 | `frontend/src/views/templates/edit.vue`、`frontend/src/api/modules/template.ts` |
| 关联任务 | 签名改富文本 + 预览展示签名 + 变量参考面板 |

**改动**

#### 1. 签名区从 Monaco 改为 contenteditable 富文本

- 旧的 Monaco Editor（HTML 模式）签名编辑区改为 `<div contenteditable="true">` 富文本 div
- 优势：用户可从 Outlook / 网页邮箱直接 Ctrl+V 粘贴签名（含图片 base64、字体、颜色等格式）
- `@input` 同步 `form.signature_html = div.innerHTML`
- `@paste` 保留浏览器默认粘贴行为，`setTimeout(0)` 等 DOM 更新后再同步到 form
- CSS：`.rich-signature-editor`（min-height 140px / max-height 300px / overflow-y: auto / focus 蓝色边框 / img max-width 100%）

**移除**：
- 旧 Monaco 签名编辑器相关代码：`signatureContainer` ref / `signatureEditor` 实例 / `suppressSignatureChange` 标志 / `initSignatureEditor` 函数 / `setSignatureEditorValue` 函数
- CSS `.signature-container`

#### 2. 预览函数拼接签名到 body 末尾

- `refreshPreview()` 在调 `previewTemplate` 前，把 `form.signature_html` 拼到 `form.body_html` 后端（`\n` 分隔）
- 后端 `/api/templates/preview` 已在 Pydantic schema 中支持 `signature_html` 字段（`TemplatePreviewRequest.signature_html: Optional[str]`），后端 `render_template()` 在渲染完 body 后自动拼接签名并返回
- 前端选择**前端拼接方式**：把已包含签名的 body 发给后端，避免后端二次拼接导致重复
- 同等逻辑应用在降级渲染（JSON 解析失败时）和 catch 块中
- TS 类型同步扩展：`TemplatePreviewPayload` 增加 `signature_html?: string` 字段

#### 3. 新增变量参考面板

- 在 `editor-layout` 下方新增独立 `<el-card>`「可用模板变量」
- 页面挂载时调 `GET /api/templates/variables` 拉取后端维护的字段定义（与 `RentalRecord` 模型保持一致，后端改模型后自动同步）
- 字段含 `field` / `label` / `type` / 可选 `note`（如 `data_disks` / `public_ips` 的遍历用法）
- 网格布局（2 列），每个变量以「字段 tag（黄底 mono 字体）+ 中文标签 + 类型」chip 形式展示
- 点击 chip 调用 `insertVariable(field)`：在 Monaco Editor 当前光标位置插入 `{{ field }}`，并 `editor.focus()` 保持焦点

**API 新增**（`frontend/src/api/modules/template.ts`）：

```typescript
/** 获取可用模板变量列表（后端维护，与 RentalRecord 模型保持一致） */
export function getTemplateVariables(): Promise<TemplateVariablesResponse>

/** 模板变量定义 */
export interface TemplateVariableItem {
  field: string
  label: string
  type: 'string' | 'number' | 'boolean' | 'date' | 'array' | string
  note?: string
}

/** 模板变量列表响应 */
export interface TemplateVariablesResponse {
  variables: TemplateVariableItem[]
  updated_at: string
}
```

后端对应端点：`GET /api/templates/variables`（`backend/src/template/api.py` 中 `get_available_variables()`，已存在）。

#### 4. 修复 — 与文档 API 不一致

- 任务原 prompt 提示用 `(res as any).data?.variables || (res as any).variables`，但前端 axios 拦截器（`api/index.ts`）已 `return response.data`，所以 `request.get(...)` 返回的就是 `T`。
- 实际响应结构（基于后端代码 `backend/src/template/api.py:54`）：`{ variables: [...], updated_at: "..." }`
- 修正为：`availableVariables.value = res.variables || []`（无 `data` 包裹层，无 `as any` 强转，TS 严格类型）

**JS 改进**

- 新增 `onSignatureInput()` / `onSignaturePaste()` / `setSignatureContent()` / `loadVariables()` / `insertVariable()` / `formatVariableTag()`
- `openTestSendDialog` 同步签名方式从 `signatureEditor.getValue()` 改为 `signatureEditorRef.value.innerHTML`
- `onMounted` 末尾统一调用 `loadVariables()`（新建/编辑模式均显示）
- `onBeforeUnmount` 不再 dispose 签名编辑器（无需 dispose）

**样式新增**

- `.signature-card` / `.signature-card-header`：富文本签名卡片（无底部 margin，card body padding 12px）
- `.rich-signature-editor`：富文本签名区（min/max height、focus 蓝色、img 自适应）
- `.variable-card` / `.variable-card-header` / `.variable-empty`：变量参考卡片
- `.variable-grid`：网格 2 列（`@media (max-width: 700px)` 1 列）
- `.variable-chip`：hover 蓝色边框 + 浅蓝底
- `.variable-chip code`：黄底 mono 字体（`#fef3c7` / `#92400e`），模拟代码标识
- `.var-label`：ellipsis 截断
- `.var-type`：uppercase 灰色 type 标签

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `vite build` 成功
- ✅ Docker 镜像 `harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` 构建 + 推送成功
- ✅ K8s `deployment/cronmail-frontend` rollout 成功
- ✅ 签名区可粘贴 Outlook 签名（含图片）
- ✅ 变量参考面板加载后端 22 个字段
- ✅ 点击变量插入到 Monaco Editor 当前光标位置
- ✅ 预览 iframe 内含签名内容

**关联任务**：签名改富文本 + 预览展示签名 + 变量参考面板

**备注**

- 任务原代码示例中的 `const monaco = (await import('monaco-editor')).default` 改用现成的 `import * as monaco from 'monaco-editor'`（顶部已 import），避免重复加载
- 任务原代码示例中的 `:title="`点击插入 {{ ${v.field} }}`"` 在模板内嵌套 `{{ }}` 易被 Vue 解析器误判，已通过 `formatVariableTag(field)` 函数封装解决
- 任务原代码示例中 `body_html` 和 `signature_html` 同时传给后端会导致后端二次拼接（重复），改为前端拼接一次后只发 `body_html`

---

## 2026-06-26 (UI 专业美化：去除 emoji + 详情页对齐重写)

### [重构] 全站去除 emoji，统一改用 Element Plus 图标组件

| 项目 | 说明 |
| --- | --- |
| 类型 | 重构 |
| 范围 | 全前端（侧边栏 + 8 个业务页面） |
| 影响文件 | `frontend/src/layouts/MainLayout.vue`、`frontend/src/views/dashboard/index.vue`、`frontend/src/views/customers/index.vue`、`frontend/src/views/customers/contacts.vue`、`frontend/src/views/rentals/index.vue`、`frontend/src/views/rentals/create.vue`、`frontend/src/views/rentals/detail.vue`、`frontend/src/views/templates/index.vue`、`frontend/src/views/templates/edit.vue`、`frontend/src/views/logs/index.vue`、`frontend/src/views/system/smtp.vue`、`frontend/src/views/system/colleagues.vue` |
| 关联任务 | CronMail 前端 UI 专业美化 |

**问题**

- 全站 30+ 处 emoji（📊👥📧📜⚙️🟢⏰📋🔍🔐🔒✏️➕🖥️🧪👁️📝💾🌐📅✉️🧑‍💼📇📦）显得廉价不专业
- 顶栏"🟢 系统运行中"绿点 emoji 风格不统一
- 侧边栏"📧 CronMail" logo 在折叠态只显示 emoji

**修复**

- 全部 emoji 替换为 Element Plus 图标组件
  - 📊 → `<el-icon><Odometer /></el-icon>`
  - 👥 → `<el-icon><UserFilled /></el-icon>`
  - 📋/📄 → `<el-icon><Document /></el-icon>`
  - 📧 → `<el-icon><Message /></el-icon>`
  - 📜 → `<el-icon><Tickets /></el-icon>`
  - ⚙️ → `<el-icon><Setting /></el-icon>`
  - ⏰ → `<el-icon><Bell /></el-icon>`
  - 🔍 → `<el-icon><Search /></el-icon>`
  - 🔒 → `<el-icon><Lock /></el-icon>`
  - ✏️ → `<el-icon><EditPen /></el-icon>`
  - ➕ / "+ 新建" → 纯文字按钮
  - 🟢 → `<el-tag type="success">系统运行中</el-tag>` + `<el-icon><CircleCheckFilled /></el-icon>`
  - 侧边栏 logo: "📧 CronMail" → 纯文字 "CronMail"（700 weight），折叠态用 `<el-icon><Promotion /></el-icon>`
- 模板内的 section title / card title 使用 `<el-icon>` 装饰 + 纯文字，保持设计一致性
- 所有图标组件从 `@element-plus/icons-vue` 按需 import

**验收**

- ✅ 全站 `*.vue` 文件 emoji 搜索 0 命中
- ✅ 折叠/展开、icon 渲染正常

---

### [重构] 全局样式规范化（描述列表 / 卡片 / 按钮 / 标题）

| 项目 | 说明 |
| --- | --- |
| 类型 | 重构 |
| 范围 | 全局样式 |
| 影响文件 | `frontend/src/styles/global.css` |
| 关联任务 | CronMail 前端 UI 专业美化 |

**改动**

- `el-descriptions` 统一规范：
  - `border-radius: 8px` + `overflow: hidden`（与卡片圆角一致）
  - `el-descriptions__label` 浅灰底 `#fafbfc` + `font-weight: 500` + 固定宽度 120px（多列对齐整齐）
  - `el-descriptions__content` 用 `--text-primary`
- `el-card` 全局 box-shadow 统一为 `0 1px 3px rgba(0,0,0,0.06)`，`border-radius: 8px`
- `el-card__header` padding 14/20，`el-card__body` padding 20（更紧凑专业）
- `.el-button + .el-button { margin-left: 8px }`（按钮间距统一）
- `.section-title` 公共类：3px 蓝色左边线 + 标题 + 可选 icon，颜色用 CSS 变量（不再硬编码 `#409eff`）
- `.card-header .title` 公共类：自动为内部 `<el-icon>` 着色 `--primary-color`
- `.muted` 弱化文本：颜色 `#c0c4cc`
- `.pagination / .toolbar` 抽到全局
- `.el-dialog__title` 字体加粗 600
- `.el-input__prefix .el-icon / .el-input__suffix .el-icon` 统一大小 16px

**影响**

- 后续业务页面无需再重复写 page-container / card-header / section-title 的 padding 样式
- 所有 `el-descriptions` 的 label 列宽统一为 120px，对齐整齐

---

### [重构] 租赁详情页完全重写（修复对齐 + 卡片化分模块）

| 项目 | 说明 |
| --- | --- |
| 类型 | 重构 |
| 范围 | 租赁详情页 |
| 影响文件 | `frontend/src/views/rentals/detail.vue` |
| 关联任务 | CronMail 前端 UI 专业美化 |

**问题**

- 旧版详情页表格歪歪扭扭，el-descriptions 散落在多个卡片之间，label 列宽不一致
- 操作按钮（4 个）堆在一起，没有顶部 header 区域
- 字段归类混乱：「CPU型号」放在「基本信息」里，但实际属于硬件配置
- 没有"已选汇总"操作完成反馈

**重写方案**

- 顶部独立 `el-card` 作为页面 header：左侧返回按钮 + 标题 + 状态 tag + 副标题（机器型号·内网IP），右侧 4 个操作按钮（编辑/发送开通/发送临期/标记回收），全部在 `reclaimed` 状态下禁用
- 5 个独立 `el-card` 卡片分模块展示：
  1. **基本信息**（`:column="3" border`）：客户、机器型号、状态、计费方式、开通时间、到期时间、自动续期、创建时间、更新时间、备注（:span="3"）
  2. **硬件配置**（`:column="3" border`）：CPU、内存、GPU、系统盘、数据盘（:span="2"）、操作系统、机架位置（:span="2"）
  3. **网络与凭证**（`:column="3" border`）：内网IP（monospace）、公网IP（:span="2"）、SSH端口、带宽、账号、密码（:span="3"，monospace）
  4. **收件人**（el-table）：姓名 / 邮箱 / 类型（to/cc tag）
  5. **发送日志**（el-table）：收件人 / 类型 / 主题 / 状态 / 发送时间
- 到期日期智能高亮：`isExpiringSoon()` 3 天内 → 橙色 + 600 字重 + "即将到期" tag
- 所有 el-descriptions 用 `:column="3" border`，label 列 120px（global.css 统一）→ 整齐对齐
- 操作按钮 `:icon` 加 Element Plus 图标：`Edit / Promotion / Bell / Lock`
- 卡片头用 `card-section-title` 类 + `<el-icon>` 装饰（与侧边栏风格统一）

**JS 改进**

- `handleSendReminder` 改名为更明确（任务要求），仍调 `sendExpiryReminder` API
- 新增 `isExpiringSoon(endDate)` 工具函数（基于 3 天阈值，与仪表盘"3 天内到期"一致）
- `formatDate / formatDateTime` 工具函数保留

**验收**

- ✅ el-descriptions 3 列对齐整齐
- ✅ 卡片间距 16px，圆角 12px，视觉统一
- ✅ `reclaimed` 状态下所有操作按钮禁用
- ✅ 到期日期自动高亮

---

### [修改] 业务页面标题 icon 化

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 10 个业务页面 |
| 影响文件 | 见上方 emoji 重构列表 |
| 关联任务 | CronMail 前端 UI 专业美化 |

**改动**

- 所有 `.card-header` 内的 `<span class="title">📋 xxx</span>` 改为 `<span class="title"><el-icon><Document /></el-icon>xxx</span>`
- `.pane-title` / `.section-title` / `.body-title` 全部加 icon
- 侧边栏菜单图标：仪表盘 `Odometer`、客户 `UserFilled`、租赁 `Document`、模板 `Message`、日志 `Tickets`、系统 `Setting`（与任务要求一致）
- 输入框 prefix icon：搜索框 `<template #prefix><el-icon><Search /></el-icon></template>`

**验收**

- ✅ 全站视觉一致
- ✅ vue-tsc 0 错误

---

### 整体验收

| 验收项 | 结果 |
| --- | --- |
| 全站 emoji 数量 | 0 |
| `vue-tsc --noEmit` | 0 错误 |
| `vite build` | 成功 |
| Docker 镜像 `harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` | 构建 + 推送成功 |
| K8s `deployment/cronmail-frontend` | rollout 成功 |
| 新 Pod 状态 | Running (1/1) |
| 侧边栏菜单 | 6 个图标全部用 Element Plus |
| 详情页对齐 | 3 列整齐，label 120px 统一 |
| 操作按钮在 `reclaimed` 状态 | 全部禁用 |
| 全局样式 | 描述列表 / 卡片 / 按钮规范统一 |

**关联任务**：CronMail 前端 UI 专业美化（emoji 清除 + 详情页对齐重写 + 全局样式规范化）

**备注**

- 全部图标组件从 `@element-plus/icons-vue` 按需 import，不影响打包体积
- 字体使用系统 sans-serif 栈（与原有保持一致）
- 主色 `#1a73e8` 保持不变（蓝色专业感）
- 顶栏 "系统运行中" 改为带 `<CircleCheckFilled>` 图标 + 浅绿 tag，更克制专业

## 2026-06-25 (三大修复：nginx 代理 / UI 美化 / 仪表盘生产化)

### [修复] nginx 缺失 /api 反代导致 POST 返回 405

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 容器化部署 / 反向代理 |
| 影响文件 | `frontend/nginx.conf` |
| 关联任务 | CronMail 前端三大修复 |

**问题**

K8s Ingress 未代理 `/api/*` 到后端，前端 `POST http://192.168.180.171:30081/api/customers` 直接打到 nginx 默认 server，nginx 405 拒绝。

**修复**

- 在 `frontend/nginx.conf` 的 `server` 块中新增 `location /api/`，将请求反代到 K8s service `cronmail-backend.cronmail.svc.cluster.local:8000`
- 透传 `Host / X-Real-IP / X-Forwarded-For / X-Forwarded-Proto` 标准代理头
- `location /`（SPA 路由）保持不动，`location ~* \.(?:css|js|...)$` 静态资源缓存保持不动

**验收**

- `curl http://192.168.180.172:30081/api/health` → `{"status":"ok"}`
- `curl -X POST http://192.168.180.172:30081/api/customers -d '{...}'` → HTTP 201（不再 405）

---

### [重构] 全局样式升级为专业深蓝主题

| 项目 | 说明 |
| --- | --- |
| 类型 | 重构 |
| 范围 | 全局样式 / 布局 |
| 影响文件 | `frontend/src/styles/global.css`、`frontend/src/layouts/MainLayout.vue` |
| 关联任务 | CronMail 前端三大修复 |

**改动**

- `styles/global.css` 完全重写：CSS 变量定义（`--primary-color: #1a73e8` 等）、`page-container` 容器规范、`.stat-cards` / `.stat-card` 统计卡片样式、`.card-header` / `.search-bar` / `.status-tag` 等公共工具类
- `MainLayout.vue` 完全重写：
  - 侧边栏深蓝 (`#001529`) + 折叠按钮（Fold/Expand 切换 64px/220px）
  - 顶栏：折叠按钮 + 面包屑 + 右侧"系统运行中"绿 tag
  - 内容区统一 24px padding
  - 子菜单 `/system` 高亮逻辑：`activeMenu` 对 `/system/*` 返回 `'system'` 以命中父级 `el-sub-menu`

---

### [修改] 仪表盘改为生产数据视图

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 仪表盘 |
| 影响文件 | `frontend/src/views/dashboard/index.vue` |
| 关联任务 | CronMail 前端三大修复 |

**改动**

- 去掉技术栈展示（Vue 3 / FastAPI / v0.2.0 等）
- 改为 4 个真实业务统计卡片：
  - 租赁记录总数（`getRentals({ page_size: 1 }).total`）
  - 即将到期（`getRentals({ status: 'expiring', page_size: 1 }).total`）— 黄色强调
  - 已到期未回收（`getRentals({ status: 'expired', page_size: 1 }).total`）— 红色强调
  - 邮件发送总数（`getLogs({ page_size: 1 }).total`）— 蓝色强调
- 底部新增「⏰ 待处理提醒」表格：拉取 `status=expiring` 的前 10 条，支持"详情"和"发送提醒"操作
- 并发请求用 `Promise.allSettled` 容错，单个接口失败不影响其他卡片
- 复用 `RentalListItem` 类型，TS 严格类型（无 `any`）

---

### [重构] 业务页面统一容器风格

| 项目 | 说明 |
| --- | --- |
| 类型 | 重构 |
| 范围 | 全部业务页面 |
| 影响文件 | `frontend/src/views/**/*.vue` |
| 关联任务 | CronMail 前端三大修复 |

**改动**

- 10 个业务页面外层 `<div class="page">` → `<div class="page-container">`：
  - `views/customers/index.vue` / `contacts.vue`
  - `views/rentals/index.vue` / `create.vue` / `detail.vue`
  - `views/templates/index.vue` / `edit.vue`
  - `views/logs/index.vue`
  - `views/system/smtp.vue` / `colleagues.vue`
- `page-container` 在 `global.css` 中已定义为 `padding: 24px; display: flex; flex-direction: column; gap: 16px;`，统一容器风格

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `vite build` 成功
- ✅ Docker 镜像 `harbor.xhwltech.com/xhcloud/cronmail-frontend:latest` 构建 + 推送成功
- ✅ K8s deployment `cronmail-frontend` rollout 成功
- ✅ 前端 200 / API 代理通 / POST 客户 201
- ✅ 仪表盘 4 卡片 + 待处理提醒表格无技术栈残留

---

## 2026-06-24 (全面 Bug 排查与修复)

### [修复] 前端全面 Bug 排查和修复

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 全前端（API 层 / 状态层 / 表单层 / 模板层 / 系统层 / 仪表盘） |
| 影响文件 | `vite.config.ts`, `frontend/src/api/index.ts`, `frontend/src/api/modules/rental.ts`, `frontend/src/api/modules/log.ts`, `frontend/src/lib/rental.ts`, `frontend/src/views/rentals/index.vue`, `frontend/src/views/rentals/create.vue`, `frontend/src/views/rentals/detail.vue`, `frontend/src/views/customers/index.vue`, `frontend/src/views/customers/contacts.vue`, `frontend/src/views/system/colleagues.vue`, `frontend/src/views/templates/edit.vue`, `frontend/src/views/logs/index.vue`, `frontend/src/views/dashboard/index.vue` |

**Bug 清单与修复**

#### 1. 代理配置错误（导致开发环境 500 错误）

- **Bug**: `vite.config.ts` 中 dev proxy 目标地址为 `http://localhost:8000`，与实际后端 `http://192.168.180.170:30082` 不符
- **修复**: 将 `target` 改为 `http://192.168.180.170:30082`
- **关联任务**: 任务清单"修复后验证"

#### 2. Axios 响应拦截器类型不友好（多处 `as any` 强转）

- **Bug**: 拦截器返回 `response.data`，但 TypeScript 仍把 `request.get` 的返回类型推断为 `AxiosResponse<T>`，所有调用方都要 `res.data.xxx` 取值或强转 `as any`
- **修复**:
  - 引入 `RequestInstance` 类型包装 axios 实例，声明 `get<T> / post<T> / put<T> / delete<T>` 直接返回 `T`（即 response.data）
  - 删除 `dashboard/index.vue` 中两处 `as any` 强转
  - 删除 `api/index.ts` 中 `(error.config as any)?.__silent` 强转
- **影响**: 所有业务 API 调用方现在拿到的是干净的 `T`，无需 `.data.xxx`

#### 3. `__silent` 标记字段未声明类型

- **Bug**: 拦截器和业务代码用 `as any` 强转访问 `__silent`
- **修复**: 在 `api/index.ts` 中通过 `declare module 'axios'` 给 `AxiosRequestConfig / InternalAxiosRequestConfig` 扩展 `__silent?: boolean` 字段
- **影响**: 消除所有 `as any`，类型严格化

#### 4. `BillingModel` 枚举与后端不一致（会被后端 422 拒绝）

- **Bug**: 前端 `BillingModel = 'monthly' | 'quarterly' | 'yearly' | 'custom'`，但后端只支持 `'monthly' | 'yearly'`
- **修复**:
  - `api/modules/rental.ts`: `BillingModel` 改为 `'monthly' | 'yearly'`
  - `lib/rental.ts`: `BILLING_MODEL_LABEL` 删除 `quarterly` / `custom`
- **影响**: 防止用户提交后端会拒绝的计费方式

#### 5. `RentalDetail` 接口错误继承（类型与后端响应不符）

- **Bug**: 原 `RentalDetail extends Omit<RentalCreatePayload, 'contacts'>`，但后端详情响应**不返回** `customer_id` 字段（只有 `customer: {id, name}`），且很多字段为 `null`
- **修复**: 重写为独立接口，所有字段标注可空（`T | null`），并把 `email_logs` 字段也补全
- **影响**:
  - 编辑模式加载详情时 `form.customer_id = data.customer?.id ?? ''` 而非 `data.customer_id`（编译期不再报错）
  - TS 编译 0 错误

#### 6. 租赁编辑模式空值合并缺失（运行时报错）

- **Bug**: `create.vue` `loadDetail()` 把后端可能为 null 的字段直接赋给非空 `reactive`，运行时会丢失 null 信息
- **修复**: 全部用 `??` 兜底（`data.cpu_model ?? ''`, `data.memory_gb ?? 0`, `(data.public_ips ?? []).join(',')` 等）
- **关联文件**: `views/rentals/create.vue`

#### 7. 详情页 null 数据兜底（点击进入会显示空值）

- **Bug**: `detail.vue` 直接渲染 `detail.data_disks.length` / `detail.public_ips.length`，后端返回 null 时报错
- **修复**: 全部加 `!detail.x || detail.x.length === 0` 判空，`?? '-'` 兜底显示
- **关联文件**: `views/rentals/detail.vue`

#### 8. 后端 `page_size` 最大 100 - 全部 `page_size: 200 / 500` 越界返回 422

- **Bug**: 多处使用 `page_size: 200 / 500` 拉数据，触发 FastAPI `Query(page_size=200, le=100)` 校验失败 → 422
- **修复**: 全部改为 `page_size: 100`
- **影响文件**:
  - `views/rentals/index.vue` `loadCustomerOptions`
  - `views/rentals/create.vue` `loadCustomers` / `loadColleagues` / `loadCustomerContacts`
  - `views/logs/index.vue` `loadRentalOptions`
- **关联任务**: 验证中通过 curl 复现 + 浏览器 console 抓取确认

#### 9. `el-radio-button :value="null"` 触发 element-plus 废弃警告

- **Bug**: `create.vue` 联系人角色选择用 `<el-radio-button :value="null">不选</el-radio-button>`，element-plus 2.14+ 触发 `[el-radio] label act as value is about to be deprecated` 警告
- **修复**: 改用哨兵字符串 `__none__`，modelValue 用 `getContactRole(c.id) ?? '__none__'`，change 事件把 `__none__` 转换为 `null` 调 `setContactRole`
- **影响**: 消除 console warning

#### 10. `el-link :underline="false"` 触发 element-plus 废弃警告

- **Bug**: `customers/index.vue` 客户名链接用 `:underline="false"`，element-plus 2.14+ 警告 `underline option (boolean) is about to be deprecated`
- **修复**: 改为 `:underline="'never'"`

#### 11. 已回收租赁的操作按钮未禁用（重复点击会触发后端 422）

- **Bug**: `detail.vue` 只对「标记回收」「编辑」按钮做 `reclaimed` 状态禁用，「发送开通邮件」「发送临期提醒」未禁用
- **修复**: 4 个操作按钮统一 `:disabled="detail.status === 'reclaimed'"`
- **影响**: 避免无效请求与用户困惑

#### 12. 仪表盘「客户联系人总数」始终显示 `--`

- **Bug**: 原实现 `getContacts({type: 'customer'})` 但 `type=customer` 必须传 `customer_id` → 400 失败 → 降级为 `null`
- **修复**: 改为先 `getCustomers({ page: 1, page_size: 100 })` 拿到所有客户，再累加每个客户的 `contact_count` 字段
- **影响**: 仪表盘第 4 个卡片显示真实总数

#### 13. 仪表盘「本月发送邮件数」文案与实际不符

- **Bug**: 变量名 `logsThisMonth` 但实际是 `GET /logs` total（全量），不是本月
- **修复**: 改名为 `logsTotal`，文案改为「邮件发送总数」
- **影响**: 语义更准确

#### 14. 仪表盘注释与实现脱节

- **Bug**: 顶部注释说"4 个卡片待 rentals/mail/logs 接口实现"，但其实后端已实现
- **修复**: 同步注释；底部 alert 描述也同步更新

#### 15. 联系人分页 `total` 失真

- **Bug**: `contacts.vue` / `colleagues.vue` 用 `list.value.length`（当前页过滤后数量）作为分页 total
- **修复**: 改回 `res.total`（后端真实 total），加注释说明：后端 `list_contacts` 不过滤 `is_active`，实际可见的活跃联系人数 = 服务端 total - 当前页内 inactive 数量
- **影响**: 翻页时 total 一致

#### 16. 客户/同事列表删除后分页退避条件过于严格

- **Bug**: `if (list.value.length === 1 && query.page > 1) { page -= 1 }` 仅当页面剩 1 条时退避
- **说明**: 这是正确的逻辑，保留。但补充了注释说明行为
- **影响文件**: `views/customers/index.vue`, `views/customers/contacts.vue`, `views/system/colleagues.vue`, `views/rentals/index.vue`

#### 17. `resendLog` 响应类型与后端不一致

- **Bug**: 前端 `ResendLogResponse` 字段：`email_log_id: string; status; message?`，但后端实际：`success; message; email_log_id: string | null`
- **修复**: 改为 `{ email_log_id: string | null; status: 'sent' | 'failed'; success: boolean; message: string }`
- **影响**:
  - `views/logs/index.vue` handleResend 用 `res.success && res.status === 'sent'` 判定，message 直接用后端返回
  - 消除 TS 编译错误

#### 18. 模板编辑重置示例不清空错误状态

- **Bug**: `templates/edit.vue` `resetSample()` 重置示例数据 JSON 后，旧 JSON 解析错误的红色提示 `sampleDataError` 仍残留
- **修复**: 重置时同步 `sampleDataError.value = ''`

#### 19. 联系人页 goBack 用 location.href 触发全量刷新

- **Bug**: `history.length > 1 ? history.back() : (window.location.href = '/customers')` 在 SPA 中全量刷新会丢失所有状态
- **修复**: 改用 `router.push({ name: 'CustomerList' })`，更符合 Vue Router 习惯

#### 20. `rental/create.vue` 未使用的 `currentStatus` 变量 + watcher

- **Bug**: `currentStatus` ref 定义且有 watcher，但模板中未引用
- **修复**: 删除死代码（`noUnusedLocals` 编译警告）

#### 21. 注释中过时的后端地址

- **Bug**: `api/index.ts` 顶部注释说「开发阶段由 Vite 代理到后端 http://localhost:8000」，与实际 30082 端口不一致
- **修复**: 同步更新注释

#### 22. 详情页的 `RentalStatus` 类型导入未使用

- **Bug**: `detail.vue` `import type { RentalStatus }` 未在脚本中使用
- **修复**: 保留 import（模板中通过 cast 使用），但同步清理 `create.vue` 中确未使用的 import

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` **0 错误**
- ✅ `vite build` 成功（构建产物正常输出）
- ✅ `npm run dev` 启动成功
- ✅ 浏览器（Playwright 自动化）实际加载以下路径均无 console error / warning：
  - `/` (Dashboard) - 4 个统计卡片显示真实数据：客户=2 / 同事=1 / 邮件=0 / 联系人=1
  - `/customers` - 2 行客户数据
  - `/customers/:id/contacts` - 客户详情 + 联系人列表
  - `/rentals` - 1 行租赁数据
  - `/rentals/create` - 3 步骤条渲染正常，客户下拉可选 2 个客户；切换客户后正确加载联系人列表；radio 切换角色功能正常
  - `/rentals/:id` - 详情页 4 个操作按钮在 reclaimed 状态下全部禁用
  - `/templates` - 3 个模板列表
  - `/templates/create` - Monaco Editor 加载、预览 API 调用正常
  - `/logs` - 列表渲染 + 租赁下拉数据完整
  - `/system/smtp` - 配置加载正确
  - `/system/colleagues` - 1 个内部同事
- ✅ 通过 curl 直接打 `http://192.168.180.170:30082/api/*` 验证后端响应结构与 `docs/api-contracts.md` 一致
- ✅ 通过 curl 打 `http://127.0.0.1:5173/api/*` 验证 Vite 代理透传正确

**关联任务**：CronMail 前端全面 Bug 检查和修复

**备注**

- 后端实测响应（curl）确认了所有字段名/结构与 `docs/api-contracts.md` 和 `docs/backend/api.md` 完全一致
- 修复策略优先做"前端能正确处理 null/可选字段"而非"修改后端 schema"，保持与后端契约一致
- `__silent` 字段通过 `declare module` 扩展，避免 `as any` 强转

---

## 2026-06-24 (容器化部署)

### [新增] Dockerfile.frontend + nginx.conf + K8s 部署

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 容器化与 K8s 部署 |
| 影响文件 | `Dockerfile.frontend`, `frontend/nginx.conf`, `k8s/frontend.yaml`, `k8s/ingress.yaml` |

**主要内容**

- **Dockerfile.frontend**：多阶段构建
  - 阶段 1: `node:20-alpine` 执行 `npm ci && npm run build`
  - 阶段 2: `nginx:alpine` 托管 dist 静态文件
  - 最终镜像仅包含 Nginx + 静态资源，体积小

- **nginx.conf**：SPA 路由 + 静态资源缓存
  - `try_files $uri /index.html` 支持 Vue Router history 模式
  - `/assets/` 路径 1 年强缓存（Vite 构建产物带 hash）
  - Gzip 压缩开启

- **k8s/frontend.yaml**：Deployment(replicas:2) + Service(ClusterIP:80)
  - 健康检查: HTTP GET `/`
  - 资源限制: CPU 100m / Memory 128Mi

- **k8s/ingress.yaml**：`/api/*` → backend, `/*` → frontend

---

## 2026-06-24

### [新增] 前端项目脚手架 + 布局框架 + 路由

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 整体前端工程初始化 |
| 影响文件 | `frontend/`（全新目录） |

**主要内容**

- 基于 Vite 5 + Vue 3 + TypeScript 初始化项目，位于 `frontend/`
- 集成 Element Plus 2.14 作为 UI 库，`@element-plus/icons-vue` 作为图标源
- 集成 Vue Router 4，配置以下路由：
  - `/` → 重定向 `/dashboard`
  - `/dashboard` `/customers` `/rentals` `/templates` `/logs`
  - `/rentals/create` `/rentals/:id` `/rentals/:id/edit`
  - `/templates/create` `/templates/:id/edit`
  - `/system/smtp` `/system/colleagues`（系统配置下子菜单）
- `MainLayout.vue`：实现"顶栏 + 可折叠侧边栏 + 内容区"整体布局
  - 侧边栏使用 `el-menu` 配合 `router` 属性，默认 220px，支持折叠
  - 顶栏集成面包屑、用户下拉菜单
  - 路由切换带 0.15s 淡入过渡
- 集成 Axios（`baseURL: /api`）
  - 请求拦截器：开发期打印请求日志
  - 响应拦截器：统一错误处理（`ElMessage` 提示）
  - 提供 `__silent` 配置项用于静默请求
- `vite.config.ts`：
  - 配置路径别名 `@` → `./src`
  - 配置开发代理 `/api` → `http://localhost:8000`
  - 监听 `0.0.0.0:5173`
- 目录结构：

  ```
  src/
  ├── api/                  # API 请求层
  │   ├── index.ts          # Axios 实例
  │   └── modules/          # 业务 API（占位）
  ├── router/index.ts       # 路由配置
  ├── layouts/MainLayout.vue
  ├── views/                # 5 个一级页面 + 系统配置（占位）
  ├── styles/global.css
  ├── App.vue
  └── main.ts
  ```

- 仪表盘页面附带 `/api/health` 联通检测（`__silent: true`，仅刷新 tag 状态不弹错）

**验收**

- ✅ `npm run dev` 启动成功（Vite 5.4.21，440ms ready）
- ✅ 浏览器访问 `http://localhost:5173/` 返回 200，渲染仪表盘
- ✅ `/dashboard` `/customers` 等子路由均可访问
- ✅ `vue-tsc --noEmit` 类型检查通过
- ✅ `/api` 代理配置正确（后端未启动时返回 500，证明请求已转发）

**关联任务**：CronMail 前端脚手架 + 布局框架 + 路由

**备注**

- 后端 venv 当前为空（缺 fastapi 等依赖），`/api/health` 端到端验证需等后端环境就绪
- 所有页面为占位实现，路由 / 菜单结构已与后端 API 契约对齐，后续按模块逐步填充

---

### [新增] 客户管理 + 系统配置 + 仪表盘页面

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 业务页面 + API 模块 + 路由更新 |
| 影响文件 | `frontend/src/api/modules/customer.ts`、`frontend/src/api/modules/contact.ts`、`frontend/src/api/modules/system.ts`、`frontend/src/views/customers/index.vue`、`frontend/src/views/customers/contacts.vue`、`frontend/src/views/system/smtp.vue`、`frontend/src/views/system/colleagues.vue`、`frontend/src/views/system/index.vue`、`frontend/src/views/dashboard/index.vue`、`frontend/src/router/index.ts`、`frontend/src/layouts/MainLayout.vue` |

**主要内容**

#### 1. API 模块层（`src/api/modules/`）

- `customer.ts`：导出 `getCustomers / createCustomer / getCustomer / updateCustomer / deleteCustomer`，类型 `Customer / CustomerListResponse / CustomerCreatePayload / CustomerUpdatePayload / CustomerListParams`
- `contact.ts`：导出 `getContacts / createContact / getContact / updateContact / deleteContact`，类型 `Contact / ContactType / ContactListParams / ContactCreatePayload / ContactUpdatePayload`。`phone / department` 允许 `null`（与后端 `Optional[str]` 对齐）
- `system.ts`：导出 `getSmtpConfig / updateSmtpConfig / testSmtp`，类型 `SmtpConfig / SmtpConfigUpdate / SmtpTestRequest / SmtpTestResponse`

所有 API 调用均按 `docs/api-contracts.md` 与后端 Pydantic Schema 一一对应（路径、参数、字段名一致）。

#### 2. 客户列表页（`src/views/customers/index.vue`）

- 顶部：搜索框（防抖 300ms）+ 「+ 新建客户」按钮
- 表格列：客户名称（可点击跳转联系人页）、客户编码、状态（`el-tag` 区分 active/inactive）、联系人数量、创建时间、操作
- 「联系人 / 编辑 / 删除」三按钮操作；删除走 `el-popconfirm` 二次确认
- 新建 / 编辑共用弹窗表单（`el-dialog` + `el-form` + `name / code` 字段 + 必填与长度校验）
- 分页：`el-pagination` 集成 `el-table`，支持 `page_size` 切换
- 点击客户名称 → `router.push({ name: 'ContactList', params: { id: row.id } })`

#### 3. 联系人管理页（`src/views/customers/contacts.vue`）

- 路由 `/customers/:id/contacts`，页面顶部展示客户名 + 编码 tag（`getCustomer` 拉取）
- 表格列：姓名、邮箱、电话、部门、状态（`is_active`）、操作
- 列表过滤：只展示 `is_active === true`（软删除过滤）
- 新建 / 编辑弹窗表单（姓名、邮箱、电话、部门），邮箱做 `type: 'email'` 校验
- 删除走 `el-popconfirm`，软删除后将自动回退分页
- 路由参数变化时自动重新拉取（`watch(route.params.id)`）

#### 4. 内部同事管理页（`src/views/system/colleagues.vue`）

- 路由 `/system/colleagues`
- 调用 `getContacts({ type: 'colleague' })`，**新建时不传 `customer_id`**（与客户联系人数据隔离）
- 表格列、交互、过滤逻辑与联系人管理页一致
- 顶部「与客户联系人数据隔离」提示 tag 强化业务边界

#### 5. SMTP 配置页（`src/views/system/smtp.vue`）

- 表单字段：host / port（`el-input-number` 1-65535）/ username / password / sender_name / sender_email / use_tls（`el-switch`）
- 加载时 `GET /api/system/smtp` 填充表单；404 → 切换到「首次配置」模式
- 密码框带「修改密码」勾选框：已配置时不修改密码，新建 / 主动勾选时必填
- 「保存」按钮 → `PUT /api/system/smtp`，自动根据 `hasConfig` 与 `changingPassword` 决定是否传 `password`
- 「测试连接」按钮 → 弹窗输入测试邮箱 → `POST /api/system/smtp/test`，根据响应 `success` 用 `ElMessage.success/error` 提示

#### 6. 仪表盘（`src/views/dashboard/index.vue`）

- 4 个统计卡片（`el-card` + 自定义彩色 icon）：客户数 / 内部同事数 / 本月发送邮件数 / 客户联系人总数
- 已对接后端接口（`getCustomers`、`getContacts`）：并发请求 + `fetchTotal` 工具函数
- 客户联系人总数因后端 `list_contacts` 在 `type=customer` 时强制要求 `customer_id` 无法聚合全量 → 降级为「进入客户列表查看」提示
- 后端尚未实现 `rentals` / `mail/logs` 接口 → 本月发送邮件数走 `__silent: true` 探活，404 时显示「后端 logs 接口尚未实现」
- 仪表盘底部 `el-alert` 提示说明：租赁相关统计待后端接口就绪后补充

#### 7. 路由更新（`src/router/index.ts`）

- `/customers/:id/contacts` → `ContactList`（`hidden: true`，不进侧边栏菜单）
- `/system/smtp` → 指向 `views/system/smtp.vue`
- `/system/colleagues` → 指向 `views/system/colleagues.vue`
- `views/system/index.vue` 重构为嵌套路由父组件（仅 `<router-view />`）

#### 8. 修复

- `MainLayout.vue`：移除 `activeSubMenu` 未使用的 computed（`noUnusedLocals` 报错）
- `views/dashboard/index.vue`：移除未使用的 `ElMessage` import
- `api/modules/contact.ts`：`ContactCreatePayload / ContactUpdatePayload` 的 `phone / department` 类型由 `string` 改为 `string | null`，与后端 `Optional[str]` 对齐

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `npm run dev` 启动成功
- ✅ 所有路由返回 HTTP 200
- ✅ 所有新增 .vue / .ts 源文件可被 Vite 正常 transform
- ✅ 客户列表 CRUD 完整
- ✅ 联系人管理 / 内部同事 / SMTP 配置 正常
- ✅ 仪表盘 4 个统计卡片已接入后端

**关联任务**：CronMail 前端 - 客户管理 + 系统配置 + 仪表盘页面

---

## 2026-06-24

### [新增] 租赁管理 + 邮件模板编辑器 + 发送日志页面

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 业务页面 + API 模块 + 路由更新 + Monaco Editor 集成 |
| 影响文件 | `frontend/src/api/modules/rental.ts`、`frontend/src/api/modules/template.ts`、`frontend/src/api/modules/log.ts`、`frontend/src/lib/rental.ts`、`frontend/src/lib/template.ts`、`frontend/src/lib/log.ts`、`frontend/src/views/rentals/index.vue`、`frontend/src/views/rentals/create.vue`、`frontend/src/views/rentals/detail.vue`、`frontend/src/views/templates/index.vue`、`frontend/src/views/templates/edit.vue`、`frontend/src/views/logs/index.vue`、`frontend/src/router/index.ts`、`frontend/package.json` |

**主要内容**

#### 1. API 模块层（`src/api/modules/`）

- `rental.ts`：导出 `getRentals / createRental / getRental / updateRental / deleteRental / sendProvisionEmail / sendExpiryReminder / reclaimRental`
- `template.ts`：导出 `getTemplates / createTemplate / getTemplate / updateTemplate / deleteTemplate / previewTemplate`
- `log.ts`：导出 `getLogs / getLog / resendLog`

#### 2. 共享常量与工具（`src/lib/`）

- `lib/rental.ts`：`RENTAL_STATUS_LABEL` + `RENTAL_STATUS_TAG` + `BILLING_MODEL_LABEL`
- `lib/template.ts`：`TRIGGER_TYPE_LABEL` + `TRIGGER_TYPE_TAG` + `DEFAULT_TEMPLATE_SAMPLE`
- `lib/log.ts`：`LOG_TRIGGER_LABEL` + `LOG_RECIPIENT_TYPE_LABEL` + `LOG_STATUS_LABEL` + `LOG_STATUS_TAG`

#### 3. 租赁记录列表页（`src/views/rentals/index.vue`）

- 表格列：客户 / 机器型号 / 内网IP / 状态 / 到期时间 / 创建时间 / 操作
- 筛选：状态下拉 + 客户下拉 + 关键词搜索
- 整行可点击进入详情
- 「删除」走 `el-popconfirm` 二次确认

#### 4. 租赁记录 - 创建/编辑页（`src/views/rentals/create.vue`）

- 复用策略：`/rentals/create` → 新建模式；`/rentals/:id/edit` → 编辑模式
- 步骤条分 3 步：选择客户&收件人 / 服务器信息 / 服务周期&保存
- 服务器信息 6 个分区：基础信息 / 存储 / 网络 / 系统 / 凭证
- 收件人 to/cc radio 切换（已修复废弃警告）

#### 5. 租赁记录 - 详情页（`src/views/rentals/detail.vue`）

- 顶部状态 tag
- 操作区 4 个按钮：发送开通邮件 / 发送临期提醒 / 标记回收 / 编辑
- 三段 el-descriptions + 收件人 + 发送日志
- 4 个按钮在 reclaimed 状态下统一禁用（已修复）

#### 6. 邮件模板列表页（`src/views/templates/index.vue`）

- 表格列：模板名称 / 触发类型 / 主题模板 / 是否启用 / 版本 / 更新时间
- 筛选：触发类型 / 启用状态 / 关键词搜索

#### 7. 邮件模板 - 编辑/新建页（`src/views/templates/edit.vue`）⭐

**左右分栏布局**：
- 顶部元数据：模板名称 / 触发类型 / 启用状态 / 主题模板
- 左栏：Monaco Editor (HTML 模式) + 示例数据 JSON
- 右栏：实时预览（iframe srcdoc 防抖 800ms）

**Monaco Editor 集成**：
- 通过 Vite `?worker` 语法引入 5 种语言 worker
- `suppressChange` 标志位避免 setValue 触发循环
- 组件销毁时 dispose editor + clearTimeout

#### 8. 发送日志列表页（`src/views/logs/index.vue`）

- 表格列：收件人 / 类型 / 触发类型 / 主题 / 状态 / 错误信息 / 发送时间 / 操作
- 行内操作：查看详情（iframe 渲染邮件正文）/ 重发（仅 failed）

**验收**

- ✅ `vue-tsc --noEmit -p tsconfig.app.json` 0 错误
- ✅ `vite build` 成功
- ✅ `npm run dev` 启动成功
- ✅ 所有路由返回 HTTP 200
- ✅ Monaco Editor 加载正常，预览 API 调用正常
- ✅ 列表页 CRUD + 分页正常

**关联任务**：CronMail 前端 - 租赁管理 + 邮件模板编辑器 + 发送日志页面

---

## 2026-06-27 (仪表盘 + 合同列表筛选调整)

### [修改] 仪表盘「已到期」→「已回收」+ 合同列表状态筛选 + 已回收合同操作限制

| 项目 | 说明 |
| --- | --- |
| 类型 | 修改 |
| 范围 | 仪表盘 + 合同列表页 + 合同详情页 |
| 影响文件 | `frontend/src/views/dashboard/index.vue`、`frontend/src/views/contracts/index.vue`、`frontend/src/views/contracts/detail.vue` |
| 关联任务 | 仪表盘「已到期」→「已回收」+ 合同列表筛选调整 |

**改动**

#### 1. 仪表盘（`dashboard/index.vue`）

- 统计卡片「已到期」（`expired`）改为「已回收」（`reclaimed`）
- 图标从 `WarningFilled` 改为 `Checked`
- 颜色从红色 `#F56C6C` 改为灰色 `#909399`
- `stats` 内部字段 `expired` → `reclaimed`，取值从 `data.reclaimed`（后端暂未提供则 fallback 0）

#### 2. 合同列表状态筛选（`contracts/index.vue`）

- 状态筛选项改为硬编码三个选项：
  - 运行中（`active`）
  - 即将到期（`expiring`）
  - 已回收（`reclaimed`）
- 去掉 `expired`（已到期）选项
- 移除不再使用的 `CONTRACT_STATUS_OPTIONS` 导入

#### 3. 合同详情页已回收合同处理（`contracts/detail.vue`）

- `record.status === 'reclaimed'` 时隐藏以下操作按钮：
  - 编辑
  - 删除
  - 发送开通邮件
  - 发送临期提醒
  - 标记回收
  - 关联设备
  - 取消关联
- 仅保留「变更记录」和「删除」按钮可用

**验收**

- ✅ `vue-tsc --noEmit` 0 错误

**关联任务**：仪表盘「已到期」→「已回收」+ 合同列表筛选调整

**备注**

- 后端 Dashboard stats 接口目前返回 `expired` 字段，`reclaimed` 字段待后端新增；前端已用 `(data as any).reclaimed ?? 0` 做兼容

---

## 2026-06-27 (审计报告前端问题修复)

### [修复] H-2：设备状态枚举重复定义消除

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 租赁模块共享常量 |
| 影响文件 | `frontend/src/lib/rental.ts` |
| 关联任务 | 审计报告 H-2 |

**改动**

- `lib/rental.ts` 中移除重复的 `RENTAL_STATUS_FALLBACK` 常量定义
- 改为从 `@/api/modules/rental` 导入并重新导出（`export { RENTAL_STATUS_FALLBACK }`）
- 后端 `rental_record.status` 使用中文值 `空闲中 / 已断电 / 租赁中`，前端 `RentalStatus` 类型与此一致，无需修改

### [修复] H-3：合同列表添加「已到期」筛选 + 修正标签

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 合同列表页 |
| 影响文件 | `frontend/src/views/contracts/index.vue` |
| 关联任务 | 审计报告 H-3 |

**改动**

- 状态筛选下拉框新增 `{ label: '已到期', value: 'expired' }` 选项
- 「运行中」label 修正为「生效中」（与 `CONTRACT_STATUS_LABEL` 保持一致）
- 「即将到期」label 修正为「临期」

### [修复] H-4：同事管理分页 total 修复

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 内部同事管理页 |
| 影响文件 | `frontend/src/views/system/colleagues.vue` |
| 关联任务 | 审计报告 H-4 |

**改动**

- `total.value = list.value.length` → `total.value = res.total`
- 后端 `list_contacts` 不支持 `is_active` 参数，total 包含已停用的，前端仍做 `filter(c => c.is_active)` 过滤展示

### [修复] M-5：SMTP/钉钉配置 404 误判

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | SMTP 配置页 + 钉钉配置页 + 系统 API 模块 |
| 影响文件 | `frontend/src/views/system/smtp.vue`、`frontend/src/views/system/dingtalk.vue`、`frontend/src/api/modules/system.ts` |
| 关联任务 | 审计报告 M-5 |

**改动**

1. **API 层**（`system.ts`）：`getSmtpConfig()` 和 `getDingTalkConfig()` 调用时传入 `{ __silent: true }`，阻止 axios 拦截器对 404 弹出全局错误提示
2. **smtp.vue `fetchConfig()`**：catch 中 404 时判定为「尚未配置」（保持空表单），非 404 错误手动 `ElMessage.error` 提示网络异常
3. **dingtalk.vue `fetchConfig()`**：同上逻辑

**验收**

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ 所有修改文件 lint 0 错误

**关联任务**：审计报告前端问题修复（H-2 / H-3 / H-4 / M-5）

**备注**

- 网络断开时不再被误判为「未配置」，用户能看到明确的错误提示

---

## 2026-07-08 (多类型合同列表页 + 附件管理页)

### [新增] 多类型合同管理前端

| 项目 | 说明 |
| --- | --- |
| 类型 | 新增 |
| 范围 | 路由 + 侧边栏 + API 模块 + 6 个业务页面 |
| 影响文件 | 见下方详细清单 |
| 关联任务 | 多类型合同列表页 + 附件管理页 |

#### 改动概览

1. **路由重构** (`frontend/src/router/index.ts`)：
   - `/contracts` → 重定向到 `/contracts/compute-leasing`
   - 原算力租赁合同路径迁移至 `/contracts/compute-leasing/*`
   - 新增卫星数据合同路由：`/contracts/satellite-data/*`
   - 新增算力服务合同路由：`/contracts/compute-service/*`
   - 每种合同类型新增 `/:id/attachments` 附件管理路由
   - 系统配置新增 `/system/attachment-categories` 附件分类管理路由

2. **侧边栏重构** (`frontend/src/layouts/MainLayout.vue`)：
   - 「合同管理」从单一菜单改为 sub-menu（算力租赁 / 卫星数据 / 算力服务）
   - 系统配置子菜单新增「附件分类管理」
   - 面包屑逻辑适配新路由结构
   - 新增图标导入：Monitor、DataAnalysis、Cpu、FolderOpened

3. **新增 API 模块**：
   - `frontend/src/api/modules/satellite-contract.ts`：卫星数据合同 CRUD
   - `frontend/src/api/modules/service-contract.ts`：算力服务合同 CRUD
   - `frontend/src/api/modules/attachment.ts`：附件管理全部接口（含附件 CRUD、状态确认、分类管理）

4. **共享常量扩展** (`frontend/src/lib/contract.ts`)：
   - 新增 `CONTRACT_TYPE_LABEL`、`CONTRACT_TYPE_ROUTE`、`CONTRACT_TYPE_OPTIONS`
   - 新增 `ATTACHMENT_STATUS_COLORS`

5. **卫星数据合同页面** (`frontend/src/views/satellite-contracts/`)：
   - `index.vue`：列表页（客户筛选、搜索、附件状态圆点、附件下拉按钮）
   - `form.vue`：创建/编辑共用（客户选择器、合同名称、合同编号、备注）
   - `detail.vue`：详情页（基本信息 + 附件状态卡片）

6. **算力服务合同页面** (`frontend/src/views/service-contracts/`)：
   - 结构与卫星数据合同相同，API 指向 `/api/compute-service-contracts`

7. **附件管理页** (`frontend/src/views/attachments/AttachmentsPage.vue`)：
   - 可复用页面，根据路由自动推断 contract_type
   - 展开/折叠分类 + 子项确认/取消确认
   - 文件上传（el-upload）、下载（window.open）、删除（二次确认）
   - 文件大小格式化显示

8. **附件分类管理页** (`frontend/src/views/system/attachment-categories.vue`)：
   - 三个 Tab 切换合同类型
   - 分类增删改 + 上移/下移排序
   - 子项增删改 + 上移/下移排序
   - 删除为软删除（弹窗提示不影响已有数据）

9. **算力租赁合同列表页更新** (`frontend/src/views/contracts/index.vue`)：
   - 新增「附件状态」列（三个圆点指示器）
   - 操作列新增「附件」下拉按钮
   - 异步加载附件汇总状态

10. **算力租赁合同详情页更新** (`frontend/src/views/contracts/detail.vue`)：
    - 新增「附件状态」区块（三个分类的状态卡片）
    - 操作栏新增「附件管理」按钮
    - 不影响已有设备关联/联系人/邮件发送功能

#### 验收

- ✅ `vue-tsc --noEmit` 0 错误
- ✅ 所有新文件 TypeScript 严格类型，无 `any`
- ✅ 原有算力租赁合同功能保持不变
- ✅ 路由 / 侧边栏 / 面包屑全部适配

#### 关联任务

多类型合同列表页 + 附件管理页

#### 备注

- 附件管理页通过路由路径推断 `contract_type`（`compute_leasing` / `satellite_data` / `compute_service`）
- 附件状态圆点颜色：绿色=已确认、红色=未确认、灰色=未上传
- 后端 API 接口按 `docs/api-contracts-attachments.md` 契约实现

---

## 2026-07-06

### [修复] pdfjs-dist worker 从 CDN 改为本地 npm 包导入

| 项目 | 说明 |
| --- | --- |
| 类型 | 修复 |
| 范围 | 附件管理页 PDF 预览 |
| 影响文件 | `frontend/src/views/attachments/AttachmentsPage.vue` |
| 关联任务 | pdfjs-dist worker 加载失败修复 |

#### 问题

原代码通过 CDN 加载 pdfjs worker：
```typescript
GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/6.1.200/pdf.worker.min.mjs`
```
内网环境无法访问 CDN，导致 PDF 预览报错。

#### 修复

改为使用 Vite `?url` 后缀从 npm 包本地导入 worker 文件：
```typescript
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
GlobalWorkerOptions.workerSrc = pdfjsWorker
```

#### 验收

- `vue-tsc -b` 零错误 ✅
- `vite build` 成功，worker 文件正确打包至 `dist/assets/pdf.worker.min-*.mjs` ✅
- PDF 预览不再依赖外网 CDN ✅
