"""
钉钉机器人消息发送模块

提供：
- 加签（HMAC-SHA256）
- Markdown 消息构建与发送
- 邮件通知后的钉钉推送消息构建
"""
import base64
import hashlib
import hmac
import time
import urllib.parse
from datetime import datetime
from typing import Optional

import requests


# ============================================================
# 加签逻辑
# ============================================================

def _sign_dingtalk(secret: str) -> tuple:
    """
    钉钉加签

    Args:
        secret: 加签密钥

    Returns:
        (timestamp: str, sign: str)
    """
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def _build_url(webhook_url: str, secret: Optional[str]) -> str:
    """
    构建带签名的钉钉 Webhook URL

    Args:
        webhook_url: 原始 webhook URL
        secret: 加签密钥（可选）

    Returns:
        完整 URL（如有 secret 则附带 timestamp 和 sign）
    """
    if secret:
        ts, sign = _sign_dingtalk(secret)
        return f"{webhook_url}&timestamp={ts}&sign={sign}"
    return webhook_url


# ============================================================
# 发送 Markdown 消息
# ============================================================

def send_dingtalk_markdown(
    webhook_url: str,
    secret: Optional[str],
    title: str,
    text: str,
) -> tuple:
    """
    发送钉钉 Markdown 消息

    Args:
        webhook_url: 钉钉机器人 Webhook URL
        secret: 加签密钥（可选）
        title: 消息标题
        text: Markdown 文本内容

    Returns:
        (success: bool, message: str)
    """
    url = _build_url(webhook_url, secret)
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("errcode") == 0:
            return True, "发送成功"
        return False, data.get("errmsg", "未知错误")
    except requests.exceptions.Timeout:
        return False, "钉钉请求超时（10秒）"
    except requests.exceptions.ConnectionError as e:
        return False, f"钉钉连接失败：{_extract_error(e)}"
    except Exception as e:
        return False, f"钉钉发送失败：{_extract_error(e)}"


# ============================================================
# 邮件通知钉钉消息构建
# ============================================================

def build_notification_markdown(
    contract,
    trigger_type: str,
    rental_contexts: list,
    to_emails: list,
) -> tuple:
    """
    构建邮件发送成功后的钉钉通知 Markdown 消息

    Args:
        contract: Contract ORM 实例（含 customer 关联）
        trigger_type: 触发类型 (provision / expiry_warning / reclaim)
        rental_contexts: 设备上下文列表
        to_emails: 收件人邮箱列表

    Returns:
        (title: str, markdown_text: str)
    """
    type_map = {
        "provision": ("开通通知", "#2e7d32"),
        "expiry_warning": ("临期提醒", "#ef6c00"),
        "reclaim": ("回收通知", "#e53935"),
    }
    type_name, color = type_map.get(trigger_type, (trigger_type, "#333333"))
    customer = contract.customer
    customer_name = customer.name if customer else ""
    customer_code = customer.code if customer else ""
    contract_no = contract.contract_no or "-"
    billing_model_map = {"monthly": "月付", "quarterly": "季付", "yearly": "年付"}
    billing_label = billing_model_map.get(contract.billing_model, contract.billing_model or "-")

    # 设备列表
    device_lines = []
    for i, r in enumerate(rental_contexts, 1):
        machine = r.get("machine_model", "-")
        ip = r.get("private_ip", "-")
        rack = r.get("rack_location", "-")
        device_lines.append(
            f"> **{i}. {machine}**\n"
            f"> - IP：{ip}\n"
            f"> - 机架：{rack}\n"
        )
    device_section = "\n".join(device_lines) if device_lines else "> 无设备"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    to_display = ", ".join(to_emails[:3])
    if len(to_emails) > 3:
        to_display += f"...等{len(to_emails)}人"

    # 客户信息行
    customer_info = f"**客户名称**：{customer_name}"
    if customer_code:
        customer_info += f"（{customer_code}）"

    markdown_text = (
        f"## 📧 邮件通知已发送\n"
        f"---\n"
        f"- **通知类型**：<font color={color}>{type_name}</font>\n"
        f"- {customer_info}\n"
        f"- **合同编号**：{contract_no}\n"
        f"- **计费方式**：{billing_label}\n"
        f"- **设备数量**：{len(rental_contexts)} 台\n"
        f"- **收件人**：{to_display}\n"
        f"- **发送时间**：{now_str}\n"
        f"\n"
        f"### 关联设备\n"
        f"{device_section}"
    )

    title = f"📧 {type_name} - {customer_name}"
    return title, markdown_text


def _extract_error(e: Exception) -> str:
    """提取异常信息"""
    return str(e) if str(e) else type(e).__name__
