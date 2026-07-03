"""
客户模块业务逻辑层
"""
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.customer.models import Customer, Contact, generate_uuid
from src.customer.schemas import (
    CustomerCreate,
    CustomerUpdate,
    ContactCreate,
    ContactUpdate,
)


# ============================================================
# Customer Services
# ============================================================

def list_customers(
    db: Session,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Customer], int]:
    """查询客户列表，支持模糊搜索和分页"""
    query = db.query(Customer)
    if search:
        query = query.filter(Customer.name.ilike(f"%{search}%"))
    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size).all()
    return items, total


def get_customer(db: Session, customer_id: str) -> Optional[Customer]:
    """根据 ID 获取客户"""
    return db.query(Customer).filter(Customer.id == customer_id).first()


def get_customer_by_code(db: Session, code: str) -> Optional[Customer]:
    """根据 code 获取客户（唯一性校验）"""
    return db.query(Customer).filter(Customer.code == code).first()


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    """创建客户"""
    customer = Customer(
        name=data.name,
        code=data.code or generate_uuid(),
        status="active",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer: Customer, data: CustomerUpdate) -> Customer:
    """更新客户"""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer: Customer) -> Customer:
    """软删除客户（设为 inactive）"""
    customer.status = "inactive"
    db.commit()
    db.refresh(customer)
    return customer


def get_customer_contact_count(db: Session, customer_id: str) -> int:
    """获取客户下的联系人数量"""
    return db.query(Contact).filter(
        Contact.customer_id == customer_id,
        Contact.is_active == True,
    ).count()


# ============================================================
# Contact Services
# ============================================================

def list_contacts(
    db: Session,
    customer_id: Optional[str] = None,
    contact_type: Optional[str] = None,
    all_customers: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Contact], int]:
    """
    查询联系人列表
    - type='colleague': 查询 customer_id IS NULL
    - type='customer': 查询 customer_id = ? (需要 customer_id 参数)
      - all_customers=True: 不加 customer_id 过滤，返回所有客户联系人
    """
    query = db.query(Contact)

    if contact_type == "colleague":
        query = query.filter(Contact.customer_id.is_(None))
    elif contact_type == "customer":
        if customer_id:
            query = query.filter(Contact.customer_id == customer_id)
        else:
            # all_customers=True 或未指定 customer_id 时：返回所有客户联系人 (customer_id IS NOT NULL)
            query = query.filter(Contact.customer_id.isnot(None))
    elif customer_id:
        # 兼容旧逻辑：只传 customer_id
        query = query.filter(Contact.customer_id == customer_id)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Contact.created_at.desc()).offset(offset).limit(page_size).all()
    return items, total


def get_contact(db: Session, contact_id: str) -> Optional[Contact]:
    """根据 ID 获取联系人"""
    return db.query(Contact).filter(Contact.id == contact_id).first()


def create_contact(db: Session, data: ContactCreate) -> Contact:
    """创建联系人"""
    contact = Contact(
        customer_id=data.customer_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        department=data.department,
        is_active=True,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(db: Session, contact: Contact, data: ContactUpdate) -> Contact:
    """更新联系人"""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: Contact) -> Contact:
    """软删除联系人（设为 is_active=False）"""
    contact.is_active = False
    db.commit()
    db.refresh(contact)
    return contact
