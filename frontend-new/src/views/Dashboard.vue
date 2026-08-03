<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">运营概览</h1>
      <p class="page-subtitle">系统运行数据总览</p>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">合同总数</span>
          <div class="stat-card__icon" style="background: var(--color-primary-lightest); color: var(--color-primary);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.total_contracts ?? 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">活跃合同</span>
          <div class="stat-card__icon" style="background: var(--color-success-lightest); color: var(--color-success);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.active_contracts ?? 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">客户总数</span>
          <div class="stat-card__icon" style="background: var(--color-warning-lightest); color: var(--color-warning);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.total_customers ?? 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">今日发送</span>
          <div class="stat-card__icon" style="background: var(--color-info-lightest); color: var(--color-info);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.sent_today ?? 0 }}</div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid">
      <div class="content-card">
        <h3 class="content-card__title">发送趋势</h3>
        <div ref="trendChartRef" class="chart"></div>
      </div>
      <div class="content-card">
        <h3 class="content-card__title">合同分布</h3>
        <div ref="pieChartRef" class="chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats } from '@/api/dashboard'

const stats = ref<any>({})
const trendChartRef = ref<HTMLElement>()
const pieChartRef = ref<HTMLElement>()

onMounted(async () => {
  try {
    stats.value = await getDashboardStats()
  } catch { /* ignore */ }

  initTrendChart()
  initPieChart()
})

function initTrendChart() {
  if (!trendChartRef.value) return
  const chart = echarts.init(trendChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLine: { lineStyle: { color: '#E5E7EB' } },
      axisLabel: { color: '#86909C', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F2F3F5' } },
      axisLabel: { color: '#86909C', fontSize: 12 },
    },
    series: [{
      data: [120, 200, 150, 80, 70, 110, 130],
      type: 'line',
      smooth: true,
      lineStyle: { color: '#1677FF', width: 3 },
      itemStyle: { color: '#1677FF' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(22, 119, 255, 0.2)' },
          { offset: 1, color: 'rgba(22, 119, 255, 0)' },
        ]),
      },
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

function initPieChart() {
  if (!pieChartRef.value) return
  const chart = echarts.init(pieChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#86909C', fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: 335, name: '算力租赁', itemStyle: { color: '#1677FF' } },
        { value: 234, name: '卫星数据', itemStyle: { color: '#52C41A' } },
        { value: 185, name: '算力服务', itemStyle: { color: '#FAAD14' } },
      ],
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}
</script>

<style scoped lang="scss">
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-xl);
}

.content-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-xl);

  &__title {
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-lg);
  }
}

.chart {
  width: 100%;
  height: 300px;
}

@media (max-width: 1280px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: 1fr; }
}
</style>