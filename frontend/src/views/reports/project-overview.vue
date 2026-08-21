<template>
  <div class="page-container project-overview-page" v-loading="loading">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="page-header__left">
        <div class="page-header__icon">
          <el-icon :size="18"><DataAnalysis /></el-icon>
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
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(37, 99, 235, 0.1); color: #2563EB">
          <el-icon :size="20"><Document /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-label-row">
            <span class="stat-label">合同总数</span>
            <span class="stat-sub">服务期内</span>
          </div>
          <div class="stat-value" style="color: #2563EB">{{ currentStats.totalContracts }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.1); color: #10b981">
          <el-icon :size="20"><Money /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-label-row">
            <span class="stat-label">总金额</span>
            <span class="stat-sub">累计金额</span>
          </div>
          <div class="stat-value" style="color: #10b981">{{ formatAmount(currentStats.totalAmount) }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b">
          <el-icon :size="20"><TrendCharts /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-label-row">
            <span class="stat-label">月度合同数</span>
            <span class="stat-sub">单月峰值</span>
          </div>
          <div class="stat-value" style="color: #f59e0b">{{ currentStats.maxMonthlyContracts }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(139, 92, 246, 0.1); color: #8b5cf6">
          <el-icon :size="20"><Coin /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-label-row">
            <span class="stat-label">月度金额</span>
            <span class="stat-sub">单月峰值</span>
          </div>
          <div class="stat-value" style="color: #8b5cf6">{{ formatAmount(currentStats.maxMonthlyAmount) }}</div>
        </div>
      </div>
    </div>

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
      <div class="panel-card__body panel-card__body--flush">
        <el-table
          ref="tableRef"
          :data="tableData"
          stripe
          size="default"
          row-key="month"
          class="monthly-table"
          style="width: 100%"
          @expand-change="onExpandChange"
        >
          <template #empty>
            <div class="table-empty">
              <el-empty description="暂无数据" :image-size="72" />
            </div>
          </template>
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-inner">
                <el-table
                  :data="row.contracts"
                  stripe
                  style="width: 100%"
                >
                  <template #empty>
                    <div class="table-empty table-empty--compact">
                      <el-empty description="该月暂无合同" :image-size="64" />
                    </div>
                  </template>
                  <el-table-column prop="name" label="合同名称" min-width="240" show-overflow-tooltip />
                  <el-table-column label="分摊金额" min-width="160" align="right">
                    <template #default="{ row: cr }">
                      {{ formatAmount(cr.monthly_amount) }}
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="month" label="月份" min-width="110" sortable />
          <el-table-column prop="active_contracts" label="合同数" min-width="90" align="center" sortable />
          <el-table-column label="金额" min-width="130" align="right" sortable sort-prop="monthly_amount_num">
            <template #default="{ row }">
              <span class="amount-cell">{{ formatAmount(row.monthly_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="CPU(核)" min-width="90" align="center">
            <template #default="{ row }">{{ row.resources.total_vcpu || '-' }}</template>
          </el-table-column>
          <el-table-column label="内存(GB)" min-width="100" align="center">
            <template #default="{ row }">{{ row.resources.total_memory_gb || '-' }}</template>
          </el-table-column>
          <el-table-column label="GPU(卡)" min-width="90" align="center">
            <template #default="{ row }">{{ row.resources.total_gpu_count || '-' }}</template>
          </el-table-column>
          <el-table-column label="GPU算力" min-width="90" align="center">
            <template #default="{ row }">{{ row.resources.total_gpu_tops || '-' }}</template>
          </el-table-column>
          <el-table-column label="存储" min-width="100" align="center">
            <template #default="{ row }">
              <template v-if="row.resources.total_storage_gb">
                {{ formatStorage(row.resources.total_storage_gb) }}
              </template>
              <template v-else>-</template>
            </template>
          </el-table-column>
          <el-table-column label="带宽(Mbps)" min-width="110" align="center">
            <template #default="{ row }">{{ row.resources.total_bandwidth_mbps || '-' }}</template>
          </el-table-column>
          <el-table-column label="机柜" min-width="80" align="center">
            <template #default="{ row }">{{ row.resources.total_rack_count || '-' }}</template>
          </el-table-column>
          <el-table-column label="IP" min-width="80" align="center">
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
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  color: #fff;
}

.page-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

/* ============================================================
 * 项目类型切换
 * ============================================================ */
.type-tabs :deep(.el-radio-button) {
  --el-radio-button-checked-bg-color: var(--primary-color);
  --el-radio-button-checked-border-color: var(--primary-color);
  --el-radio-button-checked-text-color: #fff;
}

.type-tabs :deep(.el-radio-button__inner) {
  padding: 8px 16px;
  border-radius: 0;
  font-weight: 500;
  color: var(--text-primary);
}

.type-tabs :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 8px 0 0 8px;
}

.type-tabs :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 8px 8px 0;
}

.type-tabs :deep(.el-radio-button:first-child:last-child .el-radio-button__inner) {
  border-radius: 8px;
}

.type-tabs :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  box-shadow: -1px 0 0 0 var(--primary-color);
}

.type-tabs :deep(.el-radio-button__inner:hover) {
  color: var(--primary-color);
}

/* ============================================================
 * 统计卡片
 * ============================================================ */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--card-bg);
  border-radius: 12px;
  padding: 18px 16px 18px 18px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
  border: none;
  min-width: 0;
}

