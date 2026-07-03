"""
时区辅助模块
提供 UTC+8 本地时间函数

支持通过环境变量 CRONMAIL_SIM_DATE 模拟日期（用于调试触发端点）：
  export CRONMAIL_SIM_DATE=2026-06-30
"""
import os
from datetime import date, datetime, timedelta


def local_now():
    """返回当前 UTC+8 (北京时间) 的 datetime"""
    sim = os.environ.get('CRONMAIL_SIM_DATE')
    if sim:
        return datetime.fromisoformat(sim + "T12:00:00")
    return datetime.utcnow() + timedelta(hours=8)


def local_today():
    """返回当前 UTC+8 (北京时间) 的 date，可通过 CRONMAIL_SIM_DATE 覆盖"""
    sim = os.environ.get('CRONMAIL_SIM_DATE')
    if sim:
        return date.fromisoformat(sim)
    return (datetime.utcnow() + timedelta(hours=8)).date()
