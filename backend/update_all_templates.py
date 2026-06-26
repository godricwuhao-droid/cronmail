"""
更新三套邮件通知模板的 HTML 内容（一次性脚本）

将 provision / expiry_warning / reclaim 三套模板的 body_html
更新为新的 7 列统一布局：
  服务器类型 | IP 地址 | 操作系统 | 系统盘 | 数据盘 | 带宽 | 到期时间

用法：在 backend 目录下运行
    python3 update_all_templates.py
"""
import sys
sys.path.insert(0, '.')

# 导入所有模型确保 SQLAlchemy registry 注册完整
from src.contract.models import Contract
from src.rental.models import RentalRecord
from src.customer.models import Customer, Contact
from src.mail.models import EmailLog
from src.system.models import SystemConfig
from src.template.models import EmailTemplate
from src.core.database import SessionLocal

# ──────────────────────────────────────────────
# 1. 开通邮件模板 (provision) — 绿色主题 #2e7d32
# ──────────────────────────────────────────────
PROVISION_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;padding:0;font-family:'Microsoft YaHei','微软雅黑','Segoe UI',Arial,sans-serif;background:#f5f7fa;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fa;padding:20px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

<!-- Header -->
<tr><td style="background:#2e7d32;padding:24px 32px;">
<table width="100%"><tr>
<td style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:1px;">裸金属服务器资源开通通知</td>
</tr></table>
</td></tr>

<!-- Body -->
<tr><td style="padding:24px 32px;">

<p style="color:#333;font-size:14px;line-height:1.6;margin:0 0 6px 0;"><b>{{ customer_name }}</b> 您好，</p>
<p style="color:#555;font-size:14px;line-height:1.6;margin:0 0 20px 0;">以下裸金属服务器已开通并交付使用，请妥善保管登录信息。</p>

<!-- Resource Info Table (7 columns) -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;border:1px solid #e0e4e8;border-radius:6px;">
<tr><td colspan="7" style="background:#e8f5e9;padding:10px 16px;font-size:14px;font-weight:bold;color:#2e7d32;border-bottom:1px solid #e0e4e8;">资源信息（共 {{ rental_count }} 台）</td></tr>
<tr style="background:#f5f7fa;">
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">服务器类型</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">IP 地址</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">操作系统</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">系统盘</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">数据盘</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">带宽</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">到期时间</td>
</tr>
{% for r in rentals %}
<tr>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;"><b>{{ r.machine_model }}</b>{{ "（" + r.cpu_model + "）" if r.cpu_model else "" }}</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">
内网: {{ r.private_ip }}{% for ip in r.public_ips %}<br>公网: {{ ip }}{% endfor %}
</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.os_version }}</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.system_disk_gb }}GB</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">
{% for disk in r.data_disks %}{{ disk.size_gb }}GB {{ disk.type }}{% if not loop.last %}, {% endif %}{% endfor %}{% if not r.data_disks %}-{% endif %}
</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.bandwidth_mbps }}Mbps</td>
<td style="padding:10px 12px;font-size:12px;color:#2e7d32;border-bottom:1px solid #f0f0f0;"><b>{{ r.end_date }}</b></td>
</tr>
{% endfor %}
</table>

<!-- Login Info Box -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;border:1px solid #c8e6c9;border-radius:6px;background:#e8f5e9;">
<tr><td colspan="3" style="background:#c8e6c9;padding:10px 16px;font-size:14px;font-weight:bold;color:#2e7d32;border-bottom:1px solid #c8e6c9;">登录信息</td></tr>
<tr style="background:#e8f5e9;">
<td style="padding:10px 16px;font-size:12px;color:#666;border-bottom:1px solid #c8e6c9;font-weight:bold;">IP</td>
<td style="padding:10px 16px;font-size:12px;color:#666;border-bottom:1px solid #c8e6c9;font-weight:bold;">账号</td>
<td style="padding:10px 16px;font-size:12px;color:#666;border-bottom:1px solid #c8e6c9;font-weight:bold;">密码</td>
</tr>
{% for r in rentals %}
<tr>
<td style="padding:10px 16px;font-size:12px;color:#333;border-bottom:1px solid #e0e4e8;">{{ r.private_ip }}:{{ r.ssh_port }}</td>
<td style="padding:10px 16px;font-size:12px;color:#333;border-bottom:1px solid #e0e4e8;">{{ r.root_username }}</td>
<td style="padding:10px 16px;font-size:12px;color:#333;border-bottom:1px solid #e0e4e8;">{{ r.root_password }}</td>
</tr>
{% endfor %}
</table>

