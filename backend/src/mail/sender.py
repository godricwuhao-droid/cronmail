"""
邮件发送服务
使用 smtplib + email.mime 发送邮件
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List


def send_email(
    host: str,
    port: int,
    username: str,
    password: str,
    sender_name: str,
    sender_email: str,
    to_list: List[str],
    cc_list: List[str],
    subject: str,
    body_html: str,
    encryption: str = "tls",
) -> tuple:
    """
    发送邮件

    Args:
        host: SMTP 服务器地址
        port: SMTP 端口
        username: SMTP 用户名
        password: SMTP 密码（明文）
        sender_name: 发件人显示名称
        sender_email: 发件人邮箱
        to_list: 收件人邮箱列表 (TO)
        cc_list: 抄送邮箱列表 (CC)
        subject: 邮件主题
        body_html: 邮件正文（HTML）
        encryption: 加密方式: tls | starttls | none

    Returns:
        (success: bool, error_msg: str)
    """
    try:
        # 构建 MIME 邮件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")

        # 发件人
        if sender_name:
            msg["From"] = f"{sender_name} <{sender_email}>"
        else:
            msg["From"] = sender_email

        # 收件人
        msg["To"] = ", ".join(to_list) if to_list else ""

        # 抄送
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        # 邮件正文
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        # 所有收件人地址（TO + CC）
        all_recipients = list(to_list)
        if cc_list:
            all_recipients.extend(cc_list)

        # 连接 SMTP 服务器，按加密方式分发
        if encryption == "tls":
            # 端口 465: 直接 SSL 连接
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        elif encryption == "starttls":
            # 端口 587: 先普通连接，再 STARTTLS 升级
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            # 无加密 (端口 25)
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()

        # 登录
        if username and password:
            server.login(username, password)

        # 发送
        server.sendmail(sender_email, all_recipients, msg.as_string())
        server.quit()

        return True, ""

    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP 认证失败：用户名或密码错误 ({_extract_error(e)})"
    except smtplib.SMTPConnectError as e:
        return False, f"SMTP 连接失败：无法连接到 {host}:{port} ({_extract_error(e)})"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"收件人地址被拒绝 ({_extract_error(e)})"
    except smtplib.SMTPSenderRefused as e:
        return False, f"发件人地址被拒绝 ({_extract_error(e)})"
    except smtplib.SMTPDataError as e:
        return False, f"SMTP 数据错误 ({_extract_error(e)})"
    except smtplib.SMTPException as e:
        return False, f"SMTP 错误：{_extract_error(e)}"
    except TimeoutError as e:
        return False, f"连接超时：{host}:{port} ({_extract_error(e)})"
    except Exception as e:
        return False, f"发送失败：{_extract_error(e)}"


def _extract_error(e: Exception) -> str:
    """提取异常信息"""
    return str(e) if str(e) else type(e).__name__
