# 新环境部署指南与遗留事项（资产运营管理平台）

> 编写：Architect · 2026-10-30
> 适用场景：**新服务器直接跑进程（非容器化）**，代码来自 GitHub `platform-asset-ops` 分支（commit `7b08ff8`+）

---

## 1. 项目概览

| 项 | 说明 |
|----|------|
| 前端 | Vue 3 + Vite + Element Plus + TypeScript（`frontend/`） |
| 后端 | Python FastAPI + SQLAlchemy + Celery（`backend/`，入口 `main.py`） |
| 数据库 | MySQL 8.0，独立库 **`asset_ops`** |
| 消息队列 | Redis（Celery broker，**用 db 1**，与其他平台隔离） |
| 附件 | 本地文件系统，根目录由 `UPLOAD_BASE_DIR` 指定 |
| 功能 | 设备（租赁记录）管理 / 机房-排-机柜-机架 层级 / U 位点阵图 / 合同 / 数据报表 |

## 2. 获取代码

```bash
git clone git@github.com:godricwuhao-droid/cronmail.git
cd cronmail && git checkout platform-asset-ops
# 确认在 7b08ff8 或更新：git log --oneline -1
```

## 3. 环境依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+（与旧环境一致） | 后端 |
| MySQL | 8.0 | 建库 `asset_ops` |
| Redis | 任意新版 | 仅 Celery broker，**必须用 db 1**（若与 cronmail 平台共用实例） |
| Node.js | 20+ | 前端构建 |
| nginx | 任意 | 前端静态 + API 反向代理 |
| pm2 或 systemd | 建议 pm2 | 进程守护（下面给了 pm2 配置） |
| SMTP 服务器 | 可选 | 不配置则邮件功能不可用，其余功能不受影响 |

## 4. 配置项清单（旧环境值 + 新环境改法）

| 变量 | 旧环境值 | 新环境 |
|------|---------|--------|
| `DATABASE_URL` | `mysql+pymysql://root:Qwert7891@mysql-master.cronmail.svc.cluster.local:3306/asset_ops` | 改 host 为新 MySQL 地址（或先远程连旧库 `192.168.180.171:30308`，见 §5.1） |
| `CELERY_BROKER_URL` | `redis://:Qwert7891@redis.cronmail.svc.cluster.local:6379/1` | 改 host；密码/密码位按新 Redis；**db 1 保持** |
| `UPLOAD_BASE_DIR` | `/app/uploads`（容器内路径，宿主机 PV 为 `/cronmail/asset-ops`） | 新服务器的附件目录绝对路径，如 `/data/cronmail/uploads` |
| `MAIL_ENCRYPTION_KEY` | `Af408K9-xM9yzcCcUHPpTC33TZjilWMmlkrqmjLjhZs=` | **必须沿用旧值**（设备 root 密码用它加密存储，换了旧数据解不开） |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_SENDER_EMAIL` | 旧环境为空（未启用） | 需要邮件再配 |
| `APP_TITLE` / `APP_VERSION` / `DEBUG` | `Asset Ops API` / `0.1.0` / `false` | 不变 |

> 完整变量来源：`k8s/asset-ops/configmap.yaml` + `secret.yaml`（容器用 envFrom 注入，直接跑就 export 或用 pm2 的 env）。

## 5. 数据迁移（代码之外的两样东西）

### 5.1 数据库 `asset_ops`

**方案 A：远程连旧库（过渡最快）**
- 新 MySQL 不建库，`DATABASE_URL` 直接指向旧库：`mysql+pymysql://root:Qwert7891@192.168.180.171:30308/asset_ops`
- 前提：新服务器能通 `192.168.180.171:30308`；MySQL root 账号允许新来源 IP（必要时 `GRANT`）
- ⚠️ 过渡态：旧机器不挂则服务不挂，最终仍需切到本地库

