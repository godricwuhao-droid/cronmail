<template>
  <div class="page-container overview-page" v-loading="loading">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="page-header__left">
        <div class="page-header__icon">
          <el-icon :size="18"><DataAnalysis /></el-icon>
        </div>
        <span class="page-header__title">运营概览</span>
      </div>
    </div>

    <!-- 第一行：柱状图 + 扇形图 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="14" class="chart-col">
        <div class="panel-card">
          <div class="panel-card__header">
            <span class="panel-card__title">客户租用设备排行</span>
          </div>
          <div class="panel-card__body">
            <div v-if="stats.rental_by_customer.length === 0" class="chart-empty">暂无数据</div>
            <div v-else id="chart-customer" class="chart-container"></div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="10" class="chart-col">
        <div class="panel-card">
          <div class="panel-card__header">
            <span class="panel-card__title">机器型号分布</span>
          </div>
          <div class="panel-card__body">
            <div v-if="stats.rental_by_model.length === 0" class="chart-empty">暂无数据</div>
            <div v-else id="chart-model" class="chart-container"></div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 第二行：趋势图 -->
    <div class="panel-card">
      <div class="panel-card__header">
        <span class="panel-card__title">合同趋势（近12个月）</span>
      </div>
      <div class="panel-card__body">
        <div v-if="stats.contract_trend.length === 0" class="chart-empty chart-empty--trend">暂无数据</div>
        <div v-else id="chart-trend" class="chart-container chart-container--trend"></div>
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
  margin-bottom: 0;
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
 * 面板卡片
 * ============================================================ */
.chart-row {
  margin-bottom: 0;
}

.chart-col {
  margin-bottom: 0;
}

@media (max-width: 1199px) {
  .chart-col {
    margin-bottom: 16px;
  }

  .chart-col:last-child {
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

/* ============================================================
 * 图表区域
 * ============================================================ */
.chart-container {
  width: 100%;
  height: 360px;
}

.chart-container--trend {
  height: 320px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 360px;
  color: #c0c4cc;
  font-size: 14px;
}

.chart-empty--trend {
  height: 320px;
}

@media (max-width: 768px) {
  .chart-container {
    height: 280px;
  }

  .chart-container--trend {
    height: 260px;
  }

  .chart-empty {
    height: 280px;
  }

  .chart-empty--trend {
    height: 260px;
  }
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { DataAnalysis } from '@element-plus/icons-vue'
import request from '@/api'

// ============================================================
// 类型定义
// ============================================================
interface OverviewStats {
  rental_by_customer: Array<{
    customer_name: string
    models: Array<{ machine_model: string; count: number }>
  }>
  rental_by_model: Array<{ machine_model: string; count: number }>
  contract_trend: Array<{ month: string; created_count: number; expired_count: number }>
}

// ============================================================
// 状态
// ============================================================
const stats = ref<OverviewStats>({
  rental_by_customer: [],
  rental_by_model: [],
  contract_trend: [],
})
const loading = ref(false)

// ============================================================
// ECharts 实例引用
// ============================================================
let customerChart: echarts.ECharts | null = null
let modelChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

// ============================================================
// 主题色（与 global.css 一致）
// ============================================================
const themeColors = [
  '#2563EB', '#10b981', '#f59e0b', '#ef4444', '#64748b',
  '#0ea5e9', '#8b5cf6', '#f97316',
]

const tooltipStyle = {
  backgroundColor: 'rgba(32, 46, 63, 0.92)',
  borderWidth: 0,
  padding: [10, 14],
  textStyle: { color: '#fff', fontSize: 12 },
  extraCssText: 'border-radius: 8px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);',
}

// ============================================================
// 数据获取
// ============================================================
async function fetchStats() {
  loading.value = true
  try {
    const data = await request.get<OverviewStats>('/contracts/dashboard/overview-stats')
    stats.value = data
    await nextTick()
    renderCharts()
  } catch {
    // 错误已由拦截器统一处理
  } finally {
    loading.value = false
  }
}

// ============================================================
// 图表渲染入口
// ============================================================
function renderCharts() {
  initCustomerChart()
  initModelChart()
  initTrendChart()
}

// ============================================================
// 堆叠柱状图：客户租用设备排行（按机型堆叠）
// ============================================================
function initCustomerChart() {
  const dom = document.getElementById('chart-customer')
  if (!dom) return

  customerChart?.dispose()
  customerChart = echarts.init(dom)

  const data = stats.value.rental_by_customer

  // 收集所有机型名（用于 legend 和 series）
  const modelSet = new Set<string>()
  data.forEach((c) => c.models.forEach((m) => modelSet.add(m.machine_model)))
  const models = Array.from(modelSet)

  customerChart.setOption({
    color: themeColors,
    tooltip: {
      ...tooltipStyle,
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
        shadowStyle: { color: 'rgba(37, 99, 235, 0.06)' },
      },
      formatter: (params: any[]) => {
        if (!params?.length) return ''
        const name = params[0].axisValue
        let total = 0
        let rows = ''
        params.forEach((p: any) => {
          total += Number(p.value) || 0
          rows += `<div style="display:flex;align-items:center;justify-content:space-between;gap:24px;margin-top:6px;">
            <span style="display:inline-flex;align-items:center;gap:6px;">
              <span style="width:8px;height:8px;border-radius:50%;background:${p.color};"></span>${p.seriesName}
            </span>
            <strong>${p.value}</strong>
          </div>`
        })
        return `<div style="font-weight:600;margin-bottom:4px;">${name}</div>
          <div style="opacity:.75;font-size:11px;margin-bottom:2px;">合计 ${total} 台</div>${rows}`
      },
    },
    legend: {
      data: models,
      bottom: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 16,
      textStyle: { fontSize: 12, color: '#3F5573' },
    },
    grid: { left: '2%', right: '3%', bottom: '16%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((c) => c.customer_name),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: {
        rotate: data.length > 5 ? 30 : 0,
        fontSize: 11,
        color: '#64748b',
        interval: 0,
      },
    },
    yAxis: {
      type: 'value',
      name: '台',
      minInterval: 1,
      nameTextStyle: { color: '#94a3b8', fontSize: 11, padding: [0, 28, 0, 0] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    },
    series: models.map((modelName, idx) => ({
      name: modelName,
      type: 'bar',
      stack: 'total',
      barMaxWidth: 36,
      emphasis: { focus: 'series' },
      itemStyle: {
        color: themeColors[idx % themeColors.length],
        borderRadius: idx === models.length - 1 ? [4, 4, 0, 0] : 0,
      },
      data: data.map((c) => {
        const found = c.models.find((m) => m.machine_model === modelName)
        return found ? found.count : 0
      }),
    })),
    animationDuration: 600,
    animationEasing: 'cubicOut',
  })
}

// ============================================================
// 扇形图：机器型号分布
// ============================================================
function initModelChart() {
  const dom = document.getElementById('chart-model')
  if (!dom) return

  modelChart?.dispose()
  modelChart = echarts.init(dom)

  const pieData = stats.value.rental_by_model.map((r) => ({
    name: r.machine_model,
    value: r.count,
  }))
  const total = pieData.reduce((sum, d) => sum + d.value, 0)

  modelChart.setOption({
    color: themeColors,
    tooltip: {
      ...tooltipStyle,
      trigger: 'item',
      formatter: (p: any) =>
        `<div style="font-weight:600;margin-bottom:6px;">${p.name}</div>
         <div>${p.value} 台 · <strong>${p.percent}%</strong></div>`,
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 14,
      textStyle: { fontSize: 12, color: '#3F5573' },
    },
    title: {
      text: `{num|${total}}\n{unit|台}`,
      left: 'center',
      top: '40%',
      textStyle: {
        rich: {
          num: {
            fontSize: 28,
            fontWeight: 700,
            color: '#202E3F',
            lineHeight: 34,
            fontFamily: 'DIN Alternate, Segoe UI, sans-serif',
          },
          unit: {
            fontSize: 12,
            color: '#94a3b8',
            lineHeight: 20,
          },
        },
      },
    },
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '46%'],
        padAngle: 2,
        data: pieData,
        label: {
          formatter: '{d}%',
          color: '#64748b',
          fontSize: 11,
        },
        labelLine: {
          length: 12,
          length2: 8,
          lineStyle: { color: '#cbd5e1' },
        },
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        emphasis: {
          scale: true,
          scaleSize: 6,
          itemStyle: {
            shadowBlur: 12,
            shadowColor: 'rgba(37, 99, 235, 0.25)',
          },
        },
      },
    ],
    animationDuration: 600,
    animationEasing: 'cubicOut',
  })
}

