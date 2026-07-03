"""
Celery 定时任务
- check_expiring_rentals: 每天 08:00，扫描即将到期的合同，按合同合并发送
- check_expired_rentals: 每天 00:00，扫描当天到期的合同，按合同合并发送
"""
from datetime import timedelta

from sqlalchemy import delete as sa_delete

from src.core.database import SessionLocal
from src.core.timezone import local_today
from .celery_app import celery_app
from src.mail.services import send_merged_email_by_contract
from src.contract.models import contract_rental


@celery_app.task(name='scheduler.tasks.check_expiring_rentals')
def check_expiring_rentals():
    """
    每天 08:00 扫描即将到期的合同，合并发送临期提醒 (expiry_warning)

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
        days_list = sorted(list(set([int(d.strip()) for d in days_str.split(',') if d.strip().isdigit()])))

        today = local_today()

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
                    print(f"[tasks] 合同 {c.id[:8]} 临期({day_offset}天) 邮件失败: {e}")

        print(f"[tasks] check_expiring_rentals: 处理完成, 配置天数={days_list}")
    except Exception as e:
        print(f"[tasks] check_expiring_rentals 异常: {e}")
    finally:
        db.close()


def _reclaim_contract(db, contract):
    """执行合同回收：改状态、清关联、删中间表。调用方负责 commit/rollback"""
    contract.status = 'reclaimed'
    contract.history_rental_ids = [r.id for r in contract.rentals]
    for r in contract.rentals:
        r.status = '空闲中'
        r.customer_id = None
    db.execute(sa_delete(contract_rental).where(contract_rental.c.contract_id == contract.id))


@celery_app.task(name='scheduler.tasks.check_reclaim_expired')
def check_reclaim_expired():
    """
    每天 00:01：对状态为 expired 的合同执行实际回收（清理关联、释放设备）
    回收成功后发送 reclaim 通知邮件（失败不影响回收结果）
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.mail.services import send_merged_email_by_contract

        today = local_today()
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
                _reclaim_contract(db, c)
                db.commit()
                print(f"[tasks] 合同 {c.id[:8]} 回收完成, 设备 {len(c.history_rental_ids)} 台")
                # 回收成功后发送 reclaim 通知邮件
                try:
                    send_merged_email_by_contract(db, c, 'reclaim')
                except Exception as e:
                    print(f"[tasks] 合同 {c.id[:8]} 回收通知邮件发送失败（不影响回收）: {e}")
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

    V2 行为：
    - reclaim 类型：先执行回收，再发送回收通知邮件（回收失败则不发邮件）
    - 其他类型：直接发送邮件
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.mail.services import send_merged_email_by_contract

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            print(f"[send_manual_email] 合同不存在: {contract_id}")
            return

        # reclaim 类型：先回收再发邮件（回收通知 = 资源已回收）
        if trigger_type == 'reclaim':
            if contract.status != 'expired':
                print(f"[send_manual_email] 回收被拒绝: 合同 {contract.id[:8]} 状态为 '{contract.status}'，仅已到期合同可执行回收")
                return
            _reclaim_contract(db, contract)
            db.commit()
            print(f"[send_manual_email] 回收完成: contract={contract.id[:8]}, rentals={len(contract.history_rental_ids or [])}")
            # 回收成功后发送 reclaim 通知邮件
            try:
                send_merged_email_by_contract(db, contract, 'reclaim')
            except Exception as e:
                print(f"[send_manual_email] 回收通知邮件发送失败（不影响回收）: {e}")
        else:
            send_merged_email_by_contract(db, contract, trigger_type)

        print(f"[send_manual_email] 成功: trigger={trigger_type}, contract={contract.id[:8]}")
    except Exception as e:
        db.rollback()
        print(f"[send_manual_email] 失败: {e}")
    finally:
        db.close()


@celery_app.task(name='scheduler.tasks.check_expired_rentals')
def check_expired_rentals():
    """
    每天 08:00：到期当天发送到期提醒邮件 (expiry_notice)，合同状态→expired（不回收）
    邮件发送后（无论成败）都将合同状态改为 expired，解除与邮件成败的耦合。
    实际回收由 check_reclaim_expired 在次日 00:01 执行。
    """
    db = SessionLocal()
    try:
        from src.contract.models import Contract
        from src.mail.services import send_merged_email_by_contract

        today = local_today()

        contracts = (
            db.query(Contract)
            .filter(
                Contract.end_date <= today,
                Contract.status.in_(['active', 'expiring']),
            )
            .all()
        )

        if not contracts:
            print("[tasks] check_expired_rentals: 没有到期合同需要处理")
            return

        missed_count = sum(1 for c in contracts if c.end_date < today)
        print(
            f"[tasks] check_expired_rentals: 找到 {len(contracts)} 个到期合同发送到期提醒"
            + (f" (其中 {missed_count} 个非今日到期，可能是之前漏处理的)" if missed_count else "")
        )

        for c in contracts:
            if c.end_date < today:
                print(
                    f"[tasks] WARNING: 合同 {c.id[:8]} end_date={c.end_date} < today={today}, "
                    f"可能是之前 Beat 宕机漏处理的合同"
                )
            try:
                send_merged_email_by_contract(db, c, 'expiry_notice')
            except Exception as e:
                print(f"[tasks] 合同 {c.id[:8]} 到期提醒邮件失败: {e}")
            # 无论邮件成败，合同状态都改为 expired
            c.status = 'expired'
            db.commit()
            print(f"[tasks] 合同 {c.id[:8]} 状态已更新为 expired")

    except Exception as e:
        print(f"[tasks] check_expired_rentals 异常: {e}")
    finally:
        db.close()
