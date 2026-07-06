"""
合同模块仪表盘统计
"""
from datetime import timedelta
from sqlalchemy.orm import Session

from src.contract.models import Contract
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
