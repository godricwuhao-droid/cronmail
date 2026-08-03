"""
核心配置模块
使用 pydantic-settings 从环境变量加载配置
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 数据库
    DATABASE_URL: str = "mysql+pymysql://root:root@127.0.0.1:3306/cronmail"

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
