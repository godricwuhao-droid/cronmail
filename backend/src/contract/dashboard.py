"""
合同模块仪表盘统计
"""
import datetime
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from src.contract.models import Contract, contract_rental
from src.contract.services import get_contract_rentals
from src.core.timezone import local_today


def _get_max_expiry_warning_days(db: Session) -> int:
    """从 system_config 读取 expiry_warning_days，返回最大天数"""
    from src.system.models import SystemConfig
    config = db.query(SystemConfig).filter(SystemConfig.key == 'expiry_warning_days').first()
    days_str = config.value if config else '7,3'
    days_list = [int(d.strip()) for d in days_str.split(',') if d.strip().isdigit()]
    return max(days_list) if days_list else 7


def get_dashboard_stats(db: Session) -> dict:
    """返回合同维度的运营概览统计"""
    today = local_today()
    threshold = today + timedelta(days=_get_max_expiry_warning_days(db))

    total_contracts = db.query(Contract).count()
    expiring = db.query(Contract).filter(
        Contract.end_date <= threshold,
        Contract.end_date >= today,
        Contract.status.in_(['active', 'expiring']),
    ).count()
    expired = db.query(Contract).filter(
        Contract.status == 'expired'
    ).count()
    reclaimed = db.query(Contract).filter(
        Contract.status == 'reclaimed'
    ).count()
    return {"total_contracts": total_contracts, "expiring": expiring, "expired": expired, "reclaimed": reclaimed}


def get_expiring_contracts_with_rentals(db: Session, limit: int = 10) -> list[dict]:
    """返回临期及已到期合同及其关联设备列表（已到期排前面，更紧急）"""
    today = local_today()
    threshold = today + timedelta(days=_get_max_expiry_warning_days(db))

    # 已到期：status='expired'（end_date 已过）
    expired_contracts = db.query(Contract).filter(
        Contract.status.in_(['expired']),
    ).order_by(Contract.end_date).limit(limit).all()

    # 临期：end_date 在未来阈值内且未到期
    expiring_contracts = db.query(Contract).filter(
        Contract.end_date <= threshold,
        Contract.end_date >= today,
        Contract.status.in_(['active', 'expiring']),
    ).order_by(Contract.end_date).limit(limit).all()

    # 合并：已到期排前面（更紧急），去重
    seen: set[str] = set()
    result: list[dict] = []
    for c in expired_contracts + expiring_contracts:
        if c.id in seen:
            continue
        seen.add(c.id)
        rentals = get_contract_rentals(db, c.id)
        result.append({
            "contract_id": c.id,
            "contract_name": c.name,
            "customer_name": c.customer.name if c.customer else "",
            "end_date": str(c.end_date),
            "status": c.status,
            "rental_count": len(rentals),
            "rentals": rentals,
        })
        if len(result) >= limit:
            break
    return result


def get_overview_stats(db: Session) -> dict:
    """获取运营概览图表的统计数据

    返回:
        - rental_by_customer: 各客户租赁中设备二维细分（TOP 10，每客户下按机型细分）
        - rental_by_model: 机器型号分布（TOP 10）
        - contract_trend: 近 12 个月合同新签/到期趋势
    """
    from src.rental.models import RentalRecord
    from src.customer.models import Customer

    # 1. 客户设备细分：按客户+机型分组（仅统计租赁中的设备）
    rows = (
        db.query(
            Customer.name.label('customer_name'),
            RentalRecord.machine_model,
            func.count(RentalRecord.id).label('count'),
        )
        .join(RentalRecord, RentalRecord.customer_id == Customer.id)
        .filter(RentalRecord.status == '租赁中')
        .group_by(Customer.id, Customer.name, RentalRecord.machine_model)
        .order_by(Customer.name, func.count(RentalRecord.id).desc())
        .all()
    )

    # 组装嵌套结构
    customer_model_map: dict[str, list] = {}
    for row in rows:
        cname = row.customer_name or '未知'
        model = row.machine_model or '未知'
        cnt = row.count
        if cname not in customer_model_map:
            customer_model_map[cname] = []
        customer_model_map[cname].append({"machine_model": model, "count": cnt})

    # 按总设备数排序取 TOP 10 客户
    sorted_customers = sorted(
        customer_model_map.items(),
        key=lambda x: sum(m['count'] for m in x[1]),
        reverse=True
    )[:10]

    rental_by_customer = [
        {"customer_name": name, "models": models}
        for name, models in sorted_customers
    ]

    # 2. 机器型号分布（所有租赁中设备，TOP 10）
    rental_by_model = (
        db.query(
            RentalRecord.machine_model,
            func.count(RentalRecord.id).label('count'),
        )
        .filter(RentalRecord.status == '租赁中')
        .group_by(RentalRecord.machine_model)
        .order_by(func.count(RentalRecord.id).desc())
        .limit(10)
        .all()
    )
    rental_by_model = [
        {"machine_model": r.machine_model, "count": r.count}
        for r in rental_by_model
    ]

    # 3. 近 12 个月合同趋势（新签 / 到期）
    today = datetime.date.today()
    months = []
    for i in range(11, -1, -1):
        y = today.year
        m = today.month - i
        if m <= 0:
            y -= 1
            m += 12
        months.append((y, m))

    contract_trend = []
    for y, m in months:
        created_count = (
            db.query(func.count(Contract.id))
            .filter(
                extract('year', Contract.start_date) == y,
                extract('month', Contract.start_date) == m,
            )
            .scalar()
        ) or 0
        expired_count = (
            db.query(func.count(Contract.id))
            .filter(
                extract('year', Contract.end_date) == y,
                extract('month', Contract.end_date) == m,
            )
            .scalar()
        ) or 0
        contract_trend.append({
            "month": f"{y}-{m:02d}",
            "created_count": created_count,
            "expired_count": expired_count,
        })

    return {
        "rental_by_customer": rental_by_customer,
        "rental_by_model": rental_by_model,
        "contract_trend": contract_trend,
    }
