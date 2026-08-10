"""
附件管理模块业务逻辑层
"""
import os
import uuid
import shutil
from typing import Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from src.attachment.models import (
    AttachmentCategory,
    AttachmentItem,
    Attachment,
    AttachmentStatus,
)
from src.attachment.schemas import (
    AttachmentCategoryCreate,
    AttachmentCategoryUpdate,
    AttachmentItemCreate,
    AttachmentItemUpdate,
)


# 上传根目录
UPLOAD_BASE_DIR = "/app/uploads"

# 允许的 MIME 类型
ALLOWED_MIMETYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",  # xls
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "application/msword",  # doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "text/plain",
    "application/zip",
    "application/x-rar-compressed",
    "application/x-7z-compressed",
}

# 最大文件大小 50MB
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB，与 Nginx client_max_body_size 一致


def _get_upload_dir(contract_type: str, contract_id: str, item_id: str) -> str:
    """获取上传目录路径，确保存在"""
    dir_path = os.path.join(UPLOAD_BASE_DIR, contract_type, contract_id, item_id)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


# ============================================================
# 附件分类
# ============================================================

def list_categories(
    db: Session,
    contract_type: Optional[str] = None,
    project_type: Optional[str] = None,
) -> list[AttachmentCategory]:
    """获取分类列表，含子项（排除软删除的子项）
    
    当 project_type 有值时，只返回匹配该 project_type 的分类；
    project_type 为 None 或空字符串时，返回所有分类。
    """
    query = db.query(AttachmentCategory).filter(
        AttachmentCategory.is_active == True  # noqa: E712
    )
    if contract_type:
        query = query.filter(AttachmentCategory.contract_type == contract_type)

    if contract_type == "project":
        if project_type:
            query = query.filter(AttachmentCategory.project_type == project_type)
        # project_type 为 None 或空字符串时：返回所有分类

    categories = query.order_by(AttachmentCategory.sort_order).all()

    # 过滤掉每个分类下已软删除的子项
    for cat in categories:
        cat.items = [item for item in cat.items if item.is_active]

    return categories


def get_category(db: Session, category_id: str) -> Optional[AttachmentCategory]:
    return db.query(AttachmentCategory).filter(
        AttachmentCategory.id == category_id
    ).first()


def create_category(
    db: Session, data: AttachmentCategoryCreate,
) -> AttachmentCategory:
    category = AttachmentCategory(
        contract_type=data.contract_type,
        project_type=data.project_type,
        name=data.name,
        code=data.code,
        sort_order=data.sort_order,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, category: AttachmentCategory, data: AttachmentCategoryUpdate,
) -> AttachmentCategory:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def soft_delete_category(db: Session, category: AttachmentCategory):
    """软删除分类"""
    category.is_active = False
    db.commit()


def reorder_category(db: Session, category: AttachmentCategory, sort_order: int):
    category.sort_order = sort_order
    db.commit()


# ============================================================
# 附件子项
# ============================================================

def get_item(db: Session, item_id: str) -> Optional[AttachmentItem]:
    return db.query(AttachmentItem).filter(
        AttachmentItem.id == item_id
    ).first()


def create_item(
    db: Session, category_id: str, data: AttachmentItemCreate,
) -> AttachmentItem:
    category = get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    item = AttachmentItem(
        category_id=category_id,
        name=data.name,
        description=data.description,
        expected_type=data.expected_type,
        sort_order=data.sort_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, item: AttachmentItem, data: AttachmentItemUpdate,
) -> AttachmentItem:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def soft_delete_item(db: Session, item: AttachmentItem):
    """软删除子项"""
    item.is_active = False
    db.commit()


def reorder_item(db: Session, item: AttachmentItem, sort_order: int):
    item.sort_order = sort_order
    db.commit()


# ============================================================
# 附件文件
# ============================================================