// ============================================================
// 趋势图：近12个月新签/到期合同数（双折线）
// ============================================================
function initTrendChart() {
  const dom = document.getElementById('chart-trend')
  if (!dom) return

  trendChart?.dispose()
  trendChart = echarts.init(dom)

  const primary = '#2563EB'
  const danger = '#ef4444'

  trendChart.setOption({
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
      data: ['新签', '到期'],
      bottom: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 20,
      textStyle: { fontSize: 12, color: '#3F5573' },
    },
    grid: { left: '2%', right: '3%', bottom: '14%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: stats.value.contract_trend.map((r) => r.month.slice(0, 7)),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '个',
      minInterval: 1,
      nameTextStyle: { color: '#94a3b8', fontSize: 11, padding: [0, 28, 0, 0] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    },
    series: [
      {
        name: '新签',
        type: 'line',
        data: stats.value.contract_trend.map((r) => r.created_count),
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: false,
        lineStyle: { color: primary, width: 3 },
        itemStyle: { color: primary, borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'series', itemStyle: { borderWidth: 2 } },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.18)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
          ]),
        },
      },
      {
        name: '到期',
        type: 'line',
        data: stats.value.contract_trend.map((r) => r.expired_count),
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: false,
        lineStyle: { color: danger, width: 3 },
        itemStyle: { color: danger, borderColor: '#fff', borderWidth: 2 },
        emphasis: { focus: 'series', itemStyle: { borderWidth: 2 } },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(239, 68, 68, 0.12)' },
            { offset: 1, color: 'rgba(239, 68, 68, 0.02)' },
          ]),
        },
      },
    ],
    animationDuration: 600,
    animationEasing: 'cubicOut',
  })
}

// ============================================================
// 窗口缩放自适应
// ============================================================
function handleResize() {
  customerChart?.resize()
  modelChart?.resize()
  trendChart?.resize()
}

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  window.addEventListener('resize', handleResize)
  fetchStats()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  customerChart?.dispose()
  modelChart?.dispose()
  trendChart?.dispose()
})
</script>
