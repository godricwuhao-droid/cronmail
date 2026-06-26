"""
租赁记录模块 API 路由
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.crypto import decrypt_password
from src.rental import schemas, services
from src.rental.models import RentalRecord

# ============================================================
# Rental Router
# ============================================================

rental_router = APIRouter(prefix="/api/rentals", tags=["Rental"])


def _rental_to_list_item(rental: RentalRecord) -> schemas.RentalRecordListResponse:
    """将 ORM 对象转为列表项响应（不含密码、联系人列表、邮件日志）
    
    客户、日期、计费信息从关联合同继承，若无合同则返回 None/"-"。
    """
    # 取第一个关联合同
    contract = rental.contracts[0] if rental.contracts else None

    customer_brief = None
    start_date = None
    end_date = None
    billing_model = "monthly"
    auto_renew = False

    if contract:
        if contract.customer:
            customer_brief = schemas.CustomerBrief(
                id=contract.customer.id,
                name=contract.customer.name,
            )
        start_date = contract.start_date
        end_date = contract.end_date
        billing_model = contract.billing_model or "monthly"
        auto_renew = contract.auto_renew if hasattr(contract, 'auto_renew') else False
    elif rental.customer:
        # 兼容未关联合同的旧数据
        customer_brief = schemas.CustomerBrief(
            id=rental.customer.id,
            name=rental.customer.name,
        )

    # 处理 data_disks
    data_disks = None
    if rental.data_disks:
        data_disks = [
            schemas.DataDiskSchema(size_gb=d["size_gb"], type=d["type"])
            for d in rental.data_disks
        ]

    contract_id = rental.contracts[0].id if rental.contracts else None

    return schemas.RentalRecordListResponse(
        id=rental.id,
        contract_id=contract_id,
        customer=customer_brief,
        machine_model=rental.machine_model or "",
        cpu_model=rental.cpu_model,
        memory_gb=rental.memory_gb,
        gpu_info=rental.gpu_info,
        system_disk_gb=rental.system_disk_gb,
        data_disks=data_disks,
        os_version=rental.os_version,
        bandwidth_mbps=rental.bandwidth_mbps,
        rack_location=rental.rack_location,
        private_ip=rental.private_ip,
        public_ips=rental.public_ips,
        ssh_port=rental.ssh_port or 22,
        root_username=rental.root_username,
        billing_model=billing_model,
        start_date=start_date,
        end_date=end_date,
        auto_renew=auto_renew,
        remark=rental.remark,
        status=rental.status,
        created_at=rental.created_at,
        updated_at=rental.updated_at,
    )


def _rental_to_detail(rental: RentalRecord, db: Session) -> schemas.RentalRecordDetailResponse:
    """将 ORM 对象转为详情响应（含解密密码、联系人、邮件日志、合同信息）
    
    客户、日期、计费信息从关联合同继承，若无合同则返回 None/"-"。
    """
    # 取第一个关联合同
    contract = rental.contracts[0] if rental.contracts else None

    customer_brief = None
    start_date = None
    end_date = None
    billing_model = "monthly"
    auto_renew = False
    contract_info = None

    if contract:
        if contract.customer:
            customer_brief = schemas.CustomerBrief(
                id=contract.customer.id,
                name=contract.customer.name,
            )
        start_date = contract.start_date
        end_date = contract.end_date
        billing_model = contract.billing_model or "monthly"
        auto_renew = contract.auto_renew if hasattr(contract, 'auto_renew') else False
        contract_info = {
            "id": contract.id,
            "name": contract.name,
            "start_date": str(contract.start_date) if contract.start_date else None,
            "end_date": str(contract.end_date) if contract.end_date else None,
            "billing_model": contract.billing_model,
        }
    elif rental.customer:
        # 兼容未关联合同的旧数据
        customer_brief = schemas.CustomerBrief(
            id=rental.customer.id,
            name=rental.customer.name,
        )

    # 联系人信息
    contacts = services.get_rental_contacts(db, rental.id)
    contact_items = [
        schemas.RentalContactResponse(
            contact_id=c["contact_id"],
            name=c["name"],
            email=c["email"],
            recipient_type=c["recipient_type"],
        )
        for c in contacts
    ]

    # 邮件日志
    email_logs = services.get_rental_email_logs(db, rental.id)
    email_log_items = [
        schemas.EmailLogBrief.model_validate(log) for log in email_logs
    ]

    # 解密密码
    root_password = decrypt_password(rental.root_password_enc or "") if rental.root_password_enc else None

    # 处理 data_disks
    data_disks = None
    if rental.data_disks:
        data_disks = [
            schemas.DataDiskSchema(size_gb=d["size_gb"], type=d["type"])
            for d in rental.data_disks
        ]

    return schemas.RentalRecordDetailResponse(
        id=rental.id,
        customer=customer_brief,
        contacts=contact_items,
        contract_info=contract_info,
        machine_model=rental.machine_model or "",
        cpu_model=rental.cpu_model,
        memory_gb=rental.memory_gb,
        gpu_info=rental.gpu_info,
        system_disk_gb=rental.system_disk_gb,
        data_disks=data_disks,
        os_version=rental.os_version,
        bandwidth_mbps=rental.bandwidth_mbps,
        rack_location=rental.rack_location,
        private_ip=rental.private_ip,
        public_ips=rental.public_ips,
        ssh_port=rental.ssh_port or 22,
        root_username=rental.root_username,
        root_password=root_password,
        billing_model=billing_model,
        start_date=start_date,
        end_date=end_date,
        auto_renew=auto_renew,
        remark=rental.remark,
        status=rental.status,
        email_logs=email_log_items,
        created_at=rental.created_at,
        updated_at=rental.updated_at,
    )


@rental_router.get("", response_model=schemas.RentalRecordListWrap)
def list_rentals(
    customer_id: Optional[str] = Query(None, description="客户ID"),
    status: Optional[str] = Query(None, description="设备物理状态: 空闲中 / 已断电 / 租赁中"),
    search: Optional[str] = Query(None, description="按机器型号模糊搜索"),
    private_ip: Optional[str] = Query(None, description="按内网IP模糊搜索"),
    public_ip: Optional[str] = Query(None, description="按公网IP模糊搜索"),
    rack_location: Optional[str] = Query(None, description="按机架位置模糊搜索"),
    unlinked_only: bool = Query(False, description="只返回未关联合同的设备"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取租赁记录列表"""
    items, total = services.list_rentals(
        db,
        customer_id=customer_id,
        status=status,
        search=search,
        private_ip=private_ip,
        public_ip=public_ip,
        rack_location=rack_location,
        page=page,
        page_size=page_size,
        unlinked_only=unlinked_only,
    )
    result_items = [_rental_to_list_item(item) for item in items]
    return schemas.RentalRecordListWrap(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@rental_router.post("", response_model=schemas.RentalRecordDetailResponse, status_code=201)
def create_rental(
    data: schemas.RentalRecordCreate,
    db: Session = Depends(get_db),
):
    """创建租赁记录（纯硬件档案，客户/日期/计费从关联合同继承）"""
    rental = services.create_rental(db, data)
    return _rental_to_detail(rental, db)


@rental_router.get("/{rental_id}", response_model=schemas.RentalRecordDetailResponse)
def get_rental(
    rental_id: str,
    db: Session = Depends(get_db),
):
    """获取租赁记录详情（含解密密码、联系人、邮件日志）"""
    rental = services.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="租赁记录不存在")
    return _rental_to_detail(rental, db)


