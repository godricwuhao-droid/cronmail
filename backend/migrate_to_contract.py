"""
数据迁移脚本：将现有 RentalRecord 迁移到 Contract 模型

策略：
1. 按 (customer_id, start_date, end_date, billing_model) 分组
2. 每组创建一个 Contract
3. 所有同组设备链接到该 Contract
4. 迁移 rental_contact → contract_contact（去重）

执行方式：python migrate_to_contract.py
"""
from src.core.database import SessionLocal
from src.core.timezone import local_now
from src.rental.models import RentalRecord, rental_contact
from src.customer.models import Customer, Contact
from src.contract.models import Contract, contract_rental, contract_contact
# 以下导入确保 SQLAlchemy mapper registry 中注册所有依赖模块
import src.mail.models  # noqa: F401  (EmailLog 被 RentalRecord relationship 引用)
import src.template.models  # noqa: F401  (EmailTemplate 被 EmailLog relationship 引用)
from collections import defaultdict


def migrate():
    db = SessionLocal()
    try:
        # 1. 获取所有 not-reclaimed 的 rental
        rentals = db.query(RentalRecord).filter(
            RentalRecord.status != "reclaimed"
        ).all()

        if not rentals:
            print("没有需要迁移的租赁记录")
            return

        # 2. 按分组键分组
        groups = defaultdict(list)
        for r in rentals:
            key = (r.customer_id, r.start_date, r.end_date, r.billing_model or "monthly")
            groups[key].append(r)

        print(f"共 {len(rentals)} 条租赁记录，分为 {len(groups)} 个合同组")

        # 3. 为每组创建 Contract
        for (cid, sdate, edate, bmodel), group_rentals in groups.items():
            customer = db.query(Customer).filter(Customer.id == cid).first()
            if not customer:
                print(f"  跳过: 客户 {cid} 不存在")
                continue

            # 生成合同名称
            contract_name = f"{customer.name} - {sdate} 合同"

            contract = Contract(
                customer_id=cid,
                name=contract_name,
                start_date=sdate,
                end_date=edate,
                billing_model=bmodel,
                status="active",
                created_at=local_now(),
                updated_at=local_now(),
            )
            db.add(contract)
            db.flush()

            # 关联设备
            for r in group_rentals:
                db.execute(
                    contract_rental.insert().values(
                        contract_id=contract.id,
                        rental_id=r.id,
                    )
                )

            # 迁移联系人
            contact_set = set()  # (contact_id, recipient_type) 去重
            for r in group_rentals:
                rows = db.execute(
                    rental_contact.select().where(rental_contact.c.rental_id == r.id)
                ).fetchall()
                for row in rows:
                    contact_set.add((row.contact_id, row.recipient_type))

            for contact_id, rtype in contact_set:
                db.execute(
                    contract_contact.insert().values(
                        contract_id=contract.id,
                        contact_id=contact_id,
                        recipient_type=rtype,
                    )
                )

            print(
                f"  合同 [{contract.id[:8]}]: {contract_name}, "
                f"设备 {len(group_rentals)} 台, 联系人 {len(contact_set)} 个"
            )

        db.commit()
        print(f"迁移完成: 创建 {len(groups)} 个合同")

    except Exception as e:
        db.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
