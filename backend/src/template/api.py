"""
邮件模板模块 API 路由
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.crypto import decrypt_password
from src.template import schemas, services
from src.template.models import EmailTemplate
from src.mail.renderer import render_template, RenderError
from src.mail.sender import send_email
from src.system.services import get_smtp_config
from src.customer.models import Contact

# ============================================================
# Template Router
# ============================================================

template_router = APIRouter(prefix="/api/templates", tags=["Template"])


@template_router.get("/variables")
def get_available_variables():
    """
    返回租赁记录所有可用模板变量的字段名和中文说明。
    字段来源与 RentalRecord 模型保持一致，后端改模型后自动同步。

    定时任务按客户合并发送时，上下文为:
      - customer_name: 客户名称
      - rental_count: 设备数量
      - rentals: 设备列表，每个元素字段同单机变量（见下方）
    """
    variables = [
        # ---- 合并发送变量 ----
        {"field": "customer_name", "label": "客户名称", "type": "string"},
        {"field": "rental_count", "label": "设备数量", "type": "number", "note": "合并发送时可用"},
        {"field": "rentals", "label": "设备列表", "type": "array",
         "note": "用 {% for r in rentals %} 遍历，r 的字段同单机变量（machine_model, cpu_model 等）"},

        # ---- 单机变量 ----
        {"field": "machine_model", "label": "机器型号", "type": "string"},
        {"field": "cpu_model", "label": "CPU 型号", "type": "string"},
        {"field": "memory_gb", "label": "内存(GB)", "type": "number"},
        {"field": "gpu_info", "label": "GPU 信息", "type": "string"},
        {"field": "system_disk", "label": "系统盘", "type": "string", "note": "如 480GB SATA SSD"},
        {"field": "data_disks", "label": "数据盘列表", "type": "array", "note": "字符串数组，遍历: {% for disk in data_disks %}{{ disk }}{% endfor %}"},
        {"field": "os_version", "label": "操作系统", "type": "string"},
        {"field": "bandwidth_mbps", "label": "带宽(Mbps)", "type": "number"},
        {"field": "rack_location", "label": "机架位置", "type": "string"},
        {"field": "private_ip", "label": "内网 IP", "type": "string"},
        {"field": "public_ips", "label": "公网 IP 列表", "type": "array", "note": "遍历: {% for ip in public_ips %}{{ ip }}{% endfor %}"},
        {"field": "ssh_port", "label": "SSH 端口", "type": "number"},
        {"field": "root_username", "label": "SSH 账号", "type": "string"},
        {"field": "root_password", "label": "SSH 密码", "type": "string"},
        {"field": "billing_model", "label": "计费方式", "type": "string", "note": "monthly/quarterly/yearly"},
        {"field": "start_date", "label": "开通日期", "type": "date"},
        {"field": "end_date", "label": "到期日期", "type": "date"},
        {"field": "days_until_expiry", "label": "距到期天数", "type": "number", "note": "仅临期/到期模板可用"},
        {"field": "auto_renew", "label": "自动续期", "type": "boolean"},
        {"field": "remark", "label": "备注", "type": "string"},
    ]
    return {"variables": variables, "updated_at": datetime.now().isoformat()}


@template_router.get("", response_model=schemas.EmailTemplateListResponse)
def list_templates(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取邮件模板列表"""
    items, total = services.list_templates(db, page=page, page_size=page_size)
    result_items = [schemas.EmailTemplateResponse.model_validate(item) for item in items]
    return schemas.EmailTemplateListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@template_router.post("", response_model=schemas.EmailTemplateResponse, status_code=201)
def create_template(
    data: schemas.EmailTemplateCreate,
    db: Session = Depends(get_db),
):
    """创建邮件模板"""
    template = services.create_template(db, data)
    return schemas.EmailTemplateResponse.model_validate(template)


@template_router.get("/{template_id}", response_model=schemas.EmailTemplateResponse)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """获取邮件模板详情"""
    template = services.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return schemas.EmailTemplateResponse.model_validate(template)


@template_router.put("/{template_id}", response_model=schemas.EmailTemplateResponse)
def update_template(
    template_id: str,
    data: schemas.EmailTemplateUpdate,
    db: Session = Depends(get_db),
):
    """更新邮件模板（version 自动 +1）"""
    template = services.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    template = services.update_template(db, template, data)
    return schemas.EmailTemplateResponse.model_validate(template)


@template_router.delete("/{template_id}", response_model=dict)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """删除邮件模板"""
    template = services.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    services.delete_template(db, template)
    return {"detail": "模板已删除"}


