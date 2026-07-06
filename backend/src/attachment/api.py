"""
附件管理模块 API 路由
"""
import os
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.attachment import schemas, services
from src.attachment.models import Attachment, AttachmentCategory, AttachmentItem
from src.attachment.services import UPLOAD_BASE_DIR

attachment_router = APIRouter(prefix="/api/attachments", tags=["Attachment"])


# ============================================================
# 附件文件 CRUD
# ============================================================

@attachment_router.get("", response_model=schemas.AttachmentListByContractResponse)
def list_attachments(
    contract_type: str = Query(..., description="合同类型: compute_leasing/satellite_data/compute_service"),
    contract_id: str = Query(..., description="合同ID"),
    db: Session = Depends(get_db),
):
    """按合同获取附件列表（分类+子项结构）"""
    categories = services.get_attachment_list(db, contract_type, contract_id)
    return schemas.AttachmentListByContractResponse(categories=categories)


@attachment_router.post("/upload", response_model=schemas.AttachmentUploadResponse)
def upload_attachments(
    contract_type: str = Query(..., description="合同类型"),
    contract_id: str = Query(..., description="合同ID"),
    item_id: str = Query(..., description="附件子项ID"),
    files: list[UploadFile] = File(..., description="上传文件列表"),
    db: Session = Depends(get_db),
):
    """多文件上传"""
    if not files:
        raise HTTPException(status_code=400, detail="请至少选择一个文件")

    result = []
    for f in files:
        if not f.filename:
            continue
        attachment = services.save_file(db, f, contract_type, contract_id, item_id)
        result.append(schemas.AttachmentFileBrief(
            id=attachment.id,
            filename=attachment.filename,
            file_size=attachment.file_size,
            mime_type=attachment.mime_type,
            uploaded_at=attachment.uploaded_at,
        ))

    return schemas.AttachmentUploadResponse(attachments=result)


@attachment_router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
):
    """文件下载"""
    attachment = services.get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_full_path = os.path.join(UPLOAD_BASE_DIR, attachment.file_path)
    if not os.path.exists(file_full_path):
        raise HTTPException(status_code=404, detail="文件已被删除")

    # RFC 5987 编码中文文件名，兼容旧浏览器
    encoded_filename = urllib.parse.quote(attachment.filename, safe='')
    fallback_name = attachment.filename.encode('ascii', 'ignore').decode('ascii') or 'download'

    return FileResponse(
        path=file_full_path,
        filename=attachment.filename,
        media_type=attachment.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{fallback_name}\"; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


@attachment_router.delete("/{attachment_id}", response_model=dict)
def delete_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
):
    """删除文件"""
    attachment = services.get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="文件不存在")

    services.delete_file(db, attachment)
    return {"detail": "文件已删除"}


# ============================================================
# 附件完成确认
# ============================================================

@attachment_router.get("/status/summary", response_model=schemas.AttachmentSummaryResponse)
def get_status_summary(
    contract_type: str = Query(..., description="合同类型"),
    contract_id: str = Query(..., description="合同ID"),
    db: Session = Depends(get_db),
):
    """获取合同附件完成状态汇总"""
    summary = services.get_summary(db, contract_type, contract_id)
    return schemas.AttachmentSummaryResponse(**summary)


@attachment_router.post("/status/{item_id}/confirm", response_model=schemas.AttachmentStatusResponse)
def confirm_item(
    item_id: str,
    data: schemas.AttachmentStatusConfirmRequest,
    db: Session = Depends(get_db),
):
    """确认子项完成"""
    # 验证子项存在
    item = services.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件子项不存在")

    status = services.confirm_item(db, data.contract_type, data.contract_id, item_id)
    return schemas.AttachmentStatusResponse(confirmed=status.confirmed)


@attachment_router.post("/status/{item_id}/unconfirm", response_model=schemas.AttachmentStatusResponse)
def unconfirm_item(
    item_id: str,
    data: schemas.AttachmentStatusConfirmRequest,
    db: Session = Depends(get_db),
):
    """取消确认"""
    item = services.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件子项不存在")

    status = services.unconfirm_item(db, data.contract_type, data.contract_id, item_id)
    return schemas.AttachmentStatusResponse(confirmed=status.confirmed)


# ============================================================
# 附件分类管理路由（放在 attachment_router 内部，但属于 /api/system 前缀）
# 实际注册时通过 system 模块挂载
# ============================================================

system_attachment_category_router = APIRouter(
    prefix="/api/system/attachment-categories",
    tags=["System - Attachment Categories"],
)


@system_attachment_category_router.get("", response_model=schemas.AttachmentCategoryListWrap)
def list_categories(
    contract_type: Optional[str] = Query(None, description="合同类型筛选"),
    db: Session = Depends(get_db),
):
    """获取附件分类列表（含子项）"""
    categories = services.list_categories(db, contract_type=contract_type)
    return schemas.AttachmentCategoryListWrap(items=categories)


@system_attachment_category_router.post("", response_model=schemas.AttachmentCategoryResponse, status_code=201)
def create_category(
    data: schemas.AttachmentCategoryCreate,
    db: Session = Depends(get_db),
):
    """创建附件分类"""
    category = services.create_category(db, data)
    return category


@system_attachment_category_router.put("/{category_id}", response_model=schemas.AttachmentCategoryResponse)
def update_category(
    category_id: str,
    data: schemas.AttachmentCategoryUpdate,
    db: Session = Depends(get_db),
):
    """更新附件分类"""
    category = services.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return services.update_category(db, category, data)


@system_attachment_category_router.delete("/{category_id}", response_model=dict)
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
):
    """软删除附件分类"""
    category = services.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    services.soft_delete_category(db, category)
    return {"detail": "分类已删除"}


@system_attachment_category_router.put("/{category_id}/reorder", response_model=dict)
def reorder_category(
    category_id: str,
    data: schemas.AttachmentCategoryReorder,
    db: Session = Depends(get_db),
):
    """调整分类排序"""
    category = services.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    services.reorder_category(db, category, data.sort_order)
    return {"detail": "排序已更新"}


# ============================================================
# 附件子项管理
# ============================================================

@system_attachment_category_router.post("/{category_id}/items", response_model=schemas.AttachmentItemResponse, status_code=201)
def create_item(
    category_id: str,
    data: schemas.AttachmentItemCreate,
    db: Session = Depends(get_db),
):
    """在分类下添加子项"""
    item = services.create_item(db, category_id, data)
    return item


@system_attachment_category_router.put("/items/{item_id}", response_model=schemas.AttachmentItemResponse)
def update_item(
    item_id: str,
    data: schemas.AttachmentItemUpdate,
    db: Session = Depends(get_db),
):
    """更新附件子项"""
    item = services.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件子项不存在")
    return services.update_item(db, item, data)


@system_attachment_category_router.delete("/items/{item_id}", response_model=dict)
def delete_item(
    item_id: str,
    db: Session = Depends(get_db),
):
    """软删除附件子项"""
    item = services.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件子项不存在")
    services.soft_delete_item(db, item)
    return {"detail": "子项已删除"}


@system_attachment_category_router.put("/items/{item_id}/reorder", response_model=dict)
def reorder_item(
    item_id: str,
    data: schemas.AttachmentItemReorder,
    db: Session = Depends(get_db),
):
    """调整子项排序"""
    item = services.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件子项不存在")
    services.reorder_item(db, item, data.sort_order)
    return {"detail": "排序已更新"}
