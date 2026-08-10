#!/usr/bin/env python3
"""
一次性迁移脚本：确保每个 project_type 都有独立的附件分类

运行方式：cd /data/CronMail/backend && python migrate_attachment_categories.py

逻辑：
1. 查询所有 contract_type='project' 且 project_type IS NULL 且 is_active=true 的兜底分类
2. 从 project_contract 表获取所有不同的 project_type
3. 处理重复的兜底分类：每个 code 保留一条（不分配），其余软删除或分配
4. 对每个 project_type + 每个目标 code：
   - 已存在同 code 分类 → 跳过
   - 有可用的兜底分类 → 更新其 project_type（移动）
   - 无兜底分类可用 → 从已存在的同 code 分类中找模板，创建新分类
5. 幂等：可重复执行，不会重复创建或出错

注意：不修改 AttachmentItem、Attachment、AttachmentStatus 的任何记录。
"""
import sys
import uuid
sys.path.insert(0, '.')

from src.core.database import SessionLocal
from src.attachment.models import AttachmentCategory
from src.project.models import ProjectContract


def generate_uuid() -> str:
    return str(uuid.uuid4())


# 需要确保每个 project_type 下都有的分类 code
TARGET_CODES = [
    "contract_material",
    "delivery_material",
    "process_material",
    "payment_receipt",
]


def _find_template(db, code: str):
    """查找可作为模板的分类：优先找 project_type!=NULL 的，其次找兜底的"""
    cat = (
        db.query(AttachmentCategory)
        .filter(
            AttachmentCategory.contract_type == "project",
            AttachmentCategory.code == code,
            AttachmentCategory.is_active == True,
        )
        .order_by(AttachmentCategory.project_type.nullsfirst())
        .first()
    )
    return cat


def migrate():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("附件分类迁移：确保每个 project_type 都有独立分类")
        print("=" * 60)

        # ============================================================
        # 1. 获取所有 project_type（从 project_contract 表）
        # ============================================================
        project_type_rows = (
            db.query(ProjectContract.project_type)
            .filter(ProjectContract.project_type.isnot(None))
            .filter(ProjectContract.project_type != "")
            .distinct()
            .all()
        )
        project_types = sorted([row[0] for row in project_type_rows])
        print(f"\n[1] 发现 {len(project_types)} 个 project_type: {project_types}")

        if not project_types:
            print("没有找到任何 project_type，无需迁移。")
            return

        # ============================================================
        # 2. 获取所有兜底分类（project_type IS NULL, contract_type='project'）
        # ============================================================
        base_categories = (
            db.query(AttachmentCategory)
            .filter(
                AttachmentCategory.contract_type == "project",
                AttachmentCategory.project_type.is_(None),
                AttachmentCategory.is_active == True,
            )
            .all()
        )
        print(f"\n[2] 找到 {len(base_categories)} 个活跃的兜底分类:")
        for cat in base_categories:
            print(f"    id={cat.id}  name={cat.name}  code={cat.code}")

        # 按 code 分组
        by_code: dict[str, list] = {}
        for cat in base_categories:
            by_code.setdefault(cat.code, []).append(cat)

        # ============================================================
        # 3. 处理重复的兜底分类
        #    - 每个 code 保留一条作为兜底（不分配 project_type）
        #    - 其余多余的放入"可分配池"供后续移动
        # ============================================================
        print(f"\n[3] 处理重复的兜底分类...")
        dedup_soft_deleted = 0
        # 可分配池：code → [多余的兜底分类]
        available_pool: dict[str, list] = {}

        for code, cats in by_code.items():
            if len(cats) > 1:
                # 保留第一条作为兜底，其余放入可分配池
                available_pool[code] = cats[1:]
                print(f"    code={code}: 保留兜底 id={cats[0].id}, "
                      f"剩余 {len(cats[1:])} 条进入可分配池")
            else:
                available_pool[code] = []

        if available_pool:
            total_available = sum(len(v) for v in available_pool.values())
            print(f"    可分配池共 {total_available} 条")
        else:
            print("    无可分配的多余分类")

        # ============================================================
        # 4. 为每个 project_type 确保有所有 TARGET_CODES 的分类
        # ============================================================
        print(f"\n[4] 为每个 project_type 确保分类...")
        total_moved = 0       # 从可分配池移动
        total_created = 0     # 新建
        total_skipped = 0     # 已存在
        total_missing_template = 0  # 无模板无法创建

        for pt in project_types:
            print(f"\n  --- project_type = '{pt}' ---")
            for target_code in TARGET_CODES:
                # 4a. 检查该 project_type 下是否已有同 code 的分类
                existing = (
                    db.query(AttachmentCategory)
                    .filter(
                        AttachmentCategory.contract_type == "project",
                        AttachmentCategory.project_type == pt,
                        AttachmentCategory.code == target_code,
                        AttachmentCategory.is_active == True,
                    )
                    .first()
                )
                if existing:
                    print(f"    [{target_code}] 已存在 (id={existing.id})，跳过")
                    total_skipped += 1
                    continue

                # 4b. 尝试从可分配池中取一条（移动）
                pool = available_pool.get(target_code, [])
                if pool:
                    base_cat = pool.pop(0)
                    base_cat.project_type = pt
                    db.flush()
                    print(f"    [{target_code}] 移动: id={base_cat.id} project_type: NULL → '{pt}'")
                    total_moved += 1
                    continue

                # 4c. 无可用兜底分类 → 从模板创建新分类
                template = _find_template(db, target_code)
                if not template:
                    print(f"    [{target_code}] 无模板可用，跳过")
                    total_missing_template += 1
                    continue

                new_cat = AttachmentCategory(
                    id=generate_uuid(),
                    contract_type="project",
                    project_type=pt,
                    name=template.name,
                    code=template.code,
                    sort_order=template.sort_order,
                    is_active=True,
                )
                db.add(new_cat)
                db.flush()
                print(f"    [{target_code}] 新建: id={new_cat.id} (模板来自 id={template.id})")
                total_created += 1

        # ============================================================
        # 5. 提交
        # ============================================================
        db.commit()

        print(f"\n{'=' * 60}")
        print("迁移完成！")
        print(f"  project_type 数量:     {len(project_types)}")
        print(f"  已存在跳过:            {total_skipped}")
        print(f"  移动(兜底→专属):       {total_moved}")
        print(f"  新建分类:              {total_created}")
        print(f"  无模板跳过:            {total_missing_template}")

        # 最终状态：列出所有 project 类型的活跃分类
        final_cats = (
            db.query(AttachmentCategory)
            .filter(
                AttachmentCategory.contract_type == "project",
                AttachmentCategory.is_active == True,
            )
            .order_by(
                AttachmentCategory.project_type,
                AttachmentCategory.sort_order,
            )
            .all()
        )
        print(f"\n最终分类状态 ({len(final_cats)} 条):")
        for cat in final_cats:
            pt_display = cat.project_type or "(兜底)"
            print(f"    [{pt_display}] {cat.name} (code={cat.code}) id={cat.id}")

    except Exception as e:
        db.rollback()
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
