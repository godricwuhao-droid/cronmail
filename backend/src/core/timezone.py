"""
时区辅助模块
提供 UTC+8 本地时间函数
"""
from datetime import datetime, timedelta


def local_now():
    """返回当前 UTC+8 (北京时间) 的 datetime"""
    return datetime.utcnow() + timedelta(hours=8)