@template_router.post("/preview", response_model=schemas.TemplatePreviewResponse)
def preview_template(
    data: schemas.TemplatePreviewRequest,
):
    """
    实时预览模板（不依赖数据库）
    使用 Jinja2 SandboxedEnvironment 渲染

    sample_data 自动包装为统一 rentals 数组结构，与 test_send / 定时任务保持一致：
    - 如果 sample_data 中已有 rentals 键（用户手动写了多设备结构），直接使用
    - 否则包装为 {customer_name, rental_count: 1, rentals: [sample_data]}
    """
    sample_data = data.sample_data or {}

    # 智能包装：已有 rentals 键则直接使用，否则包装为统一结构
    if "rentals" in sample_data:
        context = sample_data
    else:
        context = {
            "customer_name": sample_data.get("customer_name", ""),
            "rental_count": 1,
            "rentals": [sample_data],
        }

    try:
        subject_rendered = render_template(data.subject_tpl, context)
    except RenderError as e:
        raise HTTPException(status_code=400, detail=f"主题模板渲染失败: {e}")

    try:
        body_rendered = render_template(
            data.body_html, context,
            signature_html=data.signature_html,
        )
    except RenderError as e:
        raise HTTPException(status_code=400, detail=f"正文模板渲染失败: {e}")

    return schemas.TemplatePreviewResponse(
        subject_rendered=subject_rendered,
        body_rendered=body_rendered,
    )


@template_router.post("/{template_id}/test-send", response_model=schemas.TemplateTestSendResponse)
def test_send(
    template_id: str,
    body: schemas.TemplateTestSendRequest,
    db: Session = Depends(get_db),
):
    """
    测试发送邮件
    1. 查模板
    2. 根据 contact ids 查邮箱
    3. 渲染 subject + body + signature
    4. 查 SMTP 配置
    5. 调用 send_email
    6. 不写 EmailLog（测试邮件不记录）
    """
    # 1. 查模板
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 2. 查联系人邮箱
    to_emails = _get_emails_by_contact_ids(db, body.to_contact_ids)
    if not to_emails:
        raise HTTPException(status_code=400, detail="未找到有效的收件人邮箱")

    cc_emails = _get_emails_by_contact_ids(db, body.cc_contact_ids) if body.cc_contact_ids else []

    # 3. 取 sample_data 并包装为统一 rentals 结构
    sample_data = body.sample_data or template.variables_desc or {}
    # 智能包装：已有 rentals 键则直接使用（前端传了合同级数据），否则包装为单元素数组
    if "rentals" in sample_data and isinstance(sample_data.get("rentals"), list):
        context = dict(sample_data)
        context.setdefault("rental_count", len(sample_data["rentals"]))
    else:
        context = {
            "customer_name": sample_data.get("customer_name", ""),
            "rental_count": 1,
            "rentals": [sample_data],
        }

    # 渲染 subject
    try:
        subject_rendered = render_template(template.subject_tpl, context)
    except RenderError as e:
        raise HTTPException(status_code=400, detail=f"主题模板渲染失败: {e}")

    # 渲染 body + 签名
    try:
        body_rendered = render_template(
            template.body_html,
            context,
            signature_html=template.signature_html,
        )
    except RenderError as e:
        raise HTTPException(status_code=400, detail=f"正文模板渲染失败: {e}")

    # 4. 查 SMTP 配置
    smtp_config = get_smtp_config(db)
    if not smtp_config:
        raise HTTPException(status_code=400, detail="SMTP 配置不存在，请先配置 SMTP")

    smtp_password = decrypt_password(smtp_config.password_enc or "")

    # 5. 发送邮件
    success, error_msg = send_email(
        host=smtp_config.host,
        port=smtp_config.port,
        username=smtp_config.username or "",
        password=smtp_password,
        sender_name=smtp_config.sender_name or "CronMail",
        sender_email=smtp_config.sender_email or smtp_config.username or "",
        to_list=to_emails,
        cc_list=cc_emails,
        subject=subject_rendered,
        body_html=body_rendered,
        encryption=smtp_config.encryption or "tls",
    )

    # 6. 不写 EmailLog
    if success:
        return schemas.TemplateTestSendResponse(
            success=True,
            message="测试邮件发送成功",
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject_rendered=subject_rendered,
        )
    else:
        return schemas.TemplateTestSendResponse(
            success=False,
            message=f"发送失败: {error_msg}",
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject_rendered=subject_rendered,
        )


def _get_emails_by_contact_ids(db: Session, contact_ids: list[str]) -> list[str]:
    """根据 contact id 列表获取有效邮箱地址列表"""
    if not contact_ids:
        return []
    contacts = (
        db.query(Contact)
        .filter(Contact.id.in_(contact_ids), Contact.is_active == True)
        .all()
    )
    return [c.email for c in contacts if c.email]
