<template>
  <div class="page-container project-overview-page" v-loading="loading">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="page-header__left">
        <div class="page-header__icon">
          <el-icon :size="20"><DataAnalysis /></el-icon>
        </div>
        <span class="page-header__title">项目概览</span>
      </div>
      <div class="page-header__right">
        <el-select
          v-model="selectedYear"
          size="default"
          style="width: 120px"
          @change="fetchOverview"
        >
          <el-option
            v-for="y in yearOptions"
            :key="y"
            :label="String(y)"
            :value="y"
          />
        </el-select>
      </div>
    </div>

    <!-- 项目类型切换 -->
    <div class="type-tabs">
      <el-radio-group
        v-model="selectedType"
        size="default"
        @change="onTypeChange"
      >
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button
          v-for="pt in projectTypes"
          :key="pt"
          :value="pt"
        >
          {{ pt }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 统计卡片行 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="24" :sm="12" :md="6" class="stat-col">
        <div class="stat-card stat-card--contracts">
          <div class="stat-card__icon">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="stat-card__body">
            <div class="stat-card__label">合同总数</div>
            <div class="stat-card__value">{{ currentStats.totalContracts }}</div>
            <div class="stat-card__sub">服务期内</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="stat-col">
        <div class="stat-card stat-card--amount">
          <div class="stat-card__icon">
            <el-icon :size="24"><Money /></el-icon>
          </div>
          <div class="stat-card__body">
            <div class="stat-card__label">总金额</div>
            <div class="stat-card__value stat-card__value--highlight">
              {{ formatAmount(currentStats.totalAmount) }}
            </div>
            <div class="stat-card__sub">累计金额</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="stat-col">
        <div class="stat-card stat-card--new-contracts">
          <div class="stat-card__icon">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-card__body">
            <div class="stat-card__label">月度合同数</div>
            <div class="stat-card__value">{{ currentStats.maxMonthlyContracts }}</div>
            <div class="stat-card__sub">单月峰值</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="stat-col">
        <div class="stat-card stat-card--monthly-amount">
          <div class="stat-card__icon">
            <el-icon :size="24"><Coin /></el-icon>
          </div>
          <div class="stat-card__body">
            <div class="stat-card__label">月度金额</div>
            <div class="stat-card__value stat-card__value--highlight">
              {{ formatAmount(currentStats.maxMonthlyAmount) }}
            </div>
            <div class="stat-card__sub">单月峰值</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表行：月度合同数柱状图 + 月度金额趋势 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="12" class="chart-col">
        <div class="panel-card">
          <div class="panel-card__header">
            <span class="panel-card__title">月度服务期内合同数</span>
          </div>
          <div class="panel-card__body">
            <div v-if="allMonthlyData.length === 0" class="chart-empty">暂无数据</div>
            <div v-else id="chart-monthly-contracts" class="chart-container"></div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="12" class="chart-col">
        <div class="panel-card">
          <div class="panel-card__header">
            <span class="panel-card__title">月度金额趋势</span>
          </div>
          <div class="panel-card__body">
            <div v-if="allMonthlyData.length === 0" class="chart-empty">暂无数据</div>
            <div v-else id="chart-monthly-amount" class="chart-container"></div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 月度资源消耗趋势 -->
    <div class="panel-card chart-row">
      <div class="panel-card__header">
        <span class="panel-card__title">月度资源消耗趋势</span>
      </div>
      <div class="panel-card__body">
        <div v-if="allMonthlyData.length === 0" class="chart-empty">暂无数据</div>
        <div v-else id="chart-resources" class="chart-container chart-container--lg"></div>
      </div>
    </div>

    <!-- 月度明细表 -->
    <div class="panel-card">
      <div class="panel-card__header">
        <span class="panel-card__title">月度明细</span>
        <el-button text type="primary" size="small" @click="toggleExpandAll">
          {{ allExpanded ? '全部收起' : '全部展开' }}
        </el-button>
      </div>
      <div class="panel-card__body" style="padding: 0">
        <el-table
          ref="tableRef"
          :data="tableData"
          stripe
          size="default"
          empty-text="暂无数据"
          row-key="month"
          class="monthly-table"
          @expand-change="onExpandChange"
        >
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-inner">
                <el-table
                  :data="row.contracts"
                  stripe
                  size="small"
                  empty-text="该月暂无合同"
                >
                  <el-table-column prop="name" label="合同名称" min-width="180" show-overflow-tooltip />
                  <el-table-column label="分摊金额" width="140" align="right">
                    <template #default="{ row: cr }">
                      {{ formatAmount(cr.monthly_amount) }}
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="month" label="月份" width="120" sortable />
          <el-table-column prop="active_contracts" label="合同数" width="90" align="center" sortable />
          <el-table-column label="金额" width="150" align="right" sortable sort-prop="monthly_amount_num">
            <template #default="{ row }">
              <span class="amount-cell">{{ formatAmount(row.monthly_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="CPU(核)" width="90" align="center">
            <template #default="{ row }">{{ row.resources.total_vcpu || '-' }}</template>
          </el-table-column>
          <el-table-column label="内存(GB)" width="100" align="center">
            <template #default="{ row }">{{ row.resources.total_memory_gb || '-' }}</template>
          </el-table-column>
          <el-table-column label="GPU(卡)" width="90" align="center">
            <template #default="{ row }">{{ row.resources.total_gpu_count || '-' }}</template>
          </el-table-column>
          <el-table-column label="GPU算力" width="90" align="center">
            <template #default="{ row }">{{ row.resources.total_gpu_tops || '-' }}</template>
          </el-table-column>
          <el-table-column label="存储" width="100" align="center">
            <template #default="{ row }">
              <template v-if="row.resources.total_storage_gb">
                {{ formatStorage(row.resources.total_storage_gb) }}
              </template>
              <template v-else>-</template>
            </template>
          </el-table-column>
          <el-table-column label="带宽(Mbps)" width="110" align="center">
            <template #default="{ row }">{{ row.resources.total_bandwidth_mbps || '-' }}</template>
          </el-table-column>
          <el-table-column label="机柜" width="70" align="center">
            <template #default="{ row }">{{ row.resources.total_rack_count || '-' }}</template>
          </el-table-column>
          <el-table-column label="IP" width="70" align="center">
            <template #default="{ row }">{{ row.resources.total_ip_count || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============================================================
 * 页面头部
 * ============================================================ */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-header__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
}

.page-header__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

/* ============================================================
 * 项目类型切换
 * ============================================================ */
.type-tabs {
  margin-bottom: 16px;
}

.type-tabs :deep(.el-radio-button__inner) {
  padding: 8px 20px;
}

/* ============================================================
 * 统计卡片
 * ============================================================ */
.stat-row {
  margin-bottom: 16px;
}

.stat-col {
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--card-bg);
  border-radius: 12px;
  padding: 20px 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: all 0.25s ease;
  cursor: default;
  height: 100%;
  border: 1px solid transparent;
}

.stat-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10);
  transform: translateY(-2px);
}