**方案 B：dump + restore（彻底）**
```bash
# 旧服务器导出（资产平台全量，含 排/机柜/机架/设备/合同/附件索引）
mysqldump -h 192.168.180.171 -P 30308 -uroot -pQwert7891 \
  --single-transaction --routines asset_ops > asset_ops_$(date +%F).sql
# 新服务器
mysql -u root -p < asset_ops_*.sql   # 先 CREATE DATABASE asset_ops;
```
- 表结构兜底：`docs/backend/database.md` 有全部 DDL（含各 ADR 追加语句），空库可按它从零建
- 已执行过的 DDL 关键项（新库若从零建必须包含）：
  - `rack.power_on`（ADR-023）——**后被 ADR-026 DROP**，新机架上不存在该列，勿加
  - `rack_row` / `cabinet` 表 + `rack.cabinet_id`（ADR-026）
  - `rental_record.rack_id` / `u_position` / `u_size`（ADR-022/028）

### 5.2 附件文件（必须物理搬迁，不能远程）

```bash
# 旧服务器（PV 宿主机路径）
tar czf asset-ops-attachments.tgz -C /cronmail asset-ops
# 新服务器：解压到 UPLOAD_BASE_DIR 指向的路径
mkdir -p /data/cronmail/uploads && tar xzf asset-ops-attachments.tgz -C /data/cronmail/uploads
```
> 附件在库里的 `file_path` 存的是相对/绝对路径，若 ADR-020 迁移后存的是绝对路径，注意新路径一致性（详见 `docs/backend/changelog.md` ADR-020 段落）。

## 6. 直接跑（非容器）部署步骤

### 6.1 后端（4 个进程：api + worker + beat，建议 pm2）

```bash
cd cronmail/backend
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

`pm2.asset-ops.ecosystem.js`（示例）：
```js
module.exports = {
  apps: [
    { name: 'asset-ops-api',
      cwd: '/data/cronmail/backend',
      script: './venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000',
      env: { ...ENV } },
    { name: 'asset-ops-worker',
      cwd: '/data/cronmail/backend',
      script: './venv/bin/celery',
      args: '-A src.scheduler.celery_app worker --loglevel=info',
      env: { ...ENV } },
    { name: 'asset-ops-beat',
      cwd: '/data/cronmail/backend',
      script: './venv/bin/celery',
      args: '-A src.scheduler.celery_app beat --loglevel=info',
      env: { ...ENV } },
  ],
}
// ENV = { DATABASE_URL, CELERY_BROKER_URL, UPLOAD_BASE_DIR,
//         MAIL_ENCRYPTION_KEY, APP_TITLE, APP_VERSION, DEBUG }
pm2 start pm2.asset-ops.ecosystem.js && pm2 save
```

> 端口 8000 可按需改；`uvicorn` 生产建议 `--workers 2`（注意：beat 必须单实例）。

### 6.2 前端（build + nginx）

```bash
cd cronmail/frontend
npm install
npm run build        # = vue-tsc -b && vite build，产物在 dist/
```

nginx 站点配置（以 `frontend/nginx.asset-ops.conf` 为模板改两处）：
- `root` 指向前端 `dist/`
- `location /api` 反代 `proxy_pass http://127.0.0.1:8000;`（原容器版指向 svc 名）
- `location /uploads`（或附件访问路径，按 nginx.asset-ops.conf 原样保留）→ `UPLOAD_BASE_DIR`
- SPA fallback：`try_files $uri /index.html;`

> **不要**在新服务器长期跑 `vite dev`（旧服务器教训：dev server 的文件监听/按需编译对同机其他服务有干扰；`npm run preview` 可临时用）。

### 6.3 验证清单

```bash
curl http://<新IP>:8000/docs                          # 后端 200
curl http://<新IP>:8000/api/rentals?limit=1           # 设备数据在
curl http://<新IP>:8000/api/machine-rooms/1/point-map # 层级数据（排/机柜/机架/u_cells）
# 浏览器：前端页 登录 → 机房管理 → 雅安机房 → 点位图（4 排 31 柜）→ 点设备 → 附件可下载
pm2 status   # 3 进程 online
```