.stat-card:hover {
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.08), 0 2px 6px rgba(15, 23, 42, 0.04);
  transform: translateY(-2px);
}

.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.stat-label {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
}

.stat-sub {
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ============================================================
 * 面板卡片（通用）
 * ============================================================ */
.chart-col {
  margin-bottom: 16px;
}

@media (min-width: 1200px) {
  .chart-col {
    margin-bottom: 0;
  }
}

.panel-card {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  border: none;
  height: 100%;
  transition: box-shadow 0.25s ease;
}

.panel-card:hover {
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.08), 0 2px 6px rgba(15, 23, 42, 0.04);
}

.panel-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 4px;
  background: var(--card-bg);
  border-bottom: none;
}

.panel-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  position: relative;
  padding-left: 10px;
}

.panel-card__title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--primary-color);
}

.panel-card__body {
  padding: 8px 20px 20px;
}

.panel-card__body--flush {
  padding: 8px 0 0;
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
  color: var(--text-secondary);
  font-size: 14px;
  opacity: 0.75;
}

/* ============================================================
 * 按月明细表格
 * ============================================================ */
.monthly-table {
  border-radius: 0;
  width: 100%;
}

.expand-inner {
  padding: 8px 16px;
  background: #fafbfc;
}

.amount-cell {
  font-weight: 600;
  color: var(--primary-color);
}

/* ============================================================
 * 响应式
 * ============================================================ */
