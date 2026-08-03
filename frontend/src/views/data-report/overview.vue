<template>
  <div class="page-container overview-page" v-loading="loading">
    <div class="page-title">
      <el-icon :size="22" style="color: #409EFF; vertical-align: -3px;"><DataAnalysis /></el-icon>
      <span style="margin-left: 8px;">运营概览</span>
    </div>

    <!-- 第一行：柱状图 + 扇形图 -->
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="14">
        <el-card shadow="never">
          <div id="chart-customer" style="width: 100%; height: 360px;"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <div id="chart-model" style="width: 100%; height: 360px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：趋势图 -->
    <el-row>
      <el-col :span="24">
        <el-card shadow="never">
          <div id="chart-trend" style="width: 100%; height: 320px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.overview-page .el-card {
  border: 1px solid #ebeef5;
}

.page-title {
  margin-bottom: 24px;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
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

  // 颜色
  const colors = [
    '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399',
    '#36b4c1', '#8e5ce5', '#f0a732',
  ]

  customerChart.setOption({
    title: {
      text: '客户租用设备排行',
      left: 'center',
      textStyle: { fontSize: 14 },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: { data: models, bottom: 0 },
    color: colors,
    xAxis: {
      type: 'category',
      data: data.map((c) => c.customer_name),
      axisLabel: { rotate: 30, fontSize: 11 },
    },
    yAxis: { type: 'value', name: '台' },
    series: models.map((modelName) => ({
      name: modelName,
      type: 'bar',
      stack: 'total',
      emphasis: { focus: 'series' },
      data: data.map((c) => {
        const found = c.models.find((m) => m.machine_model === modelName)
        return found ? found.count : 0
      }),
    })),
    grid: { left: '3%', right: '4%', bottom: '20%', top: '12%', containLabel: true },
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

  modelChart.setOption({
    title: {
      text: '机器型号分布',
      left: 'center',
      textStyle: { fontSize: 14 },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 台 ({d}%)',
    },
    legend: { bottom: 10 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        data: stats.value.rental_by_model.map((r) => ({
          name: r.machine_model,
          value: r.count,
        })),
        label: { formatter: '{b}\n{d}%' },
      },
    ],
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

  trendChart.setOption({
    title: {
      text: '合同趋势（近12个月）',
      left: 'center',
      textStyle: { fontSize: 14 },
    },
    tooltip: { trigger: 'axis' },
    legend: { data: ['新签', '到期'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: stats.value.contract_trend.map((r) => r.month.slice(0, 7)),
    },
    yAxis: { type: 'value', name: '个' },
    series: [
      {
        name: '新签',
        type: 'line',
        data: stats.value.contract_trend.map((r) => r.created_count),
        smooth: true,
        itemStyle: { color: '#67c23a' },
      },
      {
        name: '到期',
        type: 'line',
        data: stats.value.contract_trend.map((r) => r.expired_count),
        smooth: true,
        itemStyle: { color: '#f56c6c' },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
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
