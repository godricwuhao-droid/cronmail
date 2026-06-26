# ADR-007: 容器化与 Kubernetes 部署方案

## Status
Accepted

## Context
项目需要在 Kubernetes 集群上部署运行，需要提供完整的 Dockerfile 和 K8s YAML 文件。涉及 3 个进程（API 服务、Celery Worker、Celery Beat）和 1 个前端静态资源服务。

## Decision

### 镜像策略

| 镜像 | 基础镜像 | 构建方式 | 说明 |
|------|---------|---------|------|
| `cronmail-backend` | `python:3.12-slim` | 单阶段，pip install | 同一镜像，不同 command 启动不同进程 |
| `cronmail-frontend` | `node:20-alpine` → `nginx:alpine` | 多阶段构建 | 先 npm build，产物拷到 nginx |

**同一后端镜像，多进程模式**：

```
镜像: cronmail-backend:latest
├── API 服务    → command: uvicorn main:app --host 0.0.0.0 --port 8000
├── Celery Worker → command: celery -A scheduler.tasks worker
└── Celery Beat  → command: celery -A scheduler.tasks beat
```

三个 Deployment 使用同一个镜像，通过 `command` 区分。好处：
- 一次构建，多处使用
- 代码一致性有保证
- 镜像仓库只需管理一个 tag

### K8s 资源清单

```
cronmail/
├── Dockerfile.backend          # 后端镜像
├── Dockerfile.frontend         # 前端镜像（多阶段）
└── k8s/
    ├── namespace.yaml          # cronmail 命名空间
    ├── configmap.yaml          # 非敏感配置
    ├── secret.yaml             # 敏感配置（DB密码、加密密钥、SMTP密码）
    ├── backend-api.yaml        # Deployment + Service (API)
    ├── backend-worker.yaml     # Deployment (Celery Worker)
    ├── backend-beat.yaml       # Deployment (Celery Beat, replicas=1)
    ├── frontend.yaml           # Deployment + Service (Nginx)
    └── ingress.yaml            # 对外暴露
```

### 部署拓扑

```
                    ┌──────────────────┐
                    │    Ingress        │
                    │  /api/* → backend │
                    │  /*     → frontend│
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              │               ▼
    ┌─────────────┐          │     ┌──────────────┐
    │ Service      │          │     │ Service       │
    │ backend:8000 │          │     │ frontend:80   │
    └──────┬───────┘          │     └──────┬───────┘
           │                  │            │
    ┌──────▼───────┐          │   ┌────────▼───────┐
    │ Deployment   │          │   │ Deployment      │
    │ backend-api  │          │   │ frontend        │
    │ replicas: 2  │          │   │ replicas: 2     │
    └──────────────┘          │   └────────────────┘
                              │
    ┌──────────────┐          │
    │ Deployment   │          │
    │ backend-beat │          │
    │ replicas: 1  │(单副本)   │
    └──────────────┘          │
                              │
    ┌──────────────┐          │
    │ Deployment   │          │
    │backend-worker│          │
    │ replicas: 1  │          │
    └──────────────┘          │
                              │
                   ┌──────────▼──────────┐
                   │   External Services  │
                   │   MySQL + Redis      │
                   │   (用户提供，集群外)  │
                   └─────────────────────┘
```

### 关键部署约束

1. **Celery Beat 单副本**：必须 `replicas: 1`，多副本会导致定时任务重复执行
2. **MySQL/Redis 外部化**：数据库和 Redis 由用户提供，不在 K8s 中管理，通过 ConfigMap/Secret 配置连接地址
3. **健康检查**：
   - API: HTTP GET `/api/health`
   - Worker/Beat: 进程存活检查（liveness command）
4. **Ingress 路由**：
   - `/api/*` → backend Service:8000
   - `/*` → frontend Service:80

### Dockerfile 要点

**后端 Dockerfile.backend**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
# 默认启动 API，可通过 command 覆盖
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**前端 Dockerfile.frontend**（多阶段）:
```dockerfile
# 阶段 1: 构建
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# 阶段 2: 运行
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
```

## Consequences

### 变得容易
- 同一后端镜像管理简单，三个进程代码一致性有保证
- 多阶段前端构建镜像体积小（最终镜像仅 Nginx + 静态文件）
- 水平扩展只需改 replicas

### 变得困难
- Beat 单副本限制了高可用（可通过后续引入分布式锁解决）
- MySQL/Redis 外部化意味着需要保证网络可达性
- 首次部署需要创建 namespace、configmap、secret、deployment 等多个资源

### 可逆性等级：高
- K8s 部署可随时改为 Docker Compose 单机部署（去掉 ingress，加 docker-compose.yml）
- 镜像构建方式不变