.stat-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  flex-shrink: 0;
}

.stat-card--contracts .stat-card__icon {
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
}

.stat-card--amount .stat-card__icon {
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}

.stat-card--new-contracts .stat-card__icon {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
}

.stat-card--monthly-amount .stat-card__icon {
  background: rgba(142, 92, 229, 0.1);
  color: #8e5ce5;
}

.stat-card__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-card__label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-card__value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  letter-spacing: -0.5px;
}

.stat-card__value--highlight {
  color: #409eff;
  font-size: 22px;
}

.stat-card__sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 1px;
}

/* ============================================================
 * 面板卡片（通用）
 * ============================================================ */
.chart-row {
  margin-bottom: 16px;
}

.chart-col {
  margin-bottom: 16px;
}

.panel-card {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  border: 1px solid #ebeef5;
}

.panel-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-card__body {
  padding: 20px;
}

/* ============================================================
 * 图表区域
 * ============================================================ */
.chart-container {
  width: 100%;
  height: 340px;
}

.chart-container--lg {
  height: 380px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 340px;
  color: #c0c4cc;
  font-size: 14px;
}

/* ============================================================
 * 按月明细表格
 * ============================================================ */
.monthly-table {
  border-radius: 0;
}

.monthly-table :deep(.el-table__header th) {
  background: #f8fafc !important;
}