<!-- Footer Tip -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#e3f2fd;border:1px solid #bbdefb;border-radius:6px;margin-bottom:20px;">
<tr><td style="padding:12px 16px;font-size:13px;color:#1565c0;line-height:1.6;">
请妥善保管登录凭证，建议首次登录后修改密码。
</td></tr>
</table>

</td></tr>
</table>
</td></tr></table>
</body>
</html>"""

# ──────────────────────────────────────────────
# 2. 临期邮件模板 (expiry_warning) — 橙色主题 #ef6c00
# ──────────────────────────────────────────────
EXPIRY_WARNING_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;padding:0;font-family:'Microsoft YaHei','微软雅黑','Segoe UI',Arial,sans-serif;background:#f5f7fa;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fa;padding:20px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

<!-- Header -->
<tr><td style="background:#ef6c00;padding:24px 32px;">
<table width="100%"><tr>
<td style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:1px;">裸金属服务器资源临期提醒</td>
</tr></table>
</td></tr>

<!-- Body -->
<tr><td style="padding:24px 32px;">

<p style="color:#333;font-size:14px;line-height:1.6;margin:0 0 6px 0;"><b>{{ customer_name }}</b> 您好，</p>
<p style="color:#555;font-size:14px;line-height:1.6;margin:0 0 20px 0;">以下裸金属服务器资源即将到期（剩余 {{ rentals[0].days_until_expiry }} 天），请及时续费以避免服务中断。</p>

<!-- Resource Info Table (7 columns) -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;border:1px solid #e0e4e8;border-radius:6px;">
<tr><td colspan="7" style="background:#fff3e0;padding:10px 16px;font-size:14px;font-weight:bold;color:#ef6c00;border-bottom:1px solid #e0e4e8;">待续费资源（共 {{ rental_count }} 台）</td></tr>
<tr style="background:#f5f7fa;">
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">服务器类型</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">IP 地址</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">操作系统</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">系统盘</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">数据盘</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">带宽</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">到期时间</td>
</tr>
{% for r in rentals %}
<tr>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;"><b>{{ r.machine_model }}</b>{{ "（" + r.cpu_model + "）" if r.cpu_model else "" }}</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">
内网: {{ r.private_ip }}{% for ip in r.public_ips %}<br>公网: {{ ip }}{% endfor %}
</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.os_version }}</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.system_disk_gb }}GB</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">
{% for disk in r.data_disks %}{{ disk.size_gb }}GB {{ disk.type }}{% if not loop.last %}, {% endif %}{% endfor %}{% if not r.data_disks %}-{% endif %}
</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.bandwidth_mbps }}Mbps</td>
<td style="padding:10px 12px;font-size:12px;color:#e53935;border-bottom:1px solid #f0f0f0;"><b>{{ r.end_date }}</b></td>
</tr>
{% endfor %}
</table>

<!-- Footer Tip -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#fff3e0;border:1px solid #ffcc80;border-radius:6px;margin-bottom:20px;">
<tr><td style="padding:12px 16px;font-size:13px;color:#e65100;line-height:1.6;">
<b>⚠ 温馨提示：</b><br>
如需续租，请于到期前联系运维团队办理续租手续。到期后资源将被回收，数据无法恢复。
</td></tr>
</table>

</td></tr>
</table>
</td></tr></table>
</body>
</html>"""

# ──────────────────────────────────────────────
# 3. 回收邮件模板 (reclaim) — 红色主题 #e53935
# ──────────────────────────────────────────────
RECLAIM_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;padding:0;font-family:'Microsoft YaHei','微软雅黑','Segoe UI',Arial,sans-serif;background:#f5f7fa;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fa;padding:20px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

<!-- Header -->
<tr><td style="background:#e53935;padding:24px 32px;">
<table width="100%"><tr>
<td style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:1px;">裸金属服务器资源回收通知</td>
</tr></table>
</td></tr>

<!-- Body -->
<tr><td style="padding:24px 32px;">

<p style="color:#333;font-size:14px;line-height:1.6;margin:0 0 6px 0;"><b>{{ customer_name }}</b> 您好，</p>
<p style="color:#555;font-size:14px;line-height:1.6;margin:0 0 20px 0;">根据资源管理规定，以下裸金属服务器资源即将执行回收，请提前做好数据备份与迁移工作。</p>

<!-- Resource Info Table (7 columns) -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;border:1px solid #e0e4e8;border-radius:6px;">
<tr><td colspan="7" style="background:#fce4ec;padding:10px 16px;font-size:14px;font-weight:bold;color:#c62828;border-bottom:1px solid #e0e4e8;">待回收资源（共 {{ rental_count }} 台）</td></tr>
<tr style="background:#f5f7fa;">
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">服务器类型</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">IP 地址</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">操作系统</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">系统盘</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">数据盘</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">带宽</td>
<td style="padding:10px 12px;font-size:12px;color:#666;border-bottom:1px solid #e0e4e8;font-weight:bold;">到期时间</td>
</tr>
{% for r in rentals %}
<tr>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;"><b>{{ r.machine_model }}</b>{{ "（" + r.cpu_model + "）" if r.cpu_model else "" }}</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">
内网: {{ r.private_ip }}{% for ip in r.public_ips %}<br>公网: {{ ip }}{% endfor %}
</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.os_version }}</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.system_disk_gb }}GB</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">
{% for disk in r.data_disks %}{{ disk.size_gb }}GB {{ disk.type }}{% if not loop.last %}, {% endif %}{% endfor %}{% if not r.data_disks %}-{% endif %}
</td>
<td style="padding:10px 12px;font-size:12px;color:#333;border-bottom:1px solid #f0f0f0;">{{ r.bandwidth_mbps }}Mbps</td>
<td style="padding:10px 12px;font-size:12px;color:#e53935;border-bottom:1px solid #f0f0f0;"><b>{{ r.end_date }}</b></td>
</tr>
{% endfor %}
</table>

<!-- Recycle Info -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;border:1px solid #e0e4e8;border-radius:6px;">
<tr><td colspan="2" style="background:#f9fafb;padding:10px 16px;font-size:14px;font-weight:bold;color:#333;border-bottom:1px solid #e0e4e8;">回收信息</td></tr>
<tr><td style="padding:10px 16px;font-size:13px;color:#666;width:120px;border-bottom:1px solid #f0f0f0;">回收原因</td>
<td style="padding:10px 16px;font-size:13px;color:#333;border-bottom:1px solid #f0f0f0;">到期未续</td></tr>
<tr><td style="padding:10px 16px;font-size:13px;color:#666;border-bottom:1px solid #f0f0f0;">计划回收时间</td>
<td style="padding:10px 16px;font-size:13px;color:#e53935;border-bottom:1px solid #f0f0f0;"><b>{{ rentals[0].end_date }}</b></td></tr>
<tr><td style="padding:10px 16px;font-size:13px;color:#666;">最后保留时间</td>
<td style="padding:10px 16px;font-size:13px;color:#e53935;"><b>{{ rentals[0].end_date }}</b></td></tr>
</table>

<!-- Important Notice -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#fce4ec;border:1px solid #ef9a9a;border-radius:6px;margin-bottom:20px;">
<tr><td style="padding:12px 16px;font-size:13px;color:#c62828;line-height:1.6;">
<b>⚠ 重要提醒：</b><br>
1. 请务必在回收时间前完成数据备份与迁移，回收后数据将无法恢复。<br>
2. 如需续租，请于到期前联系运维团队办理续租手续。<br>
3. 回收后将释放所有关联资源（IP、存储、网络配置等），不做保留。
</td></tr>
</table>

</td></tr>
</table>
</td></tr></table>
</body>
</html>"""

# ──────────────────────────────────────────────
# 执行更新
# ──────────────────────────────────────────────
TRIGGER_MAP = {
    'provision': PROVISION_HTML,
    'expiry_warning': EXPIRY_WARNING_HTML,
    'reclaim': RECLAIM_HTML,
}

db = SessionLocal()
try:
    for trigger_type, new_html in TRIGGER_MAP.items():
        templates = db.query(EmailTemplate).filter(
            EmailTemplate.trigger_type == trigger_type,
            EmailTemplate.is_active == True,
        ).all()

        if not templates:
            print(f'[SKIP] No active {trigger_type} templates found')
            continue

        for t in templates:
            old_len = len(t.body_html) if t.body_html else 0
            t.body_html = new_html
            t.version += 1
            new_len = len(t.body_html)
            print(
                f'[OK] Updated template id={t.id[:8]}, '
                f'trigger={trigger_type}, name={t.name}, '
                f'version={t.version}, body_html: {old_len}→{new_len} chars'
            )

    db.commit()
    print('\nDone — all templates updated and committed.')
finally:
    db.close()
