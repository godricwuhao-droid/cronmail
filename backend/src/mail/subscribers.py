"""
邮件事件订阅者
监听 blinker 租赁事件，自动发送相应邮件
"""
from src.core.database import SessionLocal
from src.core.crypto import decrypt_password
from src.mail.renderer import render_template, RenderError
from src.mail.sender import send_email
from src.mail.services import create_log
from src.rental.events import (
    rental_provisioned,
    rental_expiring,
    rental_expired,
    rental_reclaimed,
)
from src.rental.services import get_rental_contacts, build_rental_context
from src.template.services import get_active_template_by_trigger
from src.system.services import get_smtp_config


def _send_email_for_rental(rental_record, trigger_type: str):
    """
    通用的「根据租赁记录发送邮件」逻辑
    由事件订阅者调用，自行创建 db session

    Args:
        rental_record: RentalRecord ORM 实例
        trigger_type: provision / expiry_warning / reclaim
    """
    db = SessionLocal()
    try:
        # 获取 SMTP 配置
        smtp_config = get_smtp_config(db)
        if not smtp_config:
            print(f"[subscribers] 跳过: SMTP 配置不存在 (trigger={trigger_type}, rental={rental_record.id})")
            return

        # 获取模板
        template = get_active_template_by_trigger(db, trigger_type)
        if not template:
            print(f"[subscribers] 跳过: 未找到 trigger_type='{trigger_type}' 的活跃模板")
            return

        # 构建上下文
        context = build_rental_context(db, rental_record)

        # 渲染模板
        try:
            subject = render_template(template.subject_tpl, context)
            body_html = render_template(template.body_html, context, signature_html=template.signature_html)
        except RenderError as e:
            print(f"[subscribers] 模板渲染失败: {e} (trigger={trigger_type}, rental={rental_record.id})")
            return

        # 获取联系人
        contacts = get_rental_contacts(db, rental_record.id)
        if not contacts:
            print(f"[subscribers] 跳过: 租赁记录 {rental_record.id} 没有关联联系人")
            return

        # 分组 TO / CC
        to_contacts = [c for c in contacts if c["recipient_type"] == "to"]
        cc_contacts = [c for c in contacts if c["recipient_type"] == "cc"]

        # 解密 SMTP 密码
        smtp_password = decrypt_password(smtp_config.password_enc or "")

        # 发送 TO 收件人（每个 TO 收件人单独发一封，CC 放在一起）
        if to_contacts:
            for to_c in to_contacts:
                to_list = [to_c["email"]]
                cc_list = [c["email"] for c in cc_contacts]

                success, error_msg = send_email(
                    host=smtp_config.host,
                    port=smtp_config.port,
                    username=smtp_config.username or "",
                    password=smtp_password,
                    sender_name=smtp_config.sender_name or "CronMail",
                    sender_email=smtp_config.sender_email or smtp_config.username or "",
                    to_list=to_list,
                    cc_list=cc_list,
                    subject=subject,
                    body_html=body_html,
                    encryption=smtp_config.encryption or "tls",
                )

                create_log(
                    db=db,
                    rental_id=rental_record.id,
                    template_id=template.id,
                    trigger_type=trigger_type,
                    recipient=to_c["email"],
                    recipient_type="to",
                    subject=subject,
                    body=body_html,
                    status="sent" if success else "failed",
                    error_msg=error_msg if not success else None,
                )

        # 如果只有 CC 没有 TO
        if not to_contacts and cc_contacts:
            for cc_c in cc_contacts:
                to_list = [cc_c["email"]]
                cc_list = []

                success, error_msg = send_email(
                    host=smtp_config.host,
                    port=smtp_config.port,
                    username=smtp_config.username or "",
                    password=smtp_password,
                    sender_name=smtp_config.sender_name or "CronMail",
                    sender_email=smtp_config.sender_email or smtp_config.username or "",
                    to_list=to_list,
                    cc_list=cc_list,
                    subject=subject,
                    body_html=body_html,
                    encryption=smtp_config.encryption or "tls",
                )

                create_log(
                    db=db,
                    rental_id=rental_record.id,
                    template_id=template.id,
                    trigger_type=trigger_type,
                    recipient=cc_c["email"],
                    recipient_type="cc",
                    subject=subject,
                    body=body_html,
                    status="sent" if success else "failed",
                    error_msg=error_msg if not success else None,
                )

    except Exception as e:
        print(f"[subscribers] 发送邮件异常: {e} (trigger={trigger_type}, rental={rental_record.id})")
    finally:
        db.close()


@rental_provisioned.connect
def on_rental_provisioned(sender, **kwargs):
    """监听到开通事件 → 发送开通邮件"""
    rental_record = kwargs.get('rental_record')
    if rental_record is None:
        return
    print(f"[subscribers] 收到 rental.provisioned 事件: rental={rental_record.id}")
    _send_email_for_rental(rental_record, trigger_type="provision")


@rental_expiring.connect
def on_rental_expiring(sender, **kwargs):
    """监听到临期事件 → 发送提醒邮件"""
    rental_record = kwargs.get('rental_record')
    if rental_record is None:
        return
    print(f"[subscribers] 收到 rental.expiring 事件: rental={rental_record.id}")
    _send_email_for_rental(rental_record, trigger_type="expiry_warning")


@rental_expired.connect
def on_rental_expired(sender, **kwargs):
    """监听到到期事件 → 发送回收邮件"""
    rental_record = kwargs.get('rental_record')
    if rental_record is None:
        return
    print(f"[subscribers] 收到 rental.expired 事件: rental={rental_record.id}")
    _send_email_for_rental(rental_record, trigger_type="reclaim")


@rental_reclaimed.connect
def on_rental_reclaimed(sender, **kwargs):
    """监听到回收事件 → 记录日志（邮件已在 expired 事件中发送）"""
    rental_record = kwargs.get('rental_record')
    if rental_record is None:
        return
    print(f"[subscribers] 收到 rental.reclaimed 事件: rental={rental_record.id}")
    # 回收邮件已在 expired 阶段发送，这里仅做日志记录或后续扩展
