"""
数据迁移脚本：从现有数据中提取 project_type 值写入 project_type 表

来源：
1. project_contract 表中的 project_type 字段（用户手动填写）
2. attachment_category 表中的 project_type 字段

策略：
- 从两张表中提取所有不重复的 project_type 值（排除 NULL 和空字符串）
- 写入 project_type 表（去重，按字母顺序排序）
- 幂等设计：已存在的 name 跳过不插入

执行方式：
    cd /data/CronMail/backend
    python migrate_project_types.py
"""
import os
import sys
import uuid

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import SessionLocal, engine, Base

# 确保表已创建
import src.project.models  # noqa: E402, F401
Base.metadata.create_all(bind=engine)


def migrate():
    db = SessionLocal()
    try:
        from sqlalchemy import text

        # 从 project_contract 提取
        result1 = db.execute(
            text("SELECT DISTINCT project_type FROM project_contract WHERE project_type IS NOT NULL AND project_type != ''")
        ).fetchall()

        # 从 attachment_category 提取
        result2 = db.execute(
            text("SELECT DISTINCT project_type FROM attachment_category WHERE project_type IS NOT NULL AND project_type != ''")
        ).fetchall()

        # 合并去重
        all_types = set()
        for row in result1:
            all_types.add(row[0])
        for row in result2:
            all_types.add(row[0])

        print(f"[INFO] 发现 {len(all_types)} 个不重复的 project_type 值: {all_types}")

        # 获取已存在的 project_type
        from src.project.models import ProjectType
        existing_names = set(
            row[0] for row in db.query(ProjectType.name).filter(ProjectType.is_active == True).all()
        )

        inserted = 0
        skipped = 0
        for idx, name in enumerate(sorted(all_types)):
            if name in existing_names:
                print(f"[SKIP] '{name}' 已存在，跳过")
                skipped += 1
                continue
            pt = ProjectType(
                id=str(uuid.uuid4()),
                name=name,
                sort_order=idx,
                is_active=True,
            )
            db.add(pt)
            print(f"[INSERT] '{name}' (sort_order={idx})")
            inserted += 1

        db.commit()
        print(f"\n[DONE] 迁移完成: 插入 {inserted} 条，跳过 {skipped} 条")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