@rental_router.put("/{rental_id}", response_model=schemas.RentalRecordDetailResponse)
def update_rental(
    rental_id: str,
    data: schemas.RentalRecordUpdate,
    db: Session = Depends(get_db),
):
    """全量更新租赁记录（纯硬件档案）"""
    rental = services.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="租赁记录不存在")

    rental = services.update_rental(db, rental, data)
    return _rental_to_detail(rental, db)


@rental_router.delete("/{rental_id}", response_model=dict)
def delete_rental(
    rental_id: str,
    db: Session = Depends(get_db),
):
    """删除租赁记录"""
    rental = services.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="租赁记录不存在")
    services.delete_rental(db, rental)
    return {"detail": "租赁记录已删除"}


# ============================================================
# 邮件发送相关端点（事件驱动：API 执行业务逻辑 + 发布事件，订阅者发邮件）
# ============================================================

@rental_router.post("/{rental_id}/send-provision-email", response_model=schemas.SendEmailResponse)
def send_provision_email(
    rental_id: str,
    data: schemas.SendEmailRequest = schemas.SendEmailRequest(),
    db: Session = Depends(get_db),
):
    """手动发送开通邮件：以该设备所属合同为粒度合并发送"""
    rental = services.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="租赁记录不存在")

    # 找到该 rental 关联的合同（取第一个）
    contracts = rental.contracts
    if not contracts:
        raise HTTPException(status_code=400, detail="该设备未关联任何合同，请先创建合同并关联设备")

    contract = contracts[0]

    from src.scheduler.tasks import send_manual_email
    send_manual_email.delay(contract_id=contract.id, trigger_type="provision")

    # 统计设备数
    rental_count = len(contract.rentals) if contract.rentals else 1
    return schemas.SendEmailResponse(
        email_log_ids=[],
        recipient_count=0,
        message=f"已提交异步发送任务（合同 {contract.name}，共 {rental_count} 台设备）",
    )