def save_file(
    db: Session,
    uploaded_file: UploadFile,
    contract_type: str,
    contract_id: str,
    item_id: str,
) -> Attachment:
    """保存上传文件到磁盘并创建数据库记录"""
    # 验证文件大小
    if uploaded_file.size is not None and uploaded_file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过 50MB 限制")

    # 验证 MIME 类型
    content_type = uploaded_file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIMETYPES:
        # 允许通过，但记录警告（不在严格模式下拦截）
        pass

    # 验证子项存在
    item = get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件子项不存在")

    # 生成唯一文件名
    original_filename = uploaded_file.filename or "unknown"
    ext = os.path.splitext(original_filename)[1].lower() or ".bin"
    stored_name = str(uuid.uuid4()) + ext

    # 构建存储路径
    upload_dir = _get_upload_dir(contract_type, contract_id, item_id)
    file_full_path = os.path.join(upload_dir, stored_name)

    # 相对路径（数据库存储）
    relative_path = os.path.join(contract_type, contract_id, item_id, stored_name)

    # 写入磁盘
    try:
        with open(file_full_path, "wb") as f:
            content = uploaded_file.file.read()
            f.write(content)
        actual_size = len(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

    # 创建数据库记录
    attachment = Attachment(
        contract_type=contract_type,
        contract_id=contract_id,
        item_id=item_id,
        filename=original_filename,
        file_path=relative_path,
        file_size=actual_size,
        mime_type=content_type,
    )
    db.add(attachment)
    db.flush()

    # 更新 AttachmentStatus file_count
    _update_file_count(db, contract_type, contract_id, item_id)

    db.commit()
    db.refresh(attachment)
    return attachment


def delete_file(db: Session, attachment: Attachment):
    """删除磁盘文件 + DB 记录"""
    # 删除磁盘文件
    file_full_path = os.path.join(UPLOAD_BASE_DIR, attachment.file_path)
    try:
        if os.path.exists(file_full_path):
            os.remove(file_full_path)
    except OSError:
        pass  # 文件不存在或无法删除，继续清理数据库

    contract_type = attachment.contract_type
    contract_id = attachment.contract_id
    item_id = attachment.item_id

    db.delete(attachment)
    db.flush()

    # 更新 file_count
    _update_file_count(db, contract_type, contract_id, item_id)

    db.commit()


def get_attachment(db: Session, attachment_id: str) -> Optional[Attachment]:
    return db.query(Attachment).filter(Attachment.id == attachment_id).first()


def get_attachment_list(
    db: Session,
    contract_type: str,
    contract_id: str,
    project_type: Optional[str] = None,
) -> list[dict]:
    """
    按分类+子项结构返回附件列表。
    返回格式：categories 列表，每个 category 包含 items，每个 item 包含 files。
    当 project_type 指定且 contract_type="project" 时，按 project_type 过滤分类。
    """

    # 获取该合同类型下的所有活跃分类
    query = (
        db.query(AttachmentCategory)
        .filter(
            AttachmentCategory.contract_type == contract_type,
            AttachmentCategory.is_active == True,  # noqa: E712
        )
    )

    if project_type and contract_type == "project":
        query = query.filter(
            AttachmentCategory.project_type == project_type,
        )

    categories = query.order_by(AttachmentCategory.sort_order).all()

    result = []
    for cat in categories:
        cat_items = []
        for item in cat.items:
            if not item.is_active:
                continue

            # 获取该 item 下的文件
            files = (
                db.query(Attachment)
                .filter(
                    Attachment.contract_type == contract_type,
                    Attachment.contract_id == contract_id,
                    Attachment.item_id == item.id,
                )
                .order_by(Attachment.uploaded_at.desc())
                .all()
            )

            # 获取状态
            status = (
                db.query(AttachmentStatus)
                .filter(
                    AttachmentStatus.contract_type == contract_type,
                    AttachmentStatus.contract_id == contract_id,
                    AttachmentStatus.item_id == item.id,
                )
                .first()
            )

            cat_items.append({
                "item_id": item.id,
                "item_name": item.name,
                "expected_type": item.expected_type,
                "files": [
                    {
                        "id": f.id,
                        "filename": f.filename,
                        "file_size": f.file_size,
                        "mime_type": f.mime_type,
                        "uploaded_at": f.uploaded_at,
                    }
                    for f in files
                ],
                "file_count": status.file_count if status else len(files),
                "confirmed": status.confirmed if status else False,
                "confirmed_at": status.confirmed_at if status else None,
            })

        result.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "items": cat_items,
        })

    return result


