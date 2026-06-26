"""
邮件模板模块业务逻辑层
"""
from typing import Optional

from sqlalchemy.orm import Session

from src.template.models import EmailTemplate
from src.template.schemas import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
)


def list_templates(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EmailTemplate], int]:
    """查询邮件模板列表"""
    query = db.query(EmailTemplate)
    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(EmailTemplate.updated_at.desc()).offset(offset).limit(page_size).all()
    return items, total


def get_template(db: Session, template_id: str) -> Optional[EmailTemplate]:
    """根据 ID 获取模板"""
    return db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()


def get_active_template_by_trigger(db: Session, trigger_type: str) -> Optional[EmailTemplate]:
    """
    根据触发类型获取激活的模板
    取最新 version（按 version 降序）
    """
    return (
        db.query(EmailTemplate)
        .filter(
            EmailTemplate.trigger_type == trigger_type,
            EmailTemplate.is_active == True,
        )
        .order_by(EmailTemplate.version.desc())
        .first()
    )


def create_template(db: Session, data: EmailTemplateCreate) -> EmailTemplate:
    """创建邮件模板"""
    template = EmailTemplate(
        name=data.name,
        trigger_type=data.trigger_type,
        subject_tpl=data.subject_tpl,
        body_html=data.body_html,
        variables_desc=data.variables_desc,
        is_active=data.is_active,
        version=1,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(db: Session, template: EmailTemplate, data: EmailTemplateUpdate) -> EmailTemplate:
    """
    更新邮件模板（version 自动 +1）
    互斥规则：启用某个模板时，自动停用同 trigger_type 的其他模板
    """
    update_data = data.model_dump(exclude_unset=True)

    # 如果启用此模板，停用同类型的其他模板（互斥）
    if update_data.get('is_active'):
        db.query(EmailTemplate).filter(
            EmailTemplate.trigger_type == template.trigger_type,
            EmailTemplate.id != template.id,
            EmailTemplate.is_active == True,
        ).update({'is_active': False})

    for field, value in update_data.items():
        setattr(template, field, value)
    # 版本号自动 +1
    template.version += 1
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template: EmailTemplate) -> EmailTemplate:
    """删除邮件模板"""
    db.delete(template)
    db.commit()
    return template
