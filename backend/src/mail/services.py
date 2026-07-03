"""
邮件日志模块业务逻辑层
"""
from typing import Optional

from sqlalchemy.orm import Session

from src.core.crypto import decrypt_password
from src.core.timezone import local_now, local_today
from src.customer.models import Contact
from src.mail.models import EmailLog
from src.mail.renderer import render_template
from src.mail.sender import send_email
from src.rental.models import RentalRecord, rental_contact
from src.system.models import SystemConfig
from src.system.services import get_smtp_config
from src.template.services import get_active_template_by_trigger


def list_logs(
    db: Session,
    rental_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EmailLog], int]:
    """查询邮件日志列表"""
    query = db.query(EmailLog)

    if rental_id:
        query = query.filter(EmailLog.rental_id == rental_id)
    if trigger_type:
        query = query.filter(EmailLog.trigger_type == trigger_type)
    if status:
        query = query.filter(EmailLog.status == status)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(EmailLog.created_at.desc()).offset(offset).limit(page_size).all()
    return items, total


def get_log(db: Session, log_id: str) -> Optional[EmailLog]:
    """根据 ID 获取日志"""
    return db.query(EmailLog).filter(EmailLog.id == log_id).first()


def create_log(
    db: Session,
    rental_id: Optional[str],
    template_id: Optional[str],
    trigger_type: str,
    recipient: str,
    recipient_type: str,
    subject: str,
    body: str,
    status: str = "sent",
    error_msg: Optional[str] = None,
) -> EmailLog:
    """创建邮件日志"""
    log = EmailLog(
        rental_id=rental_id,
        template_id=template_id,
        trigger_type=trigger_type,
        recipient=recipient,
        recipient_type=recipient_type,
        subject=subject,
        body=body,
        status=status,
        error_msg=error_msg,
        sent_at=local_now() if status == "sent" else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_log_status(
    db: Session,
    log: EmailLog,
    status: str,
    error_msg: Optional[str] = None,
) -> EmailLog:
    """更新日志状态"""
    log.status = status
    if error_msg is not None:
        log.error_msg = error_msg
    if status == "sent":
        log.sent_at = local_now()
        log.error_msg = None
    db.commit()
    db.refresh(log)
    return log


def send_merged_email(
    db: Session,
    records: list,
    customer,
    trigger_type: str,
) -> dict:
    """
    按客户合并发送邮件

    同一客户的多台设备合并为一封邮件，使用 rentals 数组变量。

    Args:
        db: 数据库会话
        records: 该客户下本次需要发送的 RentalRecord 列表
        customer: 客户 ORM 实例
        trigger_type: 触发类型 (provision / expiry_warning / expiry_notice / reclaim)

    Returns:
        dict: {"log_ids": [...], "recipient_count": n}
    """
    # 1. 获取活跃模板
    template = get_active_template_by_trigger(db, trigger_type)
    if not template:
        print(f"[send_merged_email] 跳过: 未找到 trigger_type='{trigger_type}' 的活跃模板")
        return {"log_ids": [], "recipient_count": 0}

    # 2. 获取 SMTP 配置
    smtp_config = get_smtp_config(db)
    if not smtp_config:
        print(f"[send_merged_email] 跳过: SMTP 配置不存在 (trigger={trigger_type}, customer={customer.id})")
        return {"log_ids": [], "recipient_count": 0}

    # 3. 收集去重收件人（跨多台设备的 contacts）
    to_emails_set: set[str] = set()
    cc_emails_set: set[str] = set()
    for r in records:
        contacts = db.execute(
            rental_contact.select().where(rental_contact.c.rental_id == r.id)
        ).fetchall()
        for rc in contacts:
            contact = db.query(Contact).filter(Contact.id == rc.contact_id).first()
            if not contact or not contact.is_active:
                continue
            if rc.recipient_type == 'to':
                to_emails_set.add(contact.email)
            else:
                cc_emails_set.add(contact.email)

    if not to_emails_set:
        print(f"[send_merged_email] 跳过: 客户 {customer.name} (id={customer.id}) 没有有效 TO 收件人")
        return {"log_ids": [], "recipient_count": 0}

    to_emails = list(to_emails_set)
    cc_emails = list(cc_emails_set)

    # 4. 构建合并上下文
    today = local_today()
    rental_contexts = []
    for r in records:
        ctx = {
            'machine_model': r.machine_model or '',
            'cpu_model': r.cpu_model or '',
            'memory_gb': r.memory_gb or '',
            'gpu_info': r.gpu_info or '',
            'system_disk': r.system_disk or '',
            'data_disks': r.data_disks or [],
            'os_version': r.os_version or '',
            'bandwidth_mbps': r.bandwidth_mbps or '',
            'rack_location': r.rack_location or '',
            'private_ip': r.private_ip or '',
            'public_ips': r.public_ips or [],
            'ssh_port': r.ssh_port or 22,
            'root_username': r.root_username or 'root',
            'root_password': decrypt_password(r.root_password_enc or ''),
            'start_date': str(r.start_date) if r.start_date else '',
            'end_date': str(r.end_date) if r.end_date else '',
            'billing_model': r.billing_model or 'monthly',
            'days_until_expiry': (r.end_date - today).days if r.end_date else 0,
            'auto_renew': r.auto_renew,
            'remark': r.remark or '',
            'status': r.status or '',
        }
        rental_contexts.append(ctx)

    context = {
        'customer_name': customer.name,
        'rental_count': len(records),
        'rentals': rental_contexts,
    }

    # 5. 渲染模板（subject 不需要签名 HTML）
    rendered_subject = render_template(template.subject_tpl, context)
    rendered_body = render_template(
        template.body_html, context,
        signature_html=template.signature_html,
    )

    # 6. 解密 SMTP 密码
    smtp_password = decrypt_password(smtp_config.password_enc or '')

    # 7. 发送邮件
    success, error_msg = send_email(
        host=smtp_config.host,
        port=smtp_config.port,
        username=smtp_config.username or '',
        password=smtp_password,
        sender_name=smtp_config.sender_name or 'CronMail',
        sender_email=smtp_config.sender_email or smtp_config.username or '',
        to_list=to_emails,
        cc_list=cc_emails,
        subject=rendered_subject,
        body_html=rendered_body,
        encryption=smtp_config.encryption or 'tls',
    )

    status = 'sent' if success else 'failed'
    log_ids = []
    rental_ids = [r.id for r in records]

    # 8. 写 1 条日志代替 N×M 条
    log = EmailLog(
        rental_id=rental_ids[0] if rental_ids else None,
        template_id=template.id,
        trigger_type=trigger_type,
        recipient=', '.join(to_emails),
        recipient_type='to',
        subject=rendered_subject,
        body=rendered_body,
        status=status,
        error_msg=error_msg if not success else None,
        sent_at=local_now() if success else None,
        extra_data={
            "rental_ids": rental_ids,
            "to_emails": to_emails,
            "cc_emails": cc_emails,
        },
    )
    db.add(log)
    db.flush()
    log_ids.append(log.id)

    db.commit()

    if success:
        print(
            f"[send_merged_email] 合并邮件发送成功: customer={customer.name}, "
            f"rentals={len(records)}, to={to_emails}, cc={cc_emails}"
        )
    else:
        print(
            f"[send_merged_email] 合并邮件发送失败: customer={customer.name}, "
            f"rentals={len(records)}, error={error_msg}"
        )

    return {
        "log_ids": log_ids,
        "recipient_count": len(to_emails),
    }


def send_merged_email_by_contract(db: Session, contract, trigger_type: str) -> dict:
    """
    按合同合并发送邮件（新增，替代旧的按 record 列表合并）

    从合同的 contract_rental 和 contract_contact 获取设备和联系人。

    Args:
        db: 数据库会话
        contract: Contract ORM 实例（需已 eager load customer）
        trigger_type: provision / expiry_warning / expiry_notice / reclaim

    Returns:
        {"log_ids": [...], "recipient_count": n}
    """
    from src.contract.services import get_contract_rentals, get_contract_contacts

    # 1. reclaim / expiry_notice 类型幂等检查：今天是否已发送成功（按合同ID过滤）
    if trigger_type in ('reclaim', 'expiry_notice'):
        from datetime import datetime as _dt
        from sqlalchemy import func
        today_start = _dt.combine(local_today(), _dt.min.time())
        existing = db.query(EmailLog).filter(
            EmailLog.trigger_type == trigger_type,
            EmailLog.status == 'sent',
            EmailLog.created_at >= today_start,
            func.json_unquote(func.json_extract(EmailLog.extra_data, '$.contract_id')) == contract.id,
        ).first()
        if existing:
            print(
                f"[send_merged_email_by_contract] 跳过: 合同 {contract.id[:8]} "
                f"今日已发送 {trigger_type} 通知 (log={existing.id[:8]})"
            )
            return {"log_ids": [], "recipient_count": 0}

    # 2. 获取活跃模板
    template = get_active_template_by_trigger(db, trigger_type)
    if not template:
        print(f"[send_merged_email_by_contract] 跳过: 未找到 trigger_type='{trigger_type}' 的活跃模板")
        return {"log_ids": [], "recipient_count": 0}

    # 3. 获取 SMTP 配置
    smtp_config = get_smtp_config(db)
    if not smtp_config:
        print(f"[send_merged_email_by_contract] 跳过: SMTP 配置不存在")
        return {"log_ids": [], "recipient_count": 0}

    # 4. 获取合同关联的设备和联系人
    rentals = get_contract_rentals(db, contract.id)
    contacts = get_contract_contacts(db, contract.id)

    if not rentals:
        print(f"[send_merged_email_by_contract] 跳过: 合同 {contract.id[:8]} 没有关联设备")
        return {"log_ids": [], "recipient_count": 0}

    # 分组联系人
    to_emails = [c["email"] for c in contacts if c["recipient_type"] == "to" and c.get("email")]
    cc_emails = [c["email"] for c in contacts if c["recipient_type"] == "cc" and c.get("email")]

    if not to_emails:
        print(f"[send_merged_email_by_contract] 跳过: 合同 {contract.id[:8]} 没有 TO 收件人")
        return {"log_ids": [], "recipient_count": 0}

    # 5. 构建 rental contexts（从 rental 实际字段构建）
    today = local_today()
    rental_contexts = []
    rental_ids = []
    for r_dict in rentals:
        # 需要从 DB 获取完整 RentalRecord（有加密密码等字段）
        rental = db.query(RentalRecord).filter(RentalRecord.id == r_dict["id"]).first()
        if not rental:
            continue
        ctx = {
            'machine_model': rental.machine_model or '',
            'cpu_model': rental.cpu_model or '',
            'memory_gb': rental.memory_gb or '',
            'gpu_info': rental.gpu_info or '',
            'system_disk': rental.system_disk or '',
            'data_disks': rental.data_disks or [],
            'os_version': rental.os_version or '',
            'bandwidth_mbps': rental.bandwidth_mbps or '',
            'rack_location': rental.rack_location or '',
            'private_ip': rental.private_ip or '',
            'public_ips': rental.public_ips or [],
            'ssh_port': rental.ssh_port or 22,
            'root_username': rental.root_username or 'root',
            'root_password': decrypt_password(rental.root_password_enc or ''),
            'start_date': str(rental.start_date) if rental.start_date else '',
            'end_date': str(contract.end_date) if contract.end_date else '',  # 从合同继承
            'billing_model': contract.billing_model or 'monthly',
            'days_until_expiry': (contract.end_date - today).days if contract.end_date else 0,
            'auto_renew': rental.auto_renew,
            'remark': rental.remark or '',
            'status': rental.status or '',
        }
        rental_contexts.append(ctx)
        rental_ids.append(rental.id)

    context = {
        'customer_name': contract.customer.name if contract.customer else '',
        'rental_count': len(rental_contexts),
        'rentals': rental_contexts,
    }

    # reclaim / expiry_notice 类型附加回收时间
    if trigger_type in ('reclaim', 'expiry_notice'):
        config = db.query(SystemConfig).filter(SystemConfig.key == 'reclaim_time').first()
        context['reclaim_time'] = config.value if config else '22:00'

    # 6. 渲染模板
    rendered_subject = render_template(template.subject_tpl, context)
    rendered_body = render_template(
        template.body_html, context,
        signature_html=template.signature_html,
    )

    # 7. 解密 SMTP 密码
    smtp_password = decrypt_password(smtp_config.password_enc or '')

    # 8. 发送邮件
    success, error_msg = send_email(
        host=smtp_config.host,
        port=smtp_config.port,
        username=smtp_config.username or '',
        password=smtp_password,
        sender_name=smtp_config.sender_name or 'CronMail',
        sender_email=smtp_config.sender_email or smtp_config.username or '',
        to_list=to_emails,
        cc_list=cc_emails,
        subject=rendered_subject,
        body_html=rendered_body,
        encryption=smtp_config.encryption or 'tls',
    )

    status = 'sent' if success else 'failed'
    log_ids = []

    # 9. 写 1 条日志代替 N×M 条
    log = EmailLog(
        rental_id=rental_ids[0] if rental_ids else None,
        template_id=template.id,
        trigger_type=trigger_type,
        recipient=', '.join(to_emails),
        recipient_type='to',
        subject=rendered_subject,
        body=rendered_body,
        status=status,
        error_msg=error_msg if not success else None,
        sent_at=local_now() if success else None,
        extra_data={
            "contract_id": contract.id,
            "rental_ids": rental_ids,
            "to_emails": to_emails,
            "cc_emails": cc_emails,
        },
    )
    db.add(log)
    db.flush()
    log_ids.append(log.id)

    db.commit()

    if success:
        print(f"[send_merged_email_by_contract] 成功: contract={contract.id[:8]}, rentals={len(rental_ids)}")
        # 11. 钉钉通知（邮件发送成功后推送）
        try:
            from src.system.services import get_dingtalk_config as _get_dingtalk
            from src.system.dingtalk import send_dingtalk_markdown, build_notification_markdown

            dt_config = _get_dingtalk(db)
            if dt_config and dt_config.is_active and dt_config.webhook_url:
                title, markdown_text = build_notification_markdown(
                    contract, trigger_type, rental_contexts, to_emails,
                )
                dt_success, dt_msg = send_dingtalk_markdown(
                    dt_config.webhook_url, dt_config.secret, title, markdown_text,
                )
                if dt_success:
                    print(f"[dingtalk] 通知发送成功: contract={contract.id[:8]}")
                else:
                    print(f"[dingtalk] 通知发送失败: {dt_msg}")
        except Exception as e:
            print(f"[dingtalk] 通知发送异常: {e}")
    else:
        print(f"[send_merged_email_by_contract] 失败: contract={contract.id[:8]}, error={error_msg}")
        # 12. 邮件发送失败时，钉钉告警
        try:
            from src.system.services import get_dingtalk_config as _gdc
            from src.system.dingtalk import send_dingtalk_markdown
            dt = _gdc(db)
            if dt and dt.is_active and dt.webhook_url:
                title = f"⚠️ 邮件发送失败 - {contract.customer.name if contract.customer else ''}"
                text = f"""## ⚠️ 邮件发送失败
---
- **合同编号**：{contract.contract_no or '-'}
- **客户名称**：{contract.customer.name if contract.customer else '-'}
- **通知类型**：{trigger_type}
- **收件人**：{', '.join(to_emails[:3])}
- **失败原因**：{error_msg}"""
                send_dingtalk_markdown(dt.webhook_url, dt.secret, title, text)
        except Exception:
            pass

    return {"log_ids": log_ids, "recipient_count": len(to_emails)}
