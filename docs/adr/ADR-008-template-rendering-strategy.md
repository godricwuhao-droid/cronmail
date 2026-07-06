# ADR-008: 模板渲染策略 —— 保持 Jinja2 逻辑模板

## Status
Accepted

## Context
用户提出疑问：是否应该从 Jinja2"聪明模板"（支持 `{% for %}`, `{% if %}` 等逻辑）转向"纯变量模板"（仅 `{{ var }}` 替换）。

关键触发场景：
1. 预览接口报 `'rentals' is undefined` —— 暴露了三处 context 构造不一致的问题
2. 同一客户多台服务器同时到期时，需要在一封邮件中展示设备列表
3. 纯变量方案无法优雅处理不定长数组的展示（IP 列表、磁盘列表等）

## Decision
**保持 Jinja2 模板引擎不变**，理由：

1. 邮件模板变动频率低（开通/临期/回收三类，结构固定），"灵活改展示"不是强需求
2. 纯变量方案处理数组时，必须由后端拼接 HTML，导致展示逻辑散落在 Python 代码中——这是更大的坏味道
3. 当前 bug 是 preview 接口未做 context 包装导致的 **一致性 bug**，不是架构 bug；修复成本极小
4. Jinja2 已有的沙箱模式（SandboxedEnvironment）已在安全层面做了隔离

### 配套约束

为消除 context 不一致问题，强制以下规范：

> **所有渲染路径（预览 / test_send / 手动发送 / 定时合并）必须使用统一的 context 结构：**
> ```python
> {
>     "customer_name": str,
>     "rental_count": int,
>     "rentals": [{单机字段}, ...]
> }
> ```
> 单机场景下 `rentals` 为单元素数组。

### 拒绝的方案
- 纯变量模板（`{{ var }}` only）—— 无法处理不定长数组展示
- 子模板分离（主模板 + 行模板）—— 过度设计，三类邮件不需要这种复杂度
- 后端预渲染 HTML —— HTML 落入 Python 代码中，维护成本高

## Consequences

### 变容易了
- 模板作者可以用 `{% for r in rentals %}` 自由控制设备列表排版
- 不改变现有模板语法，零迁移成本

### 变难了
- 仍需要保证三条渲染路径的 context 结构一致
- 需要在代码审查中关注 context 构建的一致性

### 配套行动
- 修复 preview 接口的 context 包装（见当前 bug 修复）
- 考虑后续抽取统一的 `build_preview_context(sample_data) -> dict` 函数，消除重复

## Reversibility
高 —— 随时可以换用更受限的模板引擎，模板文件本身改动量可控。

## 实现后补充

当前所有渲染路径已统一使用以下 context：

```python
{
    "customer_name": str,       # 客户名称
    "rental_count": int,        # 设备数量
    "rentals": [{               # 设备列表（单机场景为单元素数组）
        "machine_model": str,
        "cpu_model": str,
        "memory_gb": int,
        "gpu_info": str,
        "system_disk_gb": int,
        "data_disks": [...],
        "os_version": str,
        "bandwidth_mbps": int,
        "rack_location": str,
        "private_ip": str,
        "public_ips": [...],
        "ssh_port": int,
        "root_username": str,
        "root_password": str,
        "start_date": str,
        "end_date": str,
        "billing_model": str,
    }, ...]
}
```

回收/到期提醒场景额外注入 `reclaim_time` 字段（回收执行时间）。

前端模板编辑页的默认示例数据为简化单机结构（预览场景仅需演示变量替换，不需要展示 `{% for %}` 循环）。在模板内容中鼓励使用 `{% for r in rentals %}` 实现多设备列表渲染。
