"""
系统配置模块 API 路由
"""
import os
from datetime import date, datetime
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


@system_router.get("/config/schedules", response_model=dict)
def get_schedules(db: Session = Depends(get_db)):
    """获取所有通知调度时间配置"""
    defaults = {
        'check-expiring-rentals': '08:00',
        'check-expired-rentals': '00:00',
        'check-reclaim-expired': '01:00',
    }
    result = {}
    for key in defaults:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        result[key] = config.value if config else defaults[key]
    return result


@system_router.put("/config/schedules", response_model=dict)
def update_schedules(data: dict, db: Session = Depends(get_db)):
    """
    批量更新通知调度时间，并触发 Beat 重启使配置生效
    请求体: {"check-expiring-rentals": "08:00", "check-expired-rentals": "00:00", "check-reclaim-expired": "01:00"}
    """
    ALLOWED_KEYS = {'check-expiring-rentals', 'check-expired-rentals', 'check-reclaim-expired'}
    import re
    time_ptn = re.compile(r'^\d{1,2}:\d{2}$')

    for key in ALLOWED_KEYS:
        if key not in data:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {key}")
        val = str(data[key]).strip()
        if not time_ptn.match(val):
            raise HTTPException(status_code=400, detail=f"{key} 格式错误: 需要 HH:MM 格式, 实际 {val}")
        h, m = val.split(':')
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise HTTPException(status_code=400, detail=f"{key} 时间超出范围: {val}")

    for key in ALLOWED_KEYS:
        services.upsert_system_config(db, key, str(data[key]).strip(), f"通知调度时间 - {key}")

    # 触发 Beat 重启
    restart_msg = ""
    try:
        restart_msg = services.restart_beat()
    except Exception as e:
        restart_msg = f"(Beat 重启失败: {e}，请手动执行 kubectl rollout restart deployment/cronmail-backend-beat -n cronmail)"

    return {"detail": "通知时间配置已保存", "restart": restart_msg}


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


# ============================================================
# 调试触发端点
# ============================================================

@system_router.post("/trigger/{task_name}")
def debug_trigger(task_name: str, body: dict = {}, db: Session = Depends(get_db)):
    """调试：手动触发定时任务，支持 simulate_date 模拟日期"""
    ALLOWED = {'check_expiring_rentals', 'check_expired_rentals', 'check_reclaim_expired'}
    if task_name not in ALLOWED:
        raise HTTPException(400, f"无效任务名，可选: {', '.join(ALLOWED)}")

    sim_date = body.get('simulate_date') if body else None
    if sim_date:
        os.environ['CRONMAIL_SIM_DATE'] = sim_date

    try:
        if task_name == 'check_expiring_rentals':
            from src.scheduler.tasks import check_expiring_rentals
            result = check_expiring_rentals()
        elif task_name == 'check_expired_rentals':
            from src.scheduler.tasks import check_expired_rentals
            result = check_expired_rentals()
        else:
            from src.scheduler.tasks import check_reclaim_expired
            result = check_reclaim_expired()
        return {"task": task_name, "simulated_date": sim_date, "result": str(result)}
    finally:
        if sim_date:
            os.environ.pop('CRONMAIL_SIM_DATE', None)
