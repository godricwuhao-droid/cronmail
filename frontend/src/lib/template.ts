/**
 * 模板模块共享常量与工具
 */
import type { TriggerType } from '@/api/modules/template'

/** 触发类型 → 中文 */
export const TRIGGER_TYPE_LABEL: Record<TriggerType, string> = {
  provision: '开通通知',
  expiry_warning: '临期提醒',
  expiry_notice: '到期提醒',
  reclaim: '回收通知',
}

/** 触发类型 → el-tag 颜色 */
export const TRIGGER_TYPE_TAG: Record<TriggerType, 'success' | 'warning' | 'danger'> = {
  provision: 'success',
  expiry_warning: 'warning',
  expiry_notice: 'danger',
  reclaim: 'danger',
}

/** 模板预览时默认填充的样例数据 */
export const DEFAULT_TEMPLATE_SAMPLE: Record<string, unknown> = {
  customer_name: '某科技公司',
  machine_model: 'Dell PowerEdge R740',
  cpu_model: '2×Intel Xeon Gold 6248R 48C',
  memory_gb: 256,
  gpu_info: '8×NVIDIA A100 80GB',
  system_disk: '480GB SATA SSD',
  data_disks: ['2000GB NVMe SSD', '4000GB SATA SSD'],
  os_version: 'Ubuntu 22.04 LTS',
  bandwidth_mbps: 1000,
  rack_location: 'A01-05-U12',
  private_ip: '10.0.0.1',
  public_ips: ['1.2.3.4', '1.2.3.5'],
  ssh_port: 22,
  root_username: 'root',
  root_password: 'TempPass123!',
  start_date: '2026-06-01',
  end_date: '2026-12-01',
  billing_model: 'monthly',
  auto_renew: false,
  remark: '常规租赁',
}
