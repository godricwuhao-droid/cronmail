# ADR-018: LLM 配置动态化（系统配置页管理）

## Status
Accepted — 后端 API + 前端 UI + 动态读取 全部完成

## Context

合同智能解析依赖两组 LLM 服务（OCR 视觉模型 + Extract 文本模型），当前配置硬编码在 `backend/src/core/config.py` 环境变量中，修改需重新部署。业务方需要在系统配置页面直接管理这些参数，保存后即时生效。

## Decision

### 1. 存储方案

复用 `SystemConfig` 键值表，新增 6 个 key：

| Key | 说明 | 默认值（环境变量 fallback） |
|-----|------|---------------------------|
| `llm_base_url` | OCR 视觉模型 API 地址 | `http://192.168.180.67:8080/v1` |
| `llm_api_key` | OCR 视觉模型 API Key | `not-needed` |
| `llm_model` | OCR 视觉模型名 | `Qwen3.6-27B` |
| `llm_base_url_extract` | Extract 文本模型 API 地址 | `http://api.opearlai.com:30096/v1` |
| `llm_api_key_extract` | Extract 文本模型 API Key | `sk-tArrgRR2_tqUGYoU_Glakw` |
| `llm_model_extract` | Extract 文本模型名 | `DeepSeek-V4-Flash` |

### 2. API 端点

- `GET /api/system/llm-config` — 返回 6 个字段，api_key 脱敏为 `***`（DB 有值）或 `""`（DB 无值）
- `PUT /api/system/llm-config` — 批量 upsert，api_key 传 `***` 表示保留原值，传 `""` 表示清空

路由定义在 `/config/{key}` 之前，避免路径冲突。

### 3. 动态读取策略

`contract_parser/services.py` 新增 `_get_llm_config()` 辅助函数：
- 每次创建 OpenAI client 前调用
- 先取环境变量默认值，再用 DB 值覆盖
- 5 处 OpenAI client 创建点全部改为动态读取
- 无需重启，保存后下次解析自动生效

### 4. 前端 UI

系统配置页（`/system/config`）新增「智能解析模型配置」分区：
- 两组：OCR 视觉模型（阶段1）+ Extract 文本模型（阶段2）
- API Key 字段使用 `show-password`
- 保存按钮统一提交所有配置

## Consequences

### 变容易了
- 切换模型/地址无需重新部署
- 两组模型独立配置，可分别指向不同服务
- 环境变量作为 fallback 始终保留，DB 无值时行为不变

### 变难了
- 每次解析多一次 DB 查询（可忽略，解析本身耗时秒级）
- api_key 存储为明文（与 SMTP 密码不同，SMTP 用 Fernet 加密；LLM key 风险较低，暂不加密）

### 可逆性
🟢 **高** — 纯新增配置项，环境变量作为 fallback 始终保留。如需回滚，删除 SystemConfig 表中 6 条记录即可恢复环境变量行为。