@rental_router.post("/{rental_id}/send-expiry-reminder", response_model=schemas.SendEmailResponse)
def send_expiry_reminder(
    rental_id: str,
    data: schemas.SendEmailRequest = schemas.SendEmailRequest(),
    db: Session = Depends(get_db),
):
    """手动发送临期提醒：以该设备所属合同为粒度合并发送"""
    rental = services.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="租赁记录不存在")

    # 找到该 rental 关联的合同（取第一个）
    contracts = rental.contracts
    if not contracts:
        raise HTTPException(status_code=400, detail="该设备未关联任何合同，请先创建合同并关联设备")

    contract = contracts[0]

    # 更新合同状态为 expiring
    contract.status = 'expiring'
    db.commit()

    # 异步发送
    from src.scheduler.tasks import send_manual_email
    send_manual_email.delay(contract_id=contract.id, trigger_type="expiry_warning")

    # 统计设备数
    rental_count = len(contract.rentals) if contract.rentals else 1
    return schemas.SendEmailResponse(
        email_log_ids=[],
        recipient_count=0,
        message=f"已提交异步发送任务（合同 {contract.name}，共 {rental_count} 台设备）",
    )


@rental_router.post("/{rental_id}/reclaim", response_model=schemas.ReclaimResponse)
def reclaim_rental(
    rental_id: str,
    data: schemas.SendEmailRequest = schemas.SendEmailRequest(),
    db: Session = Depends(get_db),
):
    """手动回收：以该设备所属合同为粒度合并发送（异步，状态更新在 Celery 任务里）"""
    rental = services.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=404, detail="租赁记录不存在")

    # 找到该 rental 关联的合同（取第一个）
    contracts = rental.contracts
    if not contracts:
        raise HTTPException(status_code=400, detail="该设备未关联任何合同，请先创建合同并关联设备")

    contract = contracts[0]

    # 异步发送（状态更新移到 Celery 任务里）
    from src.scheduler.tasks import send_manual_email
    send_manual_email.delay(contract_id=contract.id, trigger_type="reclaim")

    rental_count = len(contract.rentals) if contract.rentals else 1
    return schemas.ReclaimResponse(
        success=True,
        message=f"已提交异步发送任务（合同 {contract.name}，共 {rental_count} 台设备），状态将在任务完成后更新",
        email_log_ids=[],
        recipient_count=0,
    )