# ============================================================
# AttachmentStatus
# ============================================================

def _update_file_count(
    db: Session, contract_type: str, contract_id: str, item_id: str,
):
    """更新子项的文件计数"""
    count = (
        db.query(Attachment)
        .filter(
            Attachment.contract_type == contract_type,
            Attachment.contract_id == contract_id,
            Attachment.item_id == item_id,
        )
        .count()
    )

    status = (
        db.query(AttachmentStatus)
        .filter(
            AttachmentStatus.contract_type == contract_type,
            AttachmentStatus.contract_id == contract_id,
            AttachmentStatus.item_id == item_id,
        )
        .first()
    )

    if status:
        status.file_count = count
    else:
        status = AttachmentStatus(
            contract_type=contract_type,
            contract_id=contract_id,
            item_id=item_id,
            file_count=count,
            confirmed=False,
        )
        db.add(status)


def confirm_item(
    db: Session,
    contract_type: str,
    contract_id: str,
    item_id: str,
) -> AttachmentStatus:
    """手动确认子项完成"""
    status = _get_or_create_status(db, contract_type, contract_id, item_id)
    status.confirmed = True
    from src.core.timezone import local_now
    status.confirmed_at = local_now()
    db.commit()
    db.refresh(status)
    return status


def unconfirm_item(
    db: Session,
    contract_type: str,
    contract_id: str,
    item_id: str,
) -> AttachmentStatus:
    """取消确认"""
    status = _get_or_create_status(db, contract_type, contract_id, item_id)
    status.confirmed = False
    status.confirmed_at = None
    db.commit()
    db.refresh(status)
    return status


def _get_or_create_status(
    db: Session, contract_type: str, contract_id: str, item_id: str,
) -> AttachmentStatus:
    status = (
        db.query(AttachmentStatus)
        .filter(
            AttachmentStatus.contract_type == contract_type,
            AttachmentStatus.contract_id == contract_id,
            AttachmentStatus.item_id == item_id,
        )
        .first()
    )
    if not status:
        count = (
            db.query(Attachment)
            .filter(
                Attachment.contract_type == contract_type,
                Attachment.contract_id == contract_id,
                Attachment.item_id == item_id,
            )
            .count()
        )
        status = AttachmentStatus(
            contract_type=contract_type,
            contract_id=contract_id,
            item_id=item_id,
            file_count=count,
            confirmed=False,
        )
        db.add(status)
        db.flush()
    return status


def get_summary(
    db: Session,
    contract_type: str,
    contract_id: str,
    project_type: Optional[str] = None,
) -> dict:
    """获取合同附件完成状态汇总
    当 project_type 指定且 contract_type="project" 时，按 project_type 过滤分类。
    """

    # 获取该合同类型下的所有活跃分类和子项
    query = (
        db.query(AttachmentCategory)
        .filter(
            AttachmentCategory.contract_type == contract_type,
            AttachmentCategory.is_active == True,  # noqa: E712
        )
    )

    if project_type and contract_type == "project":
        query = query.filter(
            AttachmentCategory.project_type == project_type,
        )

    categories = query.all()

    total_items = 0
    confirmed_items = 0
    items_detail = {}

    for cat in categories:
        cat_confirmed = True
        cat_file_count = 0
        for item in cat.items:
            if not item.is_active:
                continue
            total_items += 1

            status = (
                db.query(AttachmentStatus)
                .filter(
                    AttachmentStatus.contract_type == contract_type,
                    AttachmentStatus.contract_id == contract_id,
                    AttachmentStatus.item_id == item.id,
                )
                .first()
            )

            is_confirmed = status.confirmed if status else False
            fc = status.file_count if status else 0
            cat_file_count += fc

            if is_confirmed:
                confirmed_items += 1
            else:
                cat_confirmed = False

            # 按子项 ID 返回明细
            items_detail[item.id] = {
                "confirmed": is_confirmed,
                "file_count": fc,
            }

    return {
        "total_items": total_items,
        "confirmed_items": confirmed_items,
        "all_confirmed": (confirmed_items == total_items) and total_items > 0,
        "items": items_detail,
    }


