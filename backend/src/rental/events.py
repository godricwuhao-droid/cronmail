"""
租赁模块事件定义
使用 blinker 实现发布/订阅模式
"""
import blinker

# 租赁开通事件
rental_provisioned = blinker.signal('rental.provisioned')

# 租赁临期事件
rental_expiring = blinker.signal('rental.expiring')

# 租赁到期事件
rental_expired = blinker.signal('rental.expired')

# 租赁回收事件
rental_reclaimed = blinker.signal('rental.reclaimed')
