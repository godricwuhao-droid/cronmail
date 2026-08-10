"""
附件管理模块 API 路由
"""
import io
import os
import re
import zipfile
import urllib.parse
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
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
    contract_type: str = Query(..., description="合同类型: compute_leasing/satellite_data/compute_service/project"),
    contract_id: str = Query(..., description="合同ID"),
    project_type: Optional[str] = Query(None, description="项目类型（仅 contract_type=project 时使用）"),
    db: Session = Depends(get_db),
):
    """按合同获取附件列表（分类+子项结构）"""
    categories = services.get_attachment_list(db, contract_type, contract_id, project_type=project_type)
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


# /export 必须在 /{attachment_id}/download 之前注册，否则 export 会被当作 attachment_id
@attachment_router.get("/export")
def export_attachments_zip(
    contract_type: str = Query(..., description="合同类型: compute_leasing/satellite_data/compute_service"),
    contract_id: str = Query(..., description="合同ID"),
    db: Session = Depends(get_db),
):
    """一键导出合同所有附件为 ZIP 包

    目录结构（动态生成）：
    {合同名称}/
    ├── {category.name}/      ← 运行时动态，可能被管理员改名或新增
    │   ├── {item.name}/
    │   │   ├── file1.pdf
    │   │   └── file2.docx
    │   └── ...
    └── ...
    """
    # 1. 获取合同名称
    contract_name = _get_contract_name(db, contract_type, contract_id)
    if not contract_name:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 2. 获取该合同类型下的活跃分类（动态，不硬编码）
    categories = (
        db.query(AttachmentCategory)
        .filter(
            AttachmentCategory.contract_type == contract_type,
            AttachmentCategory.is_active == True,  # noqa: E712
        )
        .order_by(AttachmentCategory.sort_order)
        .all()
    )

    if not categories:
        raise HTTPException(status_code=404, detail="该合同类型下无附件分类，请先在系统配置中配置")

    # 3. 组装 ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        has_any_file = False
        for cat in categories:
            for item in cat.items:
                if not item.is_active:
                    continue
                # 获取该 item 下该合同的附件
                files = (
                    db.query(Attachment)
                    .filter(
                        Attachment.contract_type == contract_type,
                        Attachment.contract_id == contract_id,
                        Attachment.item_id == item.id,
                    )
                    .order_by(Attachment.uploaded_at)
                    .all()
                )
                if not files:
                    continue  # 无文件的子项跳过

                has_any_file = True
                # 目录路径: 合同名称/category名称/item名称/
                dir_prefix = f"{_safe_zip_name(contract_name)}/{_safe_zip_name(cat.name)}/{_safe_zip_name(item.name)}"

                # 处理重名文件
                used_names: dict[str, int] = {}
                for att in files:
                    full_path = os.path.join(UPLOAD_BASE_DIR, att.file_path)
                    if not os.path.exists(full_path):
                        continue

                    original_name = att.filename or "unnamed"
                    zip_name = _resolve_duplicate_name(original_name, used_names)

                    arcname = f"{dir_prefix}/{zip_name}"
                    zf.write(full_path, arcname)

        if not has_any_file:
            raise HTTPException(status_code=404, detail="该合同下无附件文件")

    zip_buffer.seek(0)

    today_str = date.today().strftime("%Y-%m-%d")
    safe_name = _safe_zip_name(contract_name)
    filename = f"{safe_name}_附件_{today_str}.zip"
    encoded = urllib.parse.quote(filename)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )


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
    project_type: Optional[str] = Query(None, description="项目类型（仅 contract_type=project 时使用）"),
    db: Session = Depends(get_db),
):
    """获取合同附件完成状态汇总"""
    summary = services.get_summary(db, contract_type, contract_id, project_type=project_type)
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
    project_type: Optional[str] = Query(None, description="项目类型筛选（仅 contract_type=project 时使用）"),
    db: Session = Depends(get_db),
):
    """获取附件分类列表（含子项）"""
    categories = services.list_categories(db, contract_type=contract_type, project_type=project_type)
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


# ============================================================
# 辅助函数（供 export_attachments_zip 使用）
# ============================================================

def _get_contract_name(db: Session, contract_type: str, contract_id: str) -> Optional[str]:
    """根据合同类型查询合同名称"""
    if contract_type == "compute_leasing":
        from src.contract.models import Contract
        c = db.query(Contract).filter(Contract.id == contract_id).first()
        return c.name if c else None
    elif contract_type == "satellite_data":
        from src.satellite.models import SatelliteDataContract
        c = db.query(SatelliteDataContract).filter(SatelliteDataContract.id == contract_id).first()
        return c.name if c else None
    elif contract_type == "compute_service":
        from src.compute_service.models import ComputeServiceContract
        c = db.query(ComputeServiceContract).filter(ComputeServiceContract.id == contract_id).first()
        return c.name if c else None
    elif contract_type == "project":
        from src.project.models import ProjectContract
        c = db.query(ProjectContract).filter(ProjectContract.id == contract_id).first()
        return c.name if c else None
    return None


def _safe_zip_name(name: str) -> str:
    """清理文件名中的非法字符（用于 ZIP 内路径）"""
    # 替换路径分隔符和非法字符
    safe = re.sub(r'[\\/:*?"<>|]', '_', name)
    return safe.strip() or "unnamed"


def _resolve_duplicate_name(filename: str, used: dict[str, int]) -> str:
    """处理重名：file.pdf → file(2).pdf"""
    if filename not in used:
        used[filename] = 1
        return filename
    used[filename] += 1
    name, ext = os.path.splitext(filename)
    return f"{name}({used[filename]}){ext}"