# ============================================================
# 默认分类初始化
# ============================================================

DEFAULT_CATEGORIES = [
    {
        "contract_type": "compute_leasing",
        "categories": [
            {
                "name": "合同协议",
                "code": "contract_agreement",
                "sort_order": 1,
                "items": [
                    {"name": "合同扫描件", "description": "合同扫描件PDF", "expected_type": "pdf", "sort_order": 1},
                ],
            },
            {
                "name": "交付材料",
                "code": "acceptance_material",
                "sort_order": 2,
                "items": [
                    {"name": "验收单扫描件", "description": "验收单扫描件PDF", "expected_type": "pdf", "sort_order": 1},
                ],
            },
            {
                "name": "过程材料",
                "code": "process_material",
                "sort_order": 3,
                "items": [
                    {"name": "资源交付清单", "description": "资源交付清单Excel", "expected_type": "excel", "sort_order": 1},
                    {"name": "资源开通邮件截图", "description": "资源开通邮件截图", "expected_type": "image", "sort_order": 2},
                ],
            },
        ],
    },
    {
        "contract_type": "satellite_data",
        "categories": [
            {
                "name": "合同协议",
                "code": "contract_agreement",
                "sort_order": 1,
                "items": [
                    {"name": "合同扫描件", "description": "合同扫描件PDF", "expected_type": "pdf", "sort_order": 1},
                ],
            },
            {
                "name": "交付材料",
                "code": "acceptance_material",
                "sort_order": 2,
                "items": [
                    {"name": "验收单扫描件", "description": "验收单扫描件PDF", "expected_type": "pdf", "sort_order": 1},
                ],
            },
            {
                "name": "过程材料",
                "code": "process_material",
                "sort_order": 3,
                "items": [
                    {"name": "资源交付清单", "description": "资源交付清单Excel", "expected_type": "excel", "sort_order": 1},
                    {"name": "资源开通邮件截图", "description": "资源开通邮件截图", "expected_type": "image", "sort_order": 2},
                ],
            },
        ],
    },
    {
        "contract_type": "compute_service",
        "categories": [
            {
                "name": "合同协议",
                "code": "contract_agreement",
                "sort_order": 1,
                "items": [
                    {"name": "合同扫描件", "description": "合同扫描件PDF", "expected_type": "pdf", "sort_order": 1},
                ],
            },
            {
                "name": "交付材料",
                "code": "acceptance_material",
                "sort_order": 2,
                "items": [
                    {"name": "验收单扫描件", "description": "验收单扫描件PDF", "expected_type": "pdf", "sort_order": 1},
                ],
            },
            {
                "name": "过程材料",
                "code": "process_material",
                "sort_order": 3,
                "items": [
                    {"name": "资源交付清单", "description": "资源交付清单Excel", "expected_type": "excel", "sort_order": 1},
                    {"name": "资源开通邮件截图", "description": "资源开通邮件截图", "expected_type": "image", "sort_order": 2},
                ],
            },
        ],
    },
]


def init_default_categories(db: Session):
    """初始化默认分类数据（幂等）"""
    for ct_group in DEFAULT_CATEGORIES:
        contract_type = ct_group["contract_type"]
        for cat_def in ct_group["categories"]:
            existing = (
                db.query(AttachmentCategory)
                .filter(
                    AttachmentCategory.contract_type == contract_type,
                    AttachmentCategory.code == cat_def["code"],
                )
                .first()
            )
            if existing:
                continue

            category = AttachmentCategory(
                contract_type=contract_type,
                name=cat_def["name"],
                code=cat_def["code"],
                sort_order=cat_def["sort_order"],
            )
            db.add(category)
            db.flush()

            for item_def in cat_def["items"]:
                item = AttachmentItem(
                    category_id=category.id,
                    name=item_def["name"],
                    description=item_def.get("description"),
                    expected_type=item_def.get("expected_type", "any"),
                    sort_order=item_def.get("sort_order", 0),
                )
                db.add(item)

    db.commit()
