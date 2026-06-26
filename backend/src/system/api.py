"""
系统配置模块 API 路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.system import schemas, services
from src.system.models import SystemConfig

# ============================================================
# System Router
# ============================================================

system_router = APIRouter(prefix="/api/system", tags=["System"])


@system_router.get("/smtp", response_model=schemas.SmtpConfigResponse)
def get_smtp_config(
    db: Session = Depends(get_db),
):
    """获取 SMTP 配置（不返回密码）"""
    config = services.get_smtp_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="SMTP 配置不存在，请先通过 PUT 接口创建")
    return schemas.SmtpConfigResponse.model_validate(config)


@system_router.put("/smtp", response_model=schemas.SmtpConfigResponse)
def update_smtp_config(
    data: schemas.SmtpConfigUpdate,
    db: Session = Depends(get_db),
):
    """更新 SMTP 配置（首次不存在则创建，已存在则更新）"""
    config = services.upsert_smtp_config(db, data)
    return schemas.SmtpConfigResponse.model_validate(config)


@system_router.post("/smtp/test", response_model=schemas.SmtpTestResponse)
def test_smtp_config(
    data: schemas.SmtpTestRequest,
    db: Session = Depends(get_db),
):
    """测试 SMTP 连接"""
    config = services.get_smtp_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="SMTP 配置不存在，请先通过 PUT /api/system/smtp 创建配置")
    success, message = services.test_smtp_connection(config, data.test_email)
    return schemas.SmtpTestResponse(success=success, message=message)


# ============================================================
# 钉钉机器人配置
# ============================================================

def _dingtalk_config_to_response(config) -> schemas.DingTalkConfigResponse:
    """将 DingTalkConfig ORM 对象转为响应（secret 脱敏）"""
    secret_display = "***" if config.secret else ""
    return schemas.DingTalkConfigResponse(
        id=config.id,
        webhook_url=config.webhook_url,
        secret=secret_display,
        is_active=config.is_active,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@system_router.get("/dingtalk", response_model=schemas.DingTalkConfigResponse)
def get_dingtalk_config(
    db: Session = Depends(get_db),
):
    """获取钉钉配置（secret 脱敏）"""
    config = services.get_dingtalk_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="钉钉配置不存在，请先通过 PUT 接口创建")
    return _dingtalk_config_to_response(config)


@system_router.put("/dingtalk", response_model=schemas.DingTalkConfigResponse)
def update_dingtalk_config(
    data: schemas.DingTalkConfigUpdate,
    db: Session = Depends(get_db),
):
    """更新钉钉配置（首次不存在则创建，已存在则更新）"""
    update_data = data.model_dump(exclude_unset=True)
    config = services.upsert_dingtalk_config(db, update_data)
    return _dingtalk_config_to_response(config)


@system_router.post("/dingtalk/test", response_model=schemas.DingTalkTestResponse)
def test_dingtalk_config(
    data: schemas.DingTalkTestRequest,
    db: Session = Depends(get_db),
):
    """测试钉钉连接（发送测试 Markdown 消息）"""
    config = services.get_dingtalk_config(db)
    test_data = data.model_dump(exclude_unset=True)

    # 如果请求中没有提供 webhook_url/secret，使用已保存的配置
    if not test_data.get("webhook_url") and config:
        pass  # test_dingtalk 会从 config 获取

    if not test_data.get("webhook_url") and not config:
        raise HTTPException(status_code=404, detail="钉钉配置不存在，请先通过 PUT /api/system/dingtalk 创建配置或传入测试参数")

    success, message = services.test_dingtalk(config=config, test_data=test_data)
    return schemas.DingTalkTestResponse(success=success, message=message)


# ============================================================
# SystemConfig CRUD
# ============================================================

@system_router.get("/config")
def get_configs(db: Session = Depends(get_db)):
    """获取所有系统配置"""
    configs = db.query(SystemConfig).all()
    return [{"key": c.key, "value": c.value, "description": c.description} for c in configs]


@system_router.get("/config/{key}")
def get_config(key: str, db: Session = Depends(get_db)):
    """获取单个系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"配置 '{key}' 不存在")
    return {"key": config.key, "value": config.value, "description": config.description}


@system_router.put("/config/{key}")
def update_config(key: str, data: dict, db: Session = Depends(get_db)):
    """更新或创建系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        config = SystemConfig(key=key, value=data.get("value", ""), description=data.get("description"))
        db.add(config)
    else:
        config.value = data.get("value", config.value)
        if "description" in data:
            config.description = data["description"]
    db.commit()
    db.refresh(config)
    return {"key": config.key, "value": config.value, "description": config.description}
