"""
合同模块仪表盘统计
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from src.contract.models import Contract
from src.contract.services import get_contract_rentals


def get_dashboard_stats(db: Session) -> dict:
    """返回合同维度的运营概览统计"""
    today = date.today()
    threshold = today + timedelta(days=3)

    total_contracts = db.query(Contract).count()
    expiring = db.query(Contract).filter(
        Contract.end_date <= threshold,
        Contract.end_date > today,
        Contract.status.in_(['active', 'expiring']),
    ).count()
    reclaimed = db.query(Contract).filter(
        Contract.status == 'reclaimed'
    ).count()
    return {"total_contracts": total_contracts, "expiring": expiring, "reclaimed": reclaimed}


def get_expiring_contracts_with_rentals(db: Session, limit: int = 10) -> list[dict]:
    """返回临期合同及其关联设备列表"""
    today = date.today()
    threshold = today + timedelta(days=3)
    contracts = db.query(Contract).filter(
        Contract.end_date <= threshold,
        Contract.end_date > today,
        Contract.status.in_(['active', 'expiring']),
    ).order_by(Contract.end_date).limit(limit).all()

    result = []
    for c in contracts:
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
    return result
