"""
Celery 定时任务
- check_expiring_rentals: 每天 08:00，扫描即将到期的合同，按合同合并发送
- check_expired_rentals: 每天 00:00，扫描当天到期的合同，按合同合并发送
"""
from datetime import date, timedelta

from sqlalchemy import delete as sa_delete

from src.core.database import SessionLocal
from .celery_app import celery_app
from src.mail.services import send_merged_email_by_contract
from src.contract.models import contract_rental


@celery_app.task(name='scheduler.tasks.check_expiring_rentals')
def check_expiring_rentals():
    """
    每天 08:00 扫描即将到期的合同，合并发送临期提醒

    临期天数从 system_config 表 expiry_warning_days 配置读取（默认 "7,3"）。
    每个天数阈值独立扫描，同一天可能触发多次邮件。
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.system.models import SystemConfig
        from src.mail.services import send_merged_email_by_contract

        # 读取配置的天数列表
        config = db.query(SystemConfig).filter(SystemConfig.key == 'expiry_warning_days').first()
        days_str = config.value if config else '7,3'
        days_list = [int(d.strip()) for d in days_str.split(',') if d.strip().isdigit()]

        today = date.today()

        for day_offset in days_list:
            threshold = today + timedelta(days=day_offset)
            contracts = (
                db.query(Contract)
                .filter(
                    Contract.end_date == threshold,
                    Contract.status.in_(['active', 'expiring']),
                )
                .all()
            )

            if contracts:
                print(f"[tasks] check_expiring_rentals: {day_offset}天后到期, 找到 {len(contracts)} 个合同")

            for c in contracts:
                c.status = 'expiring'
            db.commit()

            for c in contracts:
                try:
                    send_merged_email_by_contract(db, c, 'expiry_warning')
                except Exception as e:
                    db.rollback()
                    print(f"[tasks] 合同 {c.id[:8]} 临期({day_offset}天) 邮件失败: {e}")

        print(f"[tasks] check_expiring_rentals: 处理完成, 配置天数={days_list}")
    except Exception as e:
        print(f"[tasks] check_expiring_rentals 异常: {e}")
    finally:
        db.close()


@celery_app.task(name='scheduler.tasks.check_reclaim_expired')
def check_reclaim_expired():
    """
    每天 00:00：对状态为 expired 的合同执行实际回收（清理关联、释放设备）
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.rental.models import RentalRecord

        today = date.today()
        contracts = (
            db.query(Contract)
            .filter(
                Contract.status == 'expired',
                Contract.end_date < today,  # 只回收昨天及以前过期的，今天过期的等明天
            )
            .all()
        )

        if not contracts:
            print("[tasks] check_reclaim_expired: 没有待回收的合同")
            return

        print(f"[tasks] check_reclaim_expired: 找到 {len(contracts)} 个待回收合同")

        for c in contracts:
            try:
                c.status = 'reclaimed'
                c.history_rental_ids = [r.id for r in c.rentals]

                for r in c.rentals:
                    r.status = '空闲中'
                    r.customer_id = None

                db.execute(sa_delete(contract_rental).where(contract_rental.c.contract_id == c.id))
                db.commit()
                print(f"[tasks] 合同 {c.id[:8]} 回收完成, 设备 {len(c.history_rental_ids)} 台")
            except Exception as e:
                db.rollback()
                print(f"[tasks] 合同 {c.id[:8]} 回收失败: {e}")

    except Exception as e:
        print(f"[tasks] check_reclaim_expired 异常: {e}")
    finally:
        db.close()


@celery_app.task(name='scheduler.tasks.send_manual_email')
def send_manual_email(contract_id: str, trigger_type: str):
    """
    手动触发合并邮件发送（异步，以合同为粒度）
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.mail.services import send_merged_email_by_contract

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            print(f"[send_manual_email] 合同不存在: {contract_id}")
            return

        result = send_merged_email_by_contract(db, contract, trigger_type)

        # reclaim 类型：更新合同和设备状态
        if trigger_type == 'reclaim':
            contract.status = 'reclaimed'
            # 查询关联设备
            from src.rental.models import RentalRecord
            rentals = (
                db.query(RentalRecord)
                .join(RentalRecord.contracts)
                .filter(Contract.id == contract_id)
                .all()
            )

            # 保存快照
            rental_ids = [r.id for r in rentals]
            contract.history_rental_ids = rental_ids

            for r in rentals:
                r.status = '空闲中'
                r.customer_id = None

            # 删除 contract_rental 关联
            db.execute(
                sa_delete(contract_rental).where(contract_rental.c.contract_id == contract_id)
            )

            db.commit()
            print(f"[send_manual_email] 回收完成: contract={contract.id[:8]}, rentals={len(rentals)}")

        print(f"[send_manual_email] 成功: trigger={trigger_type}, contract={contract.id[:8]}")
    except Exception as e:
        db.rollback()
        print(f"[send_manual_email] 失败: {e}")
    finally:
        db.close()


@celery_app.task(name='scheduler.tasks.check_expired_rentals')
def check_expired_rentals():
    """
    每天 00:00：到期当天发送回收通知邮件，合同状态→expired（不回收）
    实际回收由 check_reclaim_expired 在次日 00:00 执行。
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.mail.services import send_merged_email_by_contract

        today = date.today()

        contracts = (
            db.query(Contract)
            .filter(
                Contract.end_date == today,
                Contract.status.in_(['active', 'expiring']),
            )
            .all()
        )

        if not contracts:
            print("[tasks] check_expired_rentals: 没有今日到期的合同")
            return

        print(f"[tasks] check_expired_rentals: 找到 {len(contracts)} 个今日到期合同，发送回收通知")

        for c in contracts:
            try:
                send_merged_email_by_contract(db, c, 'reclaim')
                c.status = 'expired'
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[tasks] 合同 {c.id[:8]} 回收通知失败: {e}")

    except Exception as e:
        print(f"[tasks] check_expired_rentals 异常: {e}")
    finally:
        db.close()
