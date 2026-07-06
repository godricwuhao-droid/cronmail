# ADR-006: 服务器密码存储策略

## Status
Accepted

## Context
租赁记录中包含服务器 root 密码，需要在两个场景使用：
1. 发送开通邮件时，将密码明文展示给客户
2. 数据库中安全存储

这构成矛盾：安全存储要求不可逆（哈希），但业务要求可逆（邮件明文展示）。

## Decision

采用 **Fernet 对称加密（AES-128-CBC + HMAC-SHA256）可逆加密存储**。

### 方案对比

| 对比项 | Fernet 对称加密 | bcrypt 哈希 | 明文存储 |
|--------|-----------------|-------------|---------|
| 邮件中可展示 | ✅ 解密即可 | ❌ 不可逆 | ✅ 但极不安全 |
| 数据库泄露后 | ⚠️ 密钥未泄露则安全 | ✅ 安全 | ❌ 全部暴露 |
| 实现复杂度 | 中 | 低 | 极低 |
| 合规性 | ✅ 可接受（密钥分离管理） | ✅ 最佳 | ❌ 不合规 |

### 实现方案

```python
# core/crypto.py
from cryptography.fernet import Fernet
import os

# 密钥从环境变量注入，不写死在代码中
ENCRYPTION_KEY = os.environ.get("MAIL_ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_password(plaintext: str) -> str:
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_password(ciphertext: str) -> str:
    return cipher.decrypt(ciphertext.encode()).decode()
```

### 密钥管理

- 密钥通过环境变量 `MAIL_ENCRYPTION_KEY` 注入
- 生产和开发环境使用不同密钥
- 密钥生成命令：`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- 密钥备份和轮换策略单独文档记录

### 数据流

```
管理员创建租赁记录、填 root 密码
  → 前端传入明文密码
  → 后端 AES-256-GCM 加密
  → 数据库存 `root_password_enc`（密文）

管理员点击「发送开通邮件」
  → 后端读取 rental record
  → 解密 root_password_enc → 明文
  → 注入 Jinja2 模板变量
  → 渲染邮件 → SMTP 发送
```

## Consequences

### 变得容易
- 邮件中可以展示服务器密码，提升客户体验
- 数据库层面看不到明文，满足基本安全要求

### 变得困难
- 密钥泄露 = 所有密码暴露，需要严格的密钥管理
- 密钥轮换需要重新加密所有已有记录
- 不能使用标准的密码哈希库（如 passlib）

### 风险缓解措施

1. 访问日志：记录每次解密操作（谁、何时、解密了哪条记录的密码）
2. 密钥与代码分离：密钥不提交到 Git 仓库，通过 CI/CD 或 K8s Secret 注入
3. 定期轮换：建议每季度轮换密钥，轮换时批量重新加密

### 可逆性等级：低
- 一旦选定加密方案，历史数据已用旧密钥加密，更换哈希方案意味着放弃邮件明文展示能力
- 如需升级，建议策略：新记录用新方案，旧记录保持兼容直到自然淘汰
