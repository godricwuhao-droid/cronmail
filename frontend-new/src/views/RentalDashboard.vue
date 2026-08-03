<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">租赁概览</h1>
      <p class="page-subtitle">设备租赁数据统计</p>
    </div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">租赁总数</span>
          <div class="stat-card__icon" style="background: var(--color-primary-lightest); color: var(--color-primary);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.total ?? 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">活跃租赁</span>
          <div class="stat-card__icon" style="background: var(--color-success-lightest); color: var(--color-success);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.active ?? 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">已到期</span>
          <div class="stat-card__icon" style="background: var(--color-warning-lightest); color: var(--color-warning);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.expired ?? 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__header">
          <span class="stat-card__title">已归还</span>
          <div class="stat-card__icon" style="background: var(--color-info-lightest); color: var(--color-info);">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
          </div>
        </div>
        <div class="stat-card__value">{{ stats.returned ?? 0 }}</div>
      </div>
    </div>
    <div class="content-card">
      <h3 class="content-card__title">租赁趋势</h3>
      <div ref="chartRef" class="chart"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { getRentalDashboard } from '@/api/dashboard'

const stats = ref<any>({})
const chartRef = ref<HTMLElement>()

onMounted(async () => {
  try { stats.value = await getRentalDashboard() } catch { /* ignore */ }
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 20, bottom: 30, left: 50 },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月'], axisLine: { lineStyle: { color: '#E5E7EB' } }, axisLabel: { color: '#86909C', fontSize: 12 } },
    yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#F2F3F5' } }, axisLabel: { color: '#86909C', fontSize: 12 } },
    series: [{ data: [5, 8, 12, 7, 10, 15], type: 'bar', barWidth: '40%', itemStyle: { color: '#1677FF', borderRadius: [4, 4, 0, 0] } }],
  })
  window.addEventListener('resize', () => chart.resize())
})
</script>

<style scoped lang="scss">
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--spacing-xl); margin-bottom: var(--spacing-xl); }
.content-card { background: var(--color-bg-card); border-radius: var(--radius-lg); border: 1px solid var(--color-border-light); box-shadow: var(--shadow-sm); padding: var(--spacing-xl); }
.content-card__title { font-size: var(--font-size-md); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin-bottom: var(--spacing-lg); }
.chart { width: 100%; height: 300px; }
@media (max-width: 1280px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .stats-grid { grid-template-columns: 1fr; } }
</style>