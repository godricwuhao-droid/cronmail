# 通知流程 V2 设计文档

> 日期: 2026-07-01 | 状态: 开发中

---

## 一、现有问题

1. 到期当天 00:00 发的是「回收通知」，但实际回收在次日 01:00，客户提前 23 小时收到「回收」措辞，容易混淆
2. 回收执行后没有发邮件，客户不知道资源已被回收
3. 邮件失败只打日志，没有钉钉告警

---

## 二、新增 trigger_type：`expiry_notice`

| trigger_type | 含义 | 触发时机 | 内容 |
|:--|:--|:--|:--|
| `provision` | 开通通知 | 手动 | 登录信息 |
| `expiry_warning` | 临期提醒 | 到期前 N 天 08:00 | 快到期请续费 |
| 🆕 `expiry_notice` | 到期提醒 | 到期当天 08:00 | 今天到期，今晚回收 |
| `reclaim` | 回收通知 | 回收后立即 | 资源已回收 |

## 三、任务调度调整

| 任务 | 原来 | 改为 |
|:--|:--|:--|
| `check_expired_rentals` | 00:00 发有误导的 reclaim | **08:00 发 expiry_notice** |
| `check_reclaim_expired` | 01:00 静默回收 | **00:01 回收 + 发 reclaim 邮件** |

调度时间都从 system_config 读取，与现有通知时间配置页集成。

## 四、状态机不变

```
active → expiring → expired → reclaimed
          ↑临期提醒     ↑到期提醒    ↑回收通知
```

## 五、邮件失败钉钉告警

在 `send_merged_email_by_contract` 中，当邮件发送失败时，额外推钉钉：

```
⚠️ 邮件发送失败
- 合同编号：HT-2026-0001
- 客户名称：XX公司
- 通知类型：临期提醒
- 收件人：xxx@qq.com
- 失败原因：SMTP 连接超时
```

## 六、测试辅助

新增 `POST /api/system/trigger/{task_name}` 调试接口：
- `trigger_type = 'manual'`，不受幂等检查限制
- 支持 `simulate_date: "2026-06-30"` 参数，模拟指定日期
- 仅开发环境可用（或需 admin 权限）

示例：
```bash
# 模拟 6/30 的到期提醒
curl -X POST /api/system/trigger/check_expired_rentals \
  -d '{"simulate_date": "2026-06-30"}'

# 模拟 7/1 回收
curl -X POST /api/system/trigger/check_reclaim_expired \
  -d '{"simulate_date": "2026-07-01"}'
```
