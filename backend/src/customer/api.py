"""
客户模块 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.contract.models import Contract
from src.customer import schemas, services

# ============================================================
# Customer Router
# ============================================================

customer_router = APIRouter(prefix="/api/customers", tags=["Customer"])


def _get_contract_stats(db: Session, customer_id: str) -> schemas.ContractStats:
    """获取客户的合同统计"""
    from sqlalchemy import func, case

    stats = db.query(
        func.count(Contract.id).label('total'),
        func.sum(case((Contract.status == 'active', 1), else_=0)).label('active'),
        func.sum(case((Contract.status.in_(['expired', 'expiring']), 1), else_=0)).label('expired'),
    ).filter(Contract.customer_id == customer_id).first()
    return schemas.ContractStats(
        total=stats.total or 0,
        active=(stats.active or 0),
        expired=(stats.expired or 0),
    )


def _build_customer_response(db: Session, customer) -> schemas.CustomerResponse:
    """构建 CustomerResponse，附加联系人数量和合同统计"""
    contact_count = services.get_customer_contact_count(db, customer.id)
    contract_stats = _get_contract_stats(db, customer.id)
    return schemas.CustomerResponse(
        id=customer.id,
        name=customer.name,
        code=customer.code,
        status=customer.status,
        business_types=customer.business_types,
        contact_count=contact_count,
        contract_stats=contract_stats,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


@customer_router.get("", response_model=schemas.CustomerListResponse)
def list_customers(
    search: Optional[str] = Query(None, description="按名称模糊搜索"),
    business_type: Optional[str] = Query(
        None,
        description="业务类型过滤: 算力租赁 / 卫星数据 / 算力服务",
    ),
    status: Optional[str] = Query(None, description="状态过滤: active / inactive"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取客户列表，支持模糊搜索、业务类型过滤、状态过滤和分页"""
    items, total = services.list_customers(
        db,
        search=search,
        business_type=business_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    result_items = [_build_customer_response(db, c) for c in items]
    return schemas.CustomerListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@customer_router.post("", response_model=schemas.CustomerResponse, status_code=201)
def create_customer(
    data: schemas.CustomerCreate,
    db: Session = Depends(get_db),
):
    """创建客户"""
    # code 唯一性校验（仅当用户手动指定 code 时）
    if data.code:
        existing = services.get_customer_by_code(db, data.code)
        if existing:
            raise HTTPException(status_code=400, detail=f"客户编码 '{data.code}' 已存在")
    customer = services.create_customer(db, data)
    return _build_customer_response(db, customer)


@customer_router.get("/{customer_id}", response_model=schemas.CustomerResponse)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """获取客户详情"""
    customer = services.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return _build_customer_response(db, customer)


@customer_router.put("/{customer_id}", response_model=schemas.CustomerResponse)
def update_customer(
    customer_id: str,
    data: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
):
    """更新客户"""
    customer = services.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    # 如果修改了 code，校验唯一性
    if data.code is not None and data.code != customer.code:
        existing = services.get_customer_by_code(db, data.code)
        if existing and existing.id != customer_id:
            raise HTTPException(status_code=400, detail=f"客户编码 '{data.code}' 已存在")
    customer = services.update_customer(db, customer, data)
    return _build_customer_response(db, customer)


@customer_router.delete("/{customer_id}", response_model=dict)
def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """删除客户（软删除：设为 inactive）"""
    customer = services.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 删除前检查：该客户是否有活跃/临期合同
    from src.contract.models import Contract
    active_contracts = db.query(Contract).filter(
        Contract.customer_id == customer_id,
        Contract.status.in_(['active', 'expiring'])
    ).count()

    if active_contracts > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该客户有 {active_contracts} 个活跃合同，请先处理合同后再删除"
        )

    services.delete_customer(db, customer)
    return {"detail": "客户已删除（状态设为 inactive）"}


# ============================================================
# Contact Router
# ============================================================

contact_router = APIRouter(prefix="/api/contacts", tags=["Contact"])


@contact_router.get("", response_model=schemas.ContactListResponse)
def list_contacts(
    customer_id: Optional[str] = Query(None, description="客户ID"),
    type: Optional[str] = Query(None, description="类型: customer / colleague"),
    all: Optional[str] = Query(None, description="type=customer 时传 all=true 返回所有客户联系人"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """
    获取联系人列表
    - type=customer：查询指定客户下的联系人（需同时传 customer_id，或传 all=true 返回所有客户联系人）
    - type=colleague：查询内部同事（customer_id IS NULL），忽略 customer_id
    """
    # 参数校验
    if type == "customer" and not customer_id and all != "true":
        raise HTTPException(status_code=400, detail="type=customer 时必须提供 customer_id，或传 all=true 返回所有客户联系人")

    items, total = services.list_contacts(
        db,
        customer_id=customer_id,
        contact_type=type,
        all_customers=(all == "true"),
        page=page,
        page_size=page_size,
    )
    result_items = [schemas.ContactResponse.model_validate(item) for item in items]
    return schemas.ContactListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@contact_router.post("", response_model=schemas.ContactResponse, status_code=201)
def create_contact(
    data: schemas.ContactCreate,
    db: Session = Depends(get_db),
):
    """创建联系人"""
    # 如果传了 customer_id，校验客户是否存在
    if data.customer_id:
        from src.customer.services import get_customer
        customer = get_customer(db, data.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
    contact = services.create_contact(db, data)
    return schemas.ContactResponse.model_validate(contact)


@contact_router.get("/{contact_id}", response_model=schemas.ContactResponse)
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
):
    """获取联系人详情"""
    contact = services.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return schemas.ContactResponse.model_validate(contact)


@contact_router.put("/{contact_id}", response_model=schemas.ContactResponse)
def update_contact(
    contact_id: str,
    data: schemas.ContactUpdate,
    db: Session = Depends(get_db),
):
    """更新联系人"""
    contact = services.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    # 如果修改了 customer_id，校验客户是否存在
    if data.customer_id is not None:
        from src.customer.services import get_customer
        customer = get_customer(db, data.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")
    contact = services.update_contact(db, contact, data)
    return schemas.ContactResponse.model_validate(contact)


@contact_router.delete("/{contact_id}", response_model=dict)
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
):
    """删除联系人（软删除：设为 is_active=False）"""
    contact = services.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    services.delete_contact(db, contact)
    return {"detail": "联系人已删除（状态设为 inactive）"}
