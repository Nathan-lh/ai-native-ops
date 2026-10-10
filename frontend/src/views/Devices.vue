<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '../api/request'

// ==================== 列表状态 ====================
const loading = ref(false)
const devices = ref([])
const total = ref(0)
const query = ref({
  status: '',
  deviceType: '',
  keyword: ''
})

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '正常', value: 'NORMAL' },
  { label: '预警', value: 'WARNING' },
  { label: '故障', value: 'FAULT' }
]

const typeOptions = [
  { label: '全部类型', value: '' },
  { label: '空调', value: '空调' },
  { label: '电机', value: '电机' },
  { label: '配电柜', value: '配电柜' },
  { label: '温湿度传感器', value: '温湿度传感器' }
]

function statusTagType(status) {
  if (status === 'NORMAL') return 'success'
  if (status === 'WARNING') return 'warning'
  if (status === 'FAULT') return 'danger'
  return 'info'
}

function statusLabel(status) {
  const map = { NORMAL: '正常', WARNING: '预警', FAULT: '故障' }
  return map[status] || status
}

// ==================== 加载设备列表 ====================
async function loadDevices() {
  loading.value = true
  try {
    const params = { limit: 500 }
    if (query.value.status) params.status = query.value.status
    if (query.value.deviceType) params.deviceType = query.value.deviceType
    if (query.value.keyword) params.keyword = query.value.keyword
    const res = await request.get('/api/agent/tools/devices', { params })
    devices.value = res.devices || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.value = { status: '', deviceType: '', keyword: '' }
  loadDevices()
}

// ==================== 详情抽屉 ====================
const drawerVisible = ref(false)
const currentDevice = ref(null)
const currentTelemetry = ref(null)
const telemetryList = ref([])
const chartRef = ref(null)
let chartInstance = null

async function openDetail(row) {
  currentDevice.value = row
  drawerVisible.value = true

  // 并行拉详情 + 遥测
  try {
    const [statusRes, telemetryRes] = await Promise.all([
      request.get('/api/agent/tools/device-status', { params: { deviceId: row.id } }),
      request.get('/api/agent/tools/telemetry', { params: { deviceId: row.id, limit: 100 } })
    ])
    currentTelemetry.value = statusRes.latestTelemetry || null
    // 后端返回按 ts 倒序，画图要正序
    telemetryList.value = (telemetryRes.telemetryList || []).slice().reverse()
    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error('加载详情失败')
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  const times = telemetryList.value.map((t) => t.ts?.substring(11, 19) || '')
  const temperature = telemetryList.value.map((t) => t.temperature)
  const humidity = telemetryList.value.map((t) => t.humidity)
  const current = telemetryList.value.map((t) => t.current)
  const voltage = telemetryList.value.map((t) => t.voltage)
  const vibration = telemetryList.value.map((t) => t.vibration)

  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['温度', '湿度', '电流', '电压', '振动'], top: 0 },
    grid: { left: 40, right: 20, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: { type: 'value' },
    series: [
      { name: '温度', type: 'line', smooth: true, data: temperature, itemStyle: { color: '#f56c6c' } },
      { name: '湿度', type: 'line', smooth: true, data: humidity, itemStyle: { color: '#409eff' } },
      { name: '电流', type: 'line', smooth: true, data: current, itemStyle: { color: '#e6a23c' } },
      { name: '电压', type: 'line', smooth: true, data: voltage, itemStyle: { color: '#67c23a' } },
      { name: '振动', type: 'line', smooth: true, data: vibration, itemStyle: { color: '#909399' } }
    ]
  })
}

function closeDrawer() {
  drawerVisible.value = false
  currentDevice.value = null
  currentTelemetry.value = null
  telemetryList.value = []
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

function onResize() {
  if (chartInstance) chartInstance.resize()
}

onMounted(() => {
  loadDevices()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chartInstance) chartInstance.dispose()
})
</script>

<template>
  <div class="devices-page">
    <!-- 过滤栏 -->
    <el-card class="filter-card">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="状态" style="width: 140px" @change="loadDevices">
          <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="query.deviceType" placeholder="类型" style="width: 180px" @change="loadDevices">
          <el-option v-for="o in typeOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input
          v-model="query.keyword"
          placeholder="按设备名或编号搜索"
          style="width: 260px"
          clearable
          @keyup.enter="loadDevices"
        />
        <el-button type="primary" @click="loadDevices">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <span class="total-hint">共 {{ total }} 台设备</span>
      </div>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card">
      <el-table
        :data="devices"
        v-loading="loading"
        stripe
        @row-click="openDetail"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="deviceName" label="设备名称" min-width="160" />
        <el-table-column prop="deviceCode" label="资产编号" min-width="160" />
        <el-table-column prop="deviceType" label="类型" width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="currentDevice ? currentDevice.deviceName : '设备详情'"
      size="70%"
      @close="closeDrawer"
    >
      <div v-if="currentDevice" class="detail-body">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="ID">{{ currentDevice.id }}</el-descriptions-item>
          <el-descriptions-item label="资产编号">{{ currentDevice.deviceCode }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentDevice.deviceType }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(currentDevice.status)">
              {{ statusLabel(currentDevice.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 最新遥测 -->
        <div class="section-title">最新遥测</div>
        <el-descriptions v-if="currentTelemetry" :column="5" border size="small">
          <el-descriptions-item label="温度">{{ currentTelemetry.temperature }} ℃</el-descriptions-item>
          <el-descriptions-item label="湿度">{{ currentTelemetry.humidity }} %</el-descriptions-item>
          <el-descriptions-item label="电流">{{ currentTelemetry.current }} A</el-descriptions-item>
          <el-descriptions-item label="电压">{{ currentTelemetry.voltage }} V</el-descriptions-item>
          <el-descriptions-item label="振动">{{ currentTelemetry.vibration }}</el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="暂无遥测数据" :image-size="60" />

        <!-- 曲线 -->
        <div class="section-title">遥测曲线（最近 {{ telemetryList.length }} 条）</div>
        <div ref="chartRef" class="chart-box"></div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.devices-page {
  padding: 20px;
}
.filter-card {
  margin-bottom: 16px;
}
.filter-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.total-hint {
  margin-left: auto;
  color: #909399;
  font-size: 13px;
}
.table-card {
  min-height: 400px;
}
:deep(.el-table__row) {
  cursor: pointer;
}
.detail-body {
  padding: 0 8px;
}
.section-title {
  margin: 20px 0 10px;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.chart-box {
  width: 100%;
  height: 380px;
}
</style>