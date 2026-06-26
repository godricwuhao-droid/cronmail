"""
邮件模板渲染器
使用 Jinja2 SandboxedEnvironment 安全渲染模板
"""
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import UndefinedError


# 模块级沙箱环境实例
_env = SandboxedEnvironment()


class RenderError(Exception):
    """模板渲染错误"""
    pass


def render_template(template_str: str, context: dict, signature_html: str = None) -> str:
    """
    渲染 Jinja2 模板字符串

    Args:
        template_str: Jinja2 模板字符串（如 "{{ machine_model }} 已开通"）
        context: 模板变量上下文
        signature_html: 邮件签名（HTML），渲染完 body 后拼接在末尾

    Returns:
        渲染后的字符串

    Raises:
        RenderError: 渲染失败（变量缺失等）
    """
    if not template_str:
        return ""

    try:
        template = _env.from_string(template_str)
        rendered = template.render(**context)
        if signature_html:
            rendered += f"\n<!-- signature -->\n{signature_html}"
        return rendered
    except UndefinedError as e:
        raise RenderError(f"模板变量缺失: {e}")
    except Exception as e:
        raise RenderError(f"模板渲染失败: {e}")