## 7. 遗留事项（新环境稳定后逐项处理）

### P1 — 点位图交互缺口（一批小改，纯前端+1 个后端参数可选）
ADR-029 排查发现、已裁决方案但**尚未实施**（当时下发任务失败）：
1. **"放入设备"对话框看不到部分未上架设备**（核心缺口，数据现状触发）：
   对话框数据源 = `warehoused=true`（`machine_room_id IS NULL`）。当前有 **18 台设备"已归属雅安机房但未入柜"**（machine_room_id 有、rack_id 空），它们**不在对话框里**，也无法从点位图直接上架，只能逐台去设备编辑表单选机柜/U 位。
   → 建议（待正式裁决）：对话框数据源改为"**未占 U 位**"（`u_position IS NULL`），一次覆盖 仓库/未入柜/未定位 三种状态；同步评估 `warehoused` 语义（ADR-029 排查 #1 的 A/B 选项）
2. unlocated（已定架未定位）设备在点位图无"指定 U 位"快捷入口
3. 删机柜确认文案（"一并删除"）与后端语义（有机架 409 拒绝，不级联）矛盾
4. 放入设备 400/409 后对话框与点位图不刷新（预校验可能基于旧数据）
5. 放入设备对话框"当前位置"列恒为 —（warehoused 数据必无机房），冗余列
6. 设备列表拉取 page_size=100 截断（>100 台仓库设备时）
7. ⋯ 菜单断电/通电无防连点 loading；断电机柜上架无提示灰字；机房详情页返回固定跳列表（应用 back()）

### P2 — 功能缺口
8. **"故障"状态未成为正式枚举**：后端 status 枚举 = 空闲中/已断电/租赁中；点位图橙色（故障）样式已就位，但表单/列表下拉无"故障"选项（现在改色只能改库）
9. ADR-024 已知限制：设备列表"机柜/机架位置"搜索只命中存量 `rack_location` 文本，新结构化数据（rack_name/U位）不可搜

### P3 — 清理/运维
10. 仓库根目录两个临时文件未提交：`pm1.yaml`（playwright 快照）、`pointmap-4color.png`（截图）——可删
11. 存量设备 `rack_location` 自由文本列保留在库中（展示兜底用），P1-1 落地后可评估废弃
12. **旧环境（192.168.180.171）下线顺序**：新环境验证通过 → k8s 缩容 `asset-ops` ns（`kubectl scale deploy --replicas=0 -n asset-ops`，前端/后端 4 个）→ 观察一周 → 清理 namespace；**旧机上 core-holdings vite(5173)、director-flow vite(30001) 是独立生产服务，下线 asset-ops 时勿动**
13. 建议新环境给 mysqldump 加每日 cron（数据量小，全量即可）

## 8. 旧环境信息备忘（迁移期有效）

| 项 | 值 |
|----|-----|
| 前端 / 后端 | `http://192.168.180.171:30083` / `:30084`（K8s ns `asset-ops`） |
| MySQL | NodePort `192.168.180.171:30308`，`root` / `Qwert7891`，库 `asset_ops` |
| 附件 PV 宿主机路径 | `/cronmail/asset-ops` |
| Harbor 镜像 | `harbor.xhwltech.com/xhcloud/asset-ops-{frontend,backend}:latest`（直接跑则不需要） |
| 构建环境坑位（仅容器构建需要） | `/usr/bin/docker` 真 CLI + 代理 `192.168.180.251:7890` |

## 9. 文档索引

- 架构决策：`docs/adr/ADR-019~029`（019 独立部署 / 020 附件隔离 / 021 机房模块 / 022 U位 / 023~027 点位图演进 / 028 多U / 029 业务逻辑）
- 接口文档：`docs/backend/api.md`；数据库：`docs/backend/database.md`（含全部 DDL）
- 变更日志：`docs/backend/changelog.md`、`docs/frontend/changelog.md`
