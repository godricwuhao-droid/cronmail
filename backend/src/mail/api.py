"""
邮件日志模块 API 路由
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.crypto import decrypt_password
from src.mail import schemas, services
from src.mail.sender import send_email
from src.mail.renderer import render_template, RenderError
from src.system.services import get_smtp_config
from src.rental.models import RentalRecord, rental_contact
from src.template.services import get_active_template_by_trigger
from src.customer.models import Contact

# ============================================================
# Log Router
# ============================================================

log_router = APIRouter(prefix="/api/logs", tags=["EmailLog"])


@log_router.get("", response_model=schemas.EmailLogListResponse)
def list_logs(
    rental_id: Optional[str] = Query(None, description="租赁记录ID"),
    trigger_type: Optional[str] = Query(None, description="触发类型: provision / expiry_warning / reclaim"),
    status: Optional[str] = Query(None, description="状态: sent / failed"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取邮件日志列表"""
    items, total = services.list_logs(
        db,
        rental_id=rental_id,
        trigger_type=trigger_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    result_items = [schemas.EmailLogResponse.model_validate(item) for item in items]
    return schemas.EmailLogListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@log_router.get("/{log_id}", response_model=schemas.EmailLogDetailResponse)
def get_log(
    log_id: str,
    db: Session = Depends(get_db),
):
    """获取邮件日志详情（含 body）"""
    log = services.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return schemas.EmailLogDetailResponse.model_validate(log)


@log_router.post("/{log_id}/resend", response_model=schemas.ResendResponse)
def resend_log(
    log_id: str,
    db: Session = Depends(get_db),
):
    """重发失败的邮件"""
    log = services.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    if log.status == "sent":
        raise HTTPException(status_code=422, detail="该邮件已发送成功，无需重发")

    # 获取 SMTP 配置
    smtp_config = get_smtp_config(db)
    if not smtp_config:
        raise HTTPException(status_code=400, detail="SMTP 配置不存在，请先配置 SMTP")

    # 找到对应的租赁记录
    rental = db.query(RentalRecord).filter(RentalRecord.id == log.rental_id).first()
    if not rental:
        raise HTTPException(status_code=404, detail="关联的租赁记录不存在")

    # 找到模板
    template = get_active_template_by_trigger(db, log.trigger_type) if log.trigger_type else None
    if not template:
        raise HTTPException(status_code=404, detail="未找到活跃的邮件模板")

    # 构建渲染上下文
    context = _build_rental_context(db, rental)

    # 渲染模板
    try:
        subject = render_template(template.subject_tpl, context)
        body_html = render_template(template.body_html, context, signature_html=template.signature_html)
    except RenderError as e:
        raise HTTPException(status_code=400, detail=f"模板渲染失败: {e}")

    # 解密 SMTP 密码
    smtp_password = decrypt_password(smtp_config.password_enc or "")

    # 发送邮件
    to_list = [log.recipient] if log.recipient_type == "to" else []
    cc_list = [log.recipient] if log.recipient_type == "cc" else []

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

    if success:
        services.update_log_status(db, log, "sent")
        return schemas.ResendResponse(
            success=True,
            message="邮件重发成功",
            email_log_id=log.id,
        )
    else:
        services.update_log_status(db, log, "failed", error_msg)
        return schemas.ResendResponse(
            success=False,
            message=f"重发失败: {error_msg}",
            email_log_id=log.id,
        )


def _build_rental_context(db: Session, rental: RentalRecord) -> dict:
    """
    构建邮件模板渲染上下文（统一 rentals 数组结构）

    单条租赁记录包装为单元素 rentals 数组，与定时合并发送（N条）结构一致。
    模板变量: customer_name, rental_count, rentals (数组，元素字段如下)
    """
    from datetime import date

    # 距到期天数
    days_until_expiry = 0
    if rental.end_date:
        today = date.today()
        delta = rental.end_date - today
        days_until_expiry = delta.days

    # 联系人信息
    contacts_info = _get_rental_contacts(db, rental.id)

    # 单条设备上下文
    rental_ctx = {
        "machine_model": rental.machine_model or "",
        "cpu_model": rental.cpu_model or "",
        "memory_gb": rental.memory_gb or "",
        "gpu_info": rental.gpu_info or "",
        "system_disk_gb": rental.system_disk_gb or "",
        "data_disks": rental.data_disks or [],
        "os_version": rental.os_version or "",
        "bandwidth_mbps": rental.bandwidth_mbps or "",
        "rack_location": rental.rack_location or "",
        "private_ip": rental.private_ip or "",
        "public_ips": rental.public_ips or [],
        "ssh_port": rental.ssh_port or 22,
        "root_username": rental.root_username or "root",
        "root_password": decrypt_password(rental.root_password_enc or ""),
        "billing_model": rental.billing_model or "monthly",
        "start_date": rental.start_date.isoformat() if rental.start_date else "",
        "end_date": rental.end_date.isoformat() if rental.end_date else "",
        "auto_renew": rental.auto_renew,
        "remark": rental.remark or "",
        "status": rental.status or "",
        "days_until_expiry": days_until_expiry,
        "contacts": contacts_info,
    }

    # 客户名称
    customer = rental.customer
    customer_name = customer.name if customer else ""

    # 统一结构：rentals 数组 + rental_count + customer_name
    return {
        "customer_name": customer_name,
        "rental_count": 1,
        "rentals": [rental_ctx],
    }


def _get_rental_contacts(db: Session, rental_id: str) -> list[dict]:
    """
    获取租赁记录关联的联系人信息
    返回: [{"name": "...", "email": "...", "recipient_type": "to"}, ...]
    """
    from sqlalchemy import text

    rows = db.execute(
        text(
            "SELECT c.name, c.email, rc.recipient_type "
            "FROM rental_contact rc "
            "JOIN contact c ON rc.contact_id = c.id "
            "WHERE rc.rental_id = :rental_id"
        ),
        {"rental_id": rental_id},
    ).fetchall()

    contacts = []
    for row in rows:
        contacts.append({
            "name": row[0],
            "email": row[1],
            "recipient_type": row[2],
        })
    return contacts
