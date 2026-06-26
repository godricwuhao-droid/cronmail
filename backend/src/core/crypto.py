"""
密码加密/解密工具
使用 cryptography.fernet 进行对称加密
"""
from cryptography.fernet import Fernet

from src.core.config import settings

# 模块级缓存：确保同一进程中加密解密使用同一密钥
_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """获取 Fernet 实例（进程内单例）"""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    key = settings.MAIL_ENCRYPTION_KEY
    if not key:
        # 开发环境自动生成临时密钥（注意：重启后密钥变化，已加密数据将无法解密）
        key = Fernet.generate_key()
    # 确保 key 是 bytes
    if isinstance(key, str):
        key = key.encode("utf-8")
    _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt_password(plaintext: str) -> str:
    """
    加密密码/敏感信息
    Args:
        plaintext: 明文
    Returns:
        Base64 编码的密文（字符串形式，可直接存入数据库 TEXT 字段）
    """
    if not plaintext:
        return ""
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(ciphertext: str) -> str:
    """
    解密密文
    Args:
        ciphertext: 加密后的密文字符串
    Returns:
        明文
    """
    if not ciphertext:
        return ""
    f = _get_fernet()
    plain = f.decrypt(ciphertext.encode("utf-8"))
    return plain.decode("utf-8")
