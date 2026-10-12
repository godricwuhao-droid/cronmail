"""
存量附件迁移脚本（ADR-020：asset-ops 附件存储物理隔离）

背景：
    ADR-019 拆分后 asset-ops 与 cronmail 两平台共享 NFS 192.168.180.50:/cronmail，
    附件混在同一目录树（按 contract_type/contract_id/item_id 分层，仅靠 UUID 区分）。
    ADR-020 将 asset-ops 的 PV 指向独立子目录 /cronmail/asset-ops，
    本脚本负责把存量附件从旧目录树迁移到新目录树。

为什么不能整目录复制：
    cronmail 库与 asset_ops 库都有 compute_leasing 合同，两平台的
    compute_leasing/ 附件混在同一源目录。必须以 **asset_ops 库** attachment 表
    的 file_path 集合为白名单精确挑选文件，只复制属于 asset_ops 合同的文件。

用法（在 backend 目录下，使用项目 venv）：
    # 预演（不写任何文件，安全）
    python scripts/migrate_asset_ops_uploads.py \
        --source-root /mnt/nfs/cronmail \
        --target-root /mnt/nfs/cronmail/asset-ops \
        --dry-run

    # 正式执行
    python scripts/migrate_asset_ops_uploads.py \
        --source-root /mnt/nfs/cronmail \
        --target-root /mnt/nfs/cronmail/asset-ops

数据库连接：
    读取环境变量 DATABASE_URL（默认指向 asset_ops 库，见 src/core/config.py）。
    执行前请确认 DATABASE_URL 指向 **asset_ops** 库而非 cronmail 库。

安全说明：
    - 只复制（copy2），不移动、不删除源文件；源目录保持原样。
    - 幂等：目标已存在且大小一致则跳过。
    - 路径白名单校验：file_path 含 ".." 或解析后越出目标根目录的记录直接跳过并告警。
    - 本脚本本身不对生产 NFS 做任何操作，是否执行由运维在挂载环境手动决定。
"""
import argparse
import os
import shutil
import sys

# 保证可从 backend/ 目录外运行：把 backend 根加入 sys.path
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from sqlalchemy.orm import Session  # noqa: E402

from src.core.database import SessionLocal  # noqa: E402
from src.attachment.models import Attachment  # noqa: E402


def _is_within(child: str, parent: str) -> bool:
    """判断 child 路径是否位于 parent 目录内（基于 realpath 防符号链接逃逸）"""
    child_real = os.path.realpath(child)
    parent_real = os.path.realpath(parent)
    return child_real == parent_real or child_real.startswith(parent_real + os.sep)


def fetch_file_path_whitelist(db: Session) -> list[str]:
    """从 asset_ops 库读取 attachment 表的 file_path 白名单（去重）"""
    rows = db.query(Attachment.file_path).distinct().all()
    return [r[0] for r in rows if r[0]]


def migrate(source_root: str, target_root: str, dry_run: bool) -> int:
    """按白名单复制文件，返回进程退出码"""
    source_root = os.path.abspath(source_root)
    target_root = os.path.abspath(target_root)

    print(f"源目录:   {source_root}")
    print(f"目标目录: {target_root}")
    print(f"模式:     {'DRY-RUN（预演，不写文件）' if dry_run else '正式执行'}")
    print()

    db: Session = SessionLocal()
    try:
        whitelist = fetch_file_path_whitelist(db)
    finally:
        db.close()

    if not whitelist:
        print("asset_ops 库 attachment 表无 file_path 记录，无需迁移，安全退出。")
        return 0

    print(f"白名单文件数: {len(whitelist)}")
    print()

    copied = 0      # 实际复制（dry-run 下为“将复制”）
    skipped = 0     # 目标已存在且大小一致
    missing = 0     # 源文件不存在
    rejected = 0    # 路径校验不通过（越界/非法）
    errors = 0      # 复制过程异常

    for file_path in whitelist:
        # 归一化：统一用 / 分隔，去掉开头 /
        rel = file_path.replace("\\", "/").lstrip("/")
        if not rel or ".." in rel.split("/"):
            print(f"[REJECT] 非法路径，跳过: {file_path}")
            rejected += 1
            continue

        src = os.path.join(source_root, rel)
        dst = os.path.join(target_root, rel)

        # 双重保险：目标必须落在 target_root 内
        if not _is_within(dst, target_root):
            print(f"[REJECT] 路径越出目标根目录，跳过: {file_path}")
            rejected += 1
            continue

        if not os.path.isfile(src):
            print(f"[MISSING] 源文件不存在: {rel}")
            missing += 1
            continue

        if os.path.isfile(dst):
            if os.path.getsize(dst) == os.path.getsize(src):
                print(f"[SKIP]    已存在且大小一致: {rel}")
                skipped += 1
                continue
            print(f"[WARN]    目标已存在但大小不一致，将覆盖: {rel}")

        if dry_run:
            print(f"[WILL-COPY] {rel}")
            copied += 1
            continue

        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"[COPIED]  {rel}")
            copied += 1
        except OSError as e:
            print(f"[ERROR]   复制失败 {rel}: {e}")
            errors += 1

    print()
    print("=" * 50)
    if dry_run:
        print(f"预演统计: 将复制={copied}  跳过(已存在)={skipped}  "
              f"缺失={missing}  拒绝={rejected}")
    else:
        print(f"迁移统计: 复制={copied}  跳过(已存在)={skipped}  "
              f"缺失={missing}  拒绝={rejected}  失败={errors}")
    if missing:
        print(f"警告: 有 {missing} 个白名单文件在源目录缺失，请人工核查！")
    print("=" * 50)

    if errors:
        return 2
    if missing:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="asset-ops 存量附件迁移（按 asset_ops 库 file_path 白名单精确复制）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("用法", 1)[-1].split("数据库连接", 1)[0],
    )
    parser.add_argument(
        "--source-root", required=True,
        help="源目录根（NFS 挂载点下旧目录树根，如 /mnt/nfs/cronmail）",
    )
    parser.add_argument(
        "--target-root", required=True,
        help="目标目录根（如 /mnt/nfs/cronmail/asset-ops）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预演模式：只打印将执行的操作，不写任何文件",
    )
    args = parser.parse_args()

    if os.path.abspath(args.source_root) == os.path.abspath(args.target_root):
        print("错误: source-root 与 target-root 不能相同")
        sys.exit(2)

    sys.exit(migrate(args.source_root, args.target_root, args.dry_run))


if __name__ == "__main__":
    main()
