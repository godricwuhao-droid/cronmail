"""
核心配置模块
使用 pydantic-settings 从环境变量加载配置
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 数据库（资产运营管理平台独立库 asset_ops，见 ADR-019；
    # 生产环境通过环境变量/K8s ConfigMap 注入，K8s 侧注入留到部署阶段）
    DATABASE_URL: str = "mysql+pymysql://root:root@127.0.0.1:3306/asset_ops"

    # 加密密钥（Fernet key）
    MAIL_ENCRYPTION_KEY: str = ""

    # 应用
    APP_TITLE: str = "CronMail API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # LLM（合同解析）
    LLM_BASE_URL: str = "http://192.168.180.67:8080/v1"
    LLM_API_KEY: str = "not-needed"
    LLM_MODEL: str = "Qwen3.6-27B"

    # LLM 阶段2 提取专用模型（与 OCR 分离，独立 OpenAI 协议服务）
    LLM_BASE_URL_EXTRACT: str = "http://api.opearlai.com:30096/v1"
    LLM_API_KEY_EXTRACT: str = "sk-tArrgRR2_tqUGYoU_Glakw"
    LLM_MODEL_EXTRACT: str = "DeepSeek-V4-Flash"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Celery
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"

    # SMTP 兜底配置
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SENDER_NAME: str = "CronMail"
    SMTP_SENDER_EMAIL: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