.expand-inner {
  padding: 8px 16px;
  background: #fafbfc;
}

.amount-cell {
  font-weight: 600;
  color: #409eff;
}

/* ============================================================
 * 响应式
 * ============================================================ */
@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-card__value {
    font-size: 22px;
  }

  .stat-card__value--highlight {
    font-size: 18px;
  }

  .page-header__title {
    font-size: 17px;
  }

  .chart-container {
    height: 280px;
  }

  .chart-container--lg {
    height: 300px;
  }
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, h } from 'vue'
import { DataAnalysis, Document, Money, TrendCharts, Coin } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  getProjectOverview,
  type ProjectOverviewResponse,
  type OverviewProjectTypeStat,
  type OverviewMonthlyStat,
} from '@/api/modules/project'

// ============================================================
// 状态
// ============================================================
const loading = ref(false)
const selectedYear = ref(new Date().getFullYear())
const selectedType = ref('')
const overview = ref<ProjectOverviewResponse>({ year: selectedYear.value, by_project_type: [] })

/** 全部展开状态 */
const allExpanded = ref(false)

// ============================================================
// 年份选项
// ============================================================
const currentYear = new Date().getFullYear()
const yearOptions = computed(() => {
  const years: number[] = []
  for (let y = currentYear - 2; y <= currentYear + 3; y++) {
    years.push(y)
  }
  return years
})

// ============================================================
// 项目类型列表
// ============================================================
const projectTypes = computed(() => {
  return overview.value.by_project_type.map((pt) => pt.project_type)
})

// ============================================================
// ECharts 实例
// ============================================================
let contractsChart: echarts.ECharts | null = null
let amountChart: echarts.ECharts | null = null
let resourcesChart: echarts.ECharts | null = null

// ============================================================
// 颜色常量
// ============================================================
const typeColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#8e5ce5', '#36b4c1', '#f0a732']

// ============================================================
// 工具函数
// ============================================================
function formatAmount(val: string | number | null | undefined): string {
  if (val === null || val === undefined || val === '') return '-'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '-'
  if (n >= 1e8) return `¥${(n / 1e8).toFixed(2)}亿`
  if (n >= 1e4) return `¥${(n / 1e4).toFixed(0)}万`
  return `¥${n.toLocaleString('zh-CN')}`
}

function formatStorage(gb: number): string {
  if (gb >= 1024) return `${(gb / 1024).toFixed(0)}TB`
  return `${gb}GB`
}

// ============================================================
// 筛选后的数据
// ============================================================

/** 当前选中的项目类型数据 */
const filteredTypes = computed<OverviewProjectTypeStat[]>(() => {
  if (!selectedType.value) return overview.value.by_project_type
  return overview.value.by_project_type.filter((pt) => pt.project_type === selectedType.value)
})