@media (max-width: 768px) {
  .stat-value {
    font-size: 20px;
  }

  .chart-container {
    height: 280px;
  }

  .chart-container--lg {
    height: 300px;
  }

  .chart-empty {
    height: 280px;
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
const typeColors = ['#2563EB', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#0ea5e9', '#f97316']

const tooltipStyle = {
  backgroundColor: 'rgba(32, 46, 63, 0.92)',
  borderWidth: 0,
  padding: [10, 14] as [number, number],
  textStyle: { color: '#fff', fontSize: 12 },
  extraCssText: 'border-radius: 8px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);',
}

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
    color: typeColors,
    tooltip: {
      ...tooltipStyle,
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
        shadowStyle: { color: 'rgba(37, 99, 235, 0.06)' },
      },
      formatter: (params: any[]) => {
        if (!params?.length) return ''
        const month = params[0].axisValue
        let total = 0
        let rows = ''
        params.forEach((p: any) => {
          const val = Number(p.value) || 0
          total += val
          rows += `<div style="display:flex;align-items:center;justify-content:space-between;gap:24px;margin-top:6px;">
            <span style="display:inline-flex;align-items:center;gap:6px;">
              <span style="width:8px;height:8px;border-radius:50%;background:${p.color};"></span>${p.seriesName}
            </span>
            <strong>${val}</strong>
          </div>`
        })
        return `<div style="font-weight:600;margin-bottom:4px;">${month}</div>
          <div style="opacity:.75;font-size:11px;margin-bottom:2px;">合计 ${total} 份</div>${rows}`
      },
    },
    legend: {
      data: matrix.map((m) => m.typeName),
      bottom: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 16,
      textStyle: { fontSize: 12, color: '#3F5573' },
    },
    grid: { left: '2%', right: '3%', bottom: '14%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: { color: '#3F5573', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '合同数',
      minInterval: 1,
      nameTextStyle: { color: '#3F5573', fontSize: 11, padding: [0, 28, 0, 0] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#3F5573', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    },
    series: matrix.map((m, idx) => {
      const base = typeColors[idx % typeColors.length]
      return {
        name: m.typeName,
        type: 'bar',
        data: m.data,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: base },
            { offset: 1, color: `${base}99` },
          ]),
          borderRadius: [6, 6, 0, 0],
        },
        label: {
          show: matrix.length === 1,
          position: 'top',
          color: '#3F5573',
          fontSize: 11,
          fontWeight: 600,
          formatter: (p: any) => (p.value ? p.value : ''),
        },
        emphasis: {
          focus: 'series',
          itemStyle: {
            shadowBlur: 12,
            shadowColor: `${base}55`,
          },
          label: {
            show: true,
            position: 'top',
            color: base,
            fontSize: 11,
            fontWeight: 600,
          },
        },
        barMaxWidth: 36,
        barWidth: matrix.length === 1 ? 28 : undefined,
        barGap: '20%',
      }
    }),
    animationDuration: 800,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 500,
    animationEasingUpdate: 'cubicInOut',
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
      h('span', { style: 'font-weight:600;color:#2563EB;white-space:nowrap;' }, formatAmount(c.monthly_amount)),
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
      ...tooltipStyle,
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: { color: 'rgba(37, 99, 235, 0.35)', type: 'dashed' },
      },
      formatter: (params: any[]) => {
        if (!params?.length) return ''
        let html = `<div style="font-weight:600;margin-bottom:6px;">${params[0].axisValue}</div>`
        params.forEach((p: any) => {
          const val = p.seriesName === '金额' ? formatAmount(p.value) : p.value
          html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:24px;margin-top:6px;">
            <span style="display:inline-flex;align-items:center;gap:6px;">
              <span style="width:8px;height:8px;border-radius:50%;background:${p.color};"></span>${p.seriesName}
            </span>
            <strong>${val}</strong>
          </div>`
        })
        return html
      },
    },
    legend: {
      data: ['金额', '合同数'],
      bottom: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 20,
      textStyle: { fontSize: 12, color: '#3F5573' },
    },
    grid: { left: '2%', right: '3%', bottom: '14%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: { color: '#3F5573', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: '金额',
        nameTextStyle: { color: '#3F5573', fontSize: 11, padding: [0, 28, 0, 0] },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#3F5573',
          fontSize: 11,
          formatter: (v: number) => {
            if (v >= 1e8) return `${(v / 1e8).toFixed(1)}亿`
            if (v >= 1e4) return `${(v / 1e4).toFixed(0)}万`
            return `${v}`
          },
        },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      },
      {
        type: 'value',
        name: '合同数',
        minInterval: 1,
        nameTextStyle: { color: '#3F5573', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#3F5573', fontSize: 11 },
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
        showSymbol: true,
        lineStyle: { color: '#f59e0b', width: 3 },
        itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
        emphasis: {
          focus: 'series',
          scale: 1.3,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 158, 11, 0.22)' },
            { offset: 1, color: 'rgba(245, 158, 11, 0.02)' },
          ]),
        },
      },
      {
        name: '合同数',
        type: 'bar',
        yAxisIndex: 1,
        data: mergedContracts,
        barMaxWidth: 28,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#2563EB' },
            { offset: 1, color: '#93c5fd' },
          ]),
          borderRadius: [6, 6, 0, 0],
        },
        label: {
          show: true,
          position: 'top',
          color: '#3F5573',
          fontSize: 11,
          fontWeight: 600,
          formatter: (p: any) => (p.value ? p.value : ''),
        },
        emphasis: {
          focus: 'series',
          itemStyle: {
            shadowBlur: 12,
            shadowColor: 'rgba(37, 99, 235, 0.3)',
          },
        },
      },
    ],
    animationDuration: 800,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 500,
    animationEasingUpdate: 'cubicInOut',
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
      ...tooltipStyle,
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: { color: 'rgba(37, 99, 235, 0.35)', type: 'dashed' },
      },
      formatter: (params: any[]) => {
        if (!params?.length) return ''
        let html = `<div style="font-weight:600;margin-bottom:6px;">${params[0].axisValue}</div>`
        params.forEach((p: any) => {
          html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:24px;margin-top:6px;">
            <span style="display:inline-flex;align-items:center;gap:6px;">
              <span style="width:8px;height:8px;border-radius:50%;background:${p.color};"></span>${p.seriesName}
            </span>
            <strong>${p.value}</strong>
          </div>`
        })
        return html
      },
    },
    legend: {
      data: ['CPU(核)', '内存(GB)', 'GPU(卡)', '存储(TB)'],
      bottom: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 16,
      textStyle: { fontSize: 12, color: '#3F5573' },
    },
    grid: { left: '2%', right: '3%', bottom: '14%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: monthLabels,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: { color: '#3F5573', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '数量',
      nameTextStyle: { color: '#3F5573', fontSize: 11, padding: [0, 28, 0, 0] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#3F5573', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    },
    series: [
      {
        name: 'CPU(核)',
        type: 'line',
        data: cpuData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: true,
        lineStyle: { color: '#2563EB', width: 2.5 },
        itemStyle: { color: '#2563EB', borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'series', scale: 1.25 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.16)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
          ]),
        },
      },
      {
        name: '内存(GB)',
        type: 'line',
        data: memData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: true,
        lineStyle: { color: '#10b981', width: 2.5 },
        itemStyle: { color: '#10b981', borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'series', scale: 1.25 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.12)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.01)' },
          ]),
        },
      },
      {
        name: 'GPU(卡)',
        type: 'line',
        data: gpuData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: true,
        lineStyle: { color: '#f59e0b', width: 2.5 },
        itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'series', scale: 1.25 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 158, 11, 0.12)' },
            { offset: 1, color: 'rgba(245, 158, 11, 0.01)' },
          ]),
        },
      },
      {
        name: '存储(TB)',
        type: 'line',
        data: storageData.map((v) => (v / 1024).toFixed(1)),
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: true,
        lineStyle: { color: '#ef4444', width: 2.5 },
        itemStyle: { color: '#ef4444', borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'series', scale: 1.25 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(239, 68, 68, 0.12)' },
            { offset: 1, color: 'rgba(239, 68, 68, 0.01)' },
          ]),
        },
      },
    ],
    animationDuration: 800,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 500,
    animationEasingUpdate: 'cubicInOut',
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
