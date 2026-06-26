"""
更新 reclaim 邮件模板措辞（一次性脚本）
将第一段文字改为"即将回收"语气，强调在回收前做好备份。

用法：在能连数据库的环境中运行
    python3 update_reclaim_template.py
"""
import sys
sys.path.insert(0, '.')

from src.contract.models import Contract
from src.rental.models import RentalRecord
from src.customer.models import Customer, Contact
from src.mail.models import EmailLog
from src.system.models import SystemConfig
from src.template.models import EmailTemplate
from src.core.database import SessionLocal

db = SessionLocal()
try:
    templates = db.query(EmailTemplate).filter(
        EmailTemplate.trigger_type == 'reclaim',
        EmailTemplate.is_active == True,
    ).all()

    if not templates:
        print('No active reclaim templates found')
    else:
        print(f'Found {len(templates)} active reclaim template(s)')

    new_first_para = '以下裸金属服务器资源即将执行回收，请提前做好数据备份与迁移工作。'
    old_text = '根据资源管理规定，以下裸金属服务器资源即将执行回收，请提前做好数据备份与迁移工作。'

    for t in templates:
        if old_text in t.body_html:
            t.body_html = t.body_html.replace(old_text, new_first_para)
            t.version += 1
            print(f'Updated template id={t.id[:8]}, name={t.name}, new version={t.version}')
        else:
            print(f'Template id={t.id[:8]}: old text not found in body, skipping')

    db.commit()
    print('Done')
finally:
    db.close()