/** 所有月度数据（合并去重，按月份排序） */
const allMonthlyData = computed<OverviewMonthlyStat[]>(() => {
  const monthMap = new Map<string, OverviewMonthlyStat>()

  for (const pt of filteredTypes.value) {
    for (const m of (pt.monthly || [])) {
      const existing = monthMap.get(m.month)
      if (existing) {
        // 合并：累加合同数和金额
        existing.active_contracts += m.active_contracts
        existing.monthly_amount = (
          parseFloat(existing.monthly_amount) + parseFloat(m.monthly_amount)
        ).toFixed(2)
        existing.contracts.push(...m.contracts)
        // 合并资源
        const r = existing.resources
        const mr = m.resources
        r.total_vcpu += mr.total_vcpu
        r.total_memory_gb += mr.total_memory_gb
        r.total_storage_gb += mr.total_storage_gb
        r.total_gpu_count += mr.total_gpu_count
        r.total_gpu_tops += mr.total_gpu_tops
        r.total_bandwidth_mbps += mr.total_bandwidth_mbps
        r.total_rack_count += mr.total_rack_count
        r.total_ip_count += mr.total_ip_count
      } else {
        // 深拷贝避免修改原始数据
        monthMap.set(m.month, {
          month: m.month,
          active_contracts: m.active_contracts,
          monthly_amount: m.monthly_amount,
          contracts: [...m.contracts],
          resources: { ...m.resources },
        })
      }
    }
  }

  return Array.from(monthMap.values()).sort((a, b) => a.month.localeCompare(b.month))
})

/** 表格数据（增强：添加 monthly_amount_num 用于排序） */
const tableData = computed(() => {
  return allMonthlyData.value.map((m) => ({
    ...m,
    monthly_amount_num: parseFloat(m.monthly_amount),
  }))
})

/** 当前统计卡片数据 */
const currentStats = computed(() => {
  const types = filteredTypes.value

  let totalContracts = 0
  let totalAmount = 0
  let maxMonthlyContracts = 0
  let maxMonthlyAmount = 0

  for (const pt of types) {
    totalContracts += pt.total_contracts
    totalAmount += parseFloat(pt.total_amount)
    for (const m of (pt.monthly || [])) {
      if (m.active_contracts > maxMonthlyContracts) {
        maxMonthlyContracts = m.active_contracts
      }
      const amt = parseFloat(m.monthly_amount)
      if (amt > maxMonthlyAmount) {
        maxMonthlyAmount = amt
      }
    }
  }

  return {
    totalContracts,
    totalAmount: totalAmount.toFixed(2),
    maxMonthlyContracts,
    maxMonthlyAmount: maxMonthlyAmount.toFixed(2),
  }
})

// ============================================================
// 数据获取
// ============================================================
async function fetchOverview() {
  loading.value = true
  try {
    const data = await getProjectOverview(selectedYear.value)
    overview.value = data
    // 重置筛选
    if (selectedType.value && !data.by_project_type.some((pt) => pt.project_type === selectedType.value)) {
      selectedType.value = ''
    }
    allExpanded.value = false
    await nextTick()
    renderAllCharts()
  } catch {
    // 错误已由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function onTypeChange() {
  nextTick(() => renderAllCharts())
}

// ============================================================
// 图表渲染
// ============================================================

/** 获取 X 轴月份标签 */
function getMonthLabels(): string[] {
  return Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
}

/** 获取按类型+月份索引的合同数矩阵 */
function getContractsMatrix(): { typeName: string; data: number[] }[] {
  return filteredTypes.value.map((pt) => {
    const data = Array(12).fill(0)
    for (const m of (pt.monthly || [])) {
      const monthIdx = parseInt(m.month.split('-')[1], 10) - 1
      if (monthIdx >= 0 && monthIdx < 12) {
        data[monthIdx] = m.active_contracts
      }
    }
    return { typeName: pt.project_type, data }
  })
}

/** 获取按类型+月份索引的金额矩阵 */
function getAmountsMatrix(): { typeName: string; data: number[] }[] {
  return filteredTypes.value.map((pt) => {
    const data = Array(12).fill(0)
    for (const m of (pt.monthly || [])) {
      const monthIdx = parseInt(m.month.split('-')[1], 10) - 1
      if (monthIdx >= 0 && monthIdx < 12) {
        data[monthIdx] = parseFloat(m.monthly_amount) || 0
      }
    }
    return { typeName: pt.project_type, data }
  })
}

/** 图表：月度服务期内合同数（分组柱状图） */
function renderContractsChart() {
  const dom = document.getElementById('chart-monthly-contracts')
  if (!dom) return

  contractsChart?.dispose()
  contractsChart = echarts.init(dom)

  const matrix = getContractsMatrix()
  const monthLabels = getMonthLabels()

  contractsChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      data: matrix.map((m) => m.typeName),
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: { left: '3%', right: '4%', bottom: '14%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
      axisLabel: { color: '#909399', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '合同数',
      minInterval: 1,
      nameTextStyle: { color: '#909399', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#909399', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    series: matrix.map((m, idx) => ({
      name: m.typeName,
      type: 'bar',
      data: m.data,
      itemStyle: {
        color: typeColors[idx % typeColors.length],
        borderRadius: [4, 4, 0, 0],
      },
      emphasis: {
        itemStyle: { color: typeColors[idx % typeColors.length], shadowBlur: 8 },
      },
      barWidth: matrix.length === 1 ? 28 : undefined,
      barGap: '20%',
    })),
  })

  // 点击柱子事件
  contractsChart.off('click')
  contractsChart.on('click', (params: any) => {
    if (params.componentType === 'series') {
      const monthIdx = params.dataIndex + 1
      const monthStr = `${selectedYear.value}-${String(monthIdx).padStart(2, '0')}`
      const contracts = allMonthlyData.value.find((m) => m.month === monthStr)?.contracts ?? []
      if (contracts.length > 0) {
        showContractsDialog(monthStr, contracts)
      }
    }
  })
}

/** 弹出该月合同列表 */
function showContractsDialog(month: string, contracts: { id: string; name: string; monthly_amount: string }[]) {
  const vnodes = contracts.map((c) =>
    h('div', { style: 'display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;' }, [
      h('span', { style: 'flex:1;margin-right:16px;' }, c.name),
      h('span', { style: 'font-weight:600;color:#409eff;white-space:nowrap;' }, formatAmount(c.monthly_amount)),
    ]),
  )

  ElMessageBox({
    title: `${month} 合同列表`,
    message: h('div', { style: 'max-height:400px;overflow-y:auto;' }, vnodes),
    confirmButtonText: '关闭',
  })
}

