"""数据迁移：把兜底分类复制到每个项目类型

执行方式：kubectl exec -n cronmail deploy/cronmail-backend-api -- python /app/migrate_project_type_categories.py

幂等：重复执行不会重复创建。
"""

import os, sys, uuid
sys.path.insert(0, '/app')
from src.core.database import SessionLocal
from src.attachment.models import AttachmentCategory, AttachmentItem

db = SessionLocal()

try:
    # 1. 获取所有项目类型
    from src.project.models import ProjectContract
    project_types = [
        row[0] for row in db.query(ProjectContract.project_type)
        .filter(ProjectContract.project_type.isnot(None))
        .distinct()
        .all()
    ]
    print(f"项目类型: {project_types}")

    # 2. 获取所有兜底分类（project_type IS NULL）
    base_categories = db.query(AttachmentCategory).filter(
        AttachmentCategory.contract_type == 'project',
        AttachmentCategory.project_type.is_(None),
        AttachmentCategory.is_active == True,
    ).all()
    print(f"兜底分类: {len(base_categories)} 个")

    # 3. 获取所有兜底分类的子项
    base_category_ids = [c.id for c in base_categories]
    base_items = db.query(AttachmentItem).filter(
        AttachmentItem.category_id.in_(base_category_ids),
        AttachmentItem.is_active == True,
    ).all()
    print(f"兜底子项: {len(base_items)} 个")

    created_cats = 0
    created_items = 0
    skipped_cats = 0
    skipped_items = 0

    # 4. 对每个项目类型，复制分类和子项
    for pt in project_types:
        print(f"\n--- 处理项目类型: {pt} ---")

        for base_cat in base_categories:
            # 检查是否已存在
            existing = db.query(AttachmentCategory).filter(
                AttachmentCategory.contract_type == 'project',
                AttachmentCategory.project_type == pt,
                AttachmentCategory.code == base_cat.code,
                AttachmentCategory.is_active == True,
            ).first()

            if existing:
                print(f"  分类 [{base_cat.name}] 已存在 (code={base_cat.code})，跳过")
                skipped_cats += 1
                target_cat = existing
            else:
                new_cat = AttachmentCategory(
                    contract_type='project',
                    name=base_cat.name,
                    code=base_cat.code,
                    sort_order=base_cat.sort_order,
                    project_type=pt,
                )
                db.add(new_cat)
                db.flush()
                print(f"  创建分类 [{base_cat.name}] (code={base_cat.code}) → {new_cat.id}")
                created_cats += 1
                target_cat = new_cat

            # 复制子项
            for base_item in base_items:
                if base_item.category_id != base_cat.id:
                    continue

                existing_item = db.query(AttachmentItem).filter(
                    AttachmentItem.category_id == target_cat.id,
                    AttachmentItem.name == base_item.name,
                    AttachmentItem.is_active == True,
                ).first()

                if existing_item:
                    skipped_items += 1
                    continue

                new_item = AttachmentItem(
                    category_id=target_cat.id,
                    name=base_item.name,
                    description=base_item.description,
                    expected_type=base_item.expected_type,
                    sort_order=base_item.sort_order,
                )
                db.add(new_item)
                print(f"    子项 [{base_item.name}]")

    db.commit()
    print(f"\n=== 迁移完成 ===")
    print(f"新建分类: {created_cats}, 跳过: {skipped_cats}")
    print(f"新建子项: {len(base_items) * len(project_types) - skipped_items}")

finally:
    db.close()
