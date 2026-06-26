"""
系统配置模块业务逻辑层
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from sqlalchemy.orm import Session

from src.core.crypto import encrypt_password, decrypt_password
from src.system.models import SmtpConfig, DingTalkConfig
from src.system.schemas import SmtpConfigUpdate


def get_smtp_config(db: Session) -> Optional[SmtpConfig]:
    """获取 SMTP 配置（取第一条记录）"""
    return db.query(SmtpConfig).first()


def upsert_smtp_config(db: Session, data: SmtpConfigUpdate) -> SmtpConfig:
    """
    更新或创建 SMTP 配置
    - 首次不存在则创建
    - 已存在则更新
    - password 传入明文，后端加密存储
    """
    config = db.query(SmtpConfig).first()
    update_data = data.model_dump(exclude_unset=True)

    # 如果传了 password，加密后存储；否则保留原密码
    if "password" in update_data:
        plain_password = update_data.pop("password")
        if plain_password:
            update_data["password_enc"] = encrypt_password(plain_password)

    if config:
        # 更新已存在的配置
        for field, value in update_data.items():
            setattr(config, field, value)
        db.commit()
        db.refresh(config)
    else:
        # 创建新配置
        config = SmtpConfig(**update_data)
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


def test_smtp_connection(config: SmtpConfig, test_email: str) -> tuple[bool, str]:
    """
    测试 SMTP 连接
    发送一封测试邮件到指定地址
    Returns: (success: bool, message: str)
    """
    # 解密密码
    password = decrypt_password(config.password_enc or "")

    # 获取加密方式（兼容旧字段 use_tls）
    encryption = getattr(config, 'encryption', None) or ('tls' if config.use_tls else 'none')

    try:
        # 构造测试邮件
        msg = MIMEMultipart()
        msg["Subject"] = "CronMail SMTP 测试"
        msg["From"] = f"{config.sender_name or ''} <{config.sender_email or config.username}>"
        msg["To"] = test_email

        body = "如果您收到此邮件，说明 SMTP 配置正确。"
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 连接 SMTP 服务器，按加密方式分发
        if encryption == "tls":
            server = smtplib.SMTP_SSL(config.host, config.port, timeout=15)
            server.ehlo()
        elif encryption == "starttls":
            server = smtplib.SMTP(config.host, config.port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(config.host, config.port, timeout=15)
            server.ehlo()

        # 登录（如果有用户名）
        if config.username and password:
            server.login(config.username, password)

        # 发送邮件
        server.sendmail(
            config.sender_email or config.username,
            test_email,
            msg.as_string(),
        )
        server.quit()

        return True, f"测试邮件已发送到 {test_email}"

    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP 认证失败：用户名或密码错误 ({_extract_error(e)})"
    except smtplib.SMTPConnectError as e:
        return False, f"SMTP 连接失败：无法连接到 {config.host}:{config.port} ({_extract_error(e)})"
    except smtplib.SMTPException as e:
        return False, f"SMTP 错误：{_extract_error(e)}"
    except TimeoutError as e:
        return False, f"连接超时：{config.host}:{config.port} ({_extract_error(e)})"
    except Exception as e:
        return False, f"发送失败：{_extract_error(e)}"


# ============================================================
# 钉钉机器人配置
# ============================================================

def get_dingtalk_config(db: Session) -> Optional[DingTalkConfig]:
    """获取钉钉配置（取第一条记录）"""
    return db.query(DingTalkConfig).first()


def upsert_dingtalk_config(db: Session, data: dict) -> DingTalkConfig:
    """
    更新或创建钉钉配置
    - 首次不存在则创建
    - 已存在则更新
    - secret 传 "***" 表示保留原值，传 "" 表示清空，传其他值表示更新
    """
    config = db.query(DingTalkConfig).first()

    # 处理 secret 保留原值逻辑
    if config and data.get("secret") == "***":
        data.pop("secret")  # 不修改 secret

    if config:
        for field, value in data.items():
            setattr(config, field, value)
        db.commit()
        db.refresh(config)
    else:
        config = DingTalkConfig(**data)
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


def test_dingtalk(
    config: Optional[DingTalkConfig] = None,
    test_data: Optional[dict] = None,
) -> tuple[bool, str]:
    """
    测试钉钉连接
    发送一条测试 Markdown 消息到钉钉群

    Args:
        config: 已保存的钉钉配置（可选）
        test_data: 测试数据，可含 webhook_url / secret（可选）

    Returns:
        (success: bool, message: str)
    """
    from src.system.dingtalk import send_dingtalk_markdown

    webhook_url = None
    secret = None

    if test_data:
        webhook_url = test_data.get("webhook_url")
        secret = test_data.get("secret")

    if not webhook_url and config:
        webhook_url = config.webhook_url
        secret = config.secret

    if not webhook_url:
        return False, "未提供 Webhook URL，请先保存配置或传入测试参数"

    title = "CronMail 钉钉测试"
    text = (
        "## ✅ CronMail 钉钉通知测试\n"
        "---\n"
        "如果您看到此消息，说明钉钉机器人配置正确。\n"
        "\n"
        f"> 发送时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return send_dingtalk_markdown(webhook_url, secret, title, text)


def _extract_error(e: Exception) -> str:
    """提取异常信息"""
    return str(e) if str(e) else type(e).__name__