/** 图表：月度金额趋势（折线+柱状双Y轴） */
function renderAmountChart() {
  const dom = document.getElementById('chart-monthly-amount')
  if (!dom) return

  amountChart?.dispose()
  amountChart = echarts.init(dom)

  const amountMatrix = getAmountsMatrix()
  const contractsMatrix = getContractsMatrix()
  const monthLabels = getMonthLabels()

  // 合并所有类型的金额和合同数（按月份汇总）
  const mergedAmounts = Array(12).fill(0)
  const mergedContracts = Array(12).fill(0)
  for (const m of amountMatrix) {
    m.data.forEach((v, i) => { mergedAmounts[i] += v })
  }
  for (const m of contractsMatrix) {
    m.data.forEach((v, i) => { mergedContracts[i] += v })
  }

  amountChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#999' } },
      formatter: (params: any[]) => {
        const month = params[0]?.axisValue ?? ''
        let html = `<div style="font-weight:600;margin-bottom:6px;">${month}</div>`
        params.forEach((p: any) => {
          const val = p.seriesName === '金额' ? formatAmount(p.value) : p.value
          html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};"></span>
              ${p.seriesName}: <strong>${val}</strong>
            </div>`
        })
        return html
      },
    },
    legend: {
      data: ['金额', '合同数'],
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: { left: '3%', right: '4%', bottom: '14%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
      axisLabel: { color: '#909399', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: '金额',
        nameTextStyle: { color: '#909399', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#909399',
          fontSize: 11,
          formatter: (v: number) => {
            if (v >= 1e8) return `${(v / 1e8).toFixed(1)}亿`
            if (v >= 1e4) return `${(v / 1e4).toFixed(0)}万`
            return `${v}`
          },
        },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      },
      {
        type: 'value',
        name: '合同数',
        minInterval: 1,
        nameTextStyle: { color: '#909399', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#909399', fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '金额',
        type: 'line',
        data: mergedAmounts,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#e6a23c', width: 3 },
        itemStyle: { color: '#e6a23c', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(230, 162, 60, 0.15)' },
            { offset: 1, color: 'rgba(230, 162, 60, 0.02)' },
          ]),
        },
      },
      {
        name: '合同数',
        type: 'bar',
        yAxisIndex: 1,
        data: mergedContracts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409eff' },
            { offset: 1, color: '#79bbff' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        barWidth: 28,
      },
    ],
  })
}

/** 图表：月度资源消耗趋势（多折线图） */
function renderResourcesChart() {
  const dom = document.getElementById('chart-resources')
  if (!dom) return

  resourcesChart?.dispose()
  resourcesChart = echarts.init(dom)

  const monthLabels = getMonthLabels()
  const cpuData = Array(12).fill(0)
  const memData = Array(12).fill(0)
  const gpuData = Array(12).fill(0)
  const storageData = Array(12).fill(0)

  for (const m of allMonthlyData.value) {
    const monthIdx = parseInt(m.month.split('-')[1], 10) - 1
    if (monthIdx >= 0 && monthIdx < 12) {
      cpuData[monthIdx] += m.resources.total_vcpu
      memData[monthIdx] += m.resources.total_memory_gb
      gpuData[monthIdx] += m.resources.total_gpu_count
      storageData[monthIdx] += m.resources.total_storage_gb
    }
  }

  resourcesChart.setOption({
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: ['CPU(核)', '内存(GB)', 'GPU(卡)', '存储(TB)'],
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: { left: '3%', right: '4%', bottom: '14%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
      axisLabel: { color: '#909399', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '数量',
      nameTextStyle: { color: '#909399', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#909399', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    series: [
      {
        name: 'CPU(核)',
        type: 'line',
        data: cpuData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' },
      },
      {
        name: '内存(GB)',
        type: 'line',
        data: memData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#67c23a', width: 2 },
        itemStyle: { color: '#67c23a' },
      },
      {
        name: 'GPU(卡)',
        type: 'line',
        data: gpuData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#e6a23c', width: 2 },
        itemStyle: { color: '#e6a23c' },
      },
      {
        name: '存储(TB)',
        type: 'line',
        data: storageData.map((v) => (v / 1024).toFixed(1)),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#f56c6c', width: 2 },
        itemStyle: { color: '#f56c6c' },
      },
    ],
  })
}

function renderAllCharts() {
  renderContractsChart()
  renderAmountChart()
  renderResourcesChart()
}

// ============================================================
// 展开/收起
// ============================================================
const tableRef = ref<any>(null)

function onExpandChange(_row: any, _expandedRows: any[]) {
  // 展开时不需要额外加载，contracts 已在数据中
}

async function toggleExpandAll() {
  if (allExpanded.value) {
    tableData.value.forEach((row) => {
      tableRef.value?.toggleRowExpansion(row, false)
    })
    allExpanded.value = false
  } else {
    for (const row of tableData.value) {
      tableRef.value?.toggleRowExpansion(row, true)
    }
    allExpanded.value = true
  }
}

// ============================================================
// 窗口自适应
// ============================================================
function handleResize() {
  contractsChart?.resize()
  amountChart?.resize()
  resourcesChart?.resize()
}

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  window.addEventListener('resize', handleResize)
  fetchOverview()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  contractsChart?.dispose()
  amountChart?.dispose()
  resourcesChart?.dispose()
})
</script>
