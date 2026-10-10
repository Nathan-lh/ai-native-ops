<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const loading = ref(false)
const orders = ref([])
const total = ref(0)
const query = ref({ status: '' })

// 角色判断
const isAdmin = computed(() => userStore.role === 'ADMIN')
const isRepairer = computed(() => userStore.role === 'REPAIRER')
const canCreate = computed(() => ['STUDENT', 'TEACHER'].includes(userStore.role))

// ==================== 自动刷新 ====================
const autoRefresh = ref(true)
const lastUpdateTime = ref('')
let pollTimer = null
const POLL_INTERVAL = 5000

function startPolling() {
  stopPolling()
  if (!autoRefresh.value) return
  pollTimer = setInterval(() => {
    loadOrders(true)
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(autoRefresh, (val) => {
  if (val) startPolling()
  else stopPolling()
})

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '待审核', value: 'PENDING_REVIEW' },
  { label: '已派单', value: 'ASSIGNED' },
  { label: '维修中', value: 'REPAIRING' },
  { label: '待验证', value: 'VERIFYING' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已驳回', value: 'REJECTED' }
]

function statusLabel(s) {
  const map = {
    PENDING_REVIEW: '待审核',
    ASSIGNED: '已派单',
    REPAIRING: '维修中',
    VERIFYING: '待验证',
    COMPLETED: '已完成',
    REJECTED: '已驳回'
  }
  return map[s] || s
}

function statusTagType(s) {
  const map = {
    PENDING_REVIEW: 'warning',
    ASSIGNED: 'primary',
    REPAIRING: '',
    VERIFYING: 'warning',
    COMPLETED: 'success',
    REJECTED: 'danger'
  }
  return map[s] || 'info'
}

// ==================== 加载工单 ====================
async function loadOrders(silent = false) {
  if (!silent) loading.value = true
  try {
    const params = {}
    if (query.value.status) params.status = query.value.status
    const res = await request.get('/api/orders', { params })
    orders.value = Array.isArray(res) ? res : (res.orders || [])
    total.value = orders.value.length
    const d = new Date()
    lastUpdateTime.value = d.toLocaleTimeString('zh-CN', { hour12: false })
  } catch (e) {
    if (!silent) ElMessage.error('加载工单失败')
  } finally {
    if (!silent) loading.value = false
  }
}

// ==================== 创建工单 ====================
const createVisible = ref(false)
const createForm = ref({
  deviceId: 1,
  description: '',
  aiDiagnosisSummary: ''
})

function openCreate() {
  createForm.value = { deviceId: 1, description: '', aiDiagnosisSummary: '' }
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.value.deviceId || !createForm.value.description) {
    ElMessage.warning('请填写设备ID和问题描述')
    return
  }
  try {
    await request.post('/api/orders', createForm.value)
    ElMessage.success('工单已创建')
    createVisible.value = false
    loadOrders()
  } catch (e) { /* 拦截器已提示 */ }
}

// ==================== 派单（弹窗 + 下拉选维修工） ====================
const assignVisible = ref(false)
const assignForm = ref({
  orderId: null,
  repairerId: null,
  reviewComment: '同意派单'
})
const repairers = ref([])
const repairersLoading = ref(false)

async function openAssignDialog(row) {
  assignForm.value = {
    orderId: row.id,
    repairerId: null,
    reviewComment: '同意派单'
  }
  assignVisible.value = true

  repairersLoading.value = true
  try {
    const list = await request.get('/api/users/repairers')
    repairers.value = Array.isArray(list) ? list : []
    if (repairers.value.length > 0) {
      assignForm.value.repairerId = repairers.value[0].id
    }
  } catch (e) {
    ElMessage.error('加载维修工列表失败')
  } finally {
    repairersLoading.value = false
  }
}

async function submitAssign() {
  if (!assignForm.value.repairerId) {
    ElMessage.warning('请选择维修工')
    return
  }
  try {
    await request.post(`/api/orders/${assignForm.value.orderId}/assign`, {
      repairerId: assignForm.value.repairerId,
      reviewComment: assignForm.value.reviewComment
    })
    ElMessage.success('派单成功')
    assignVisible.value = false
    loadOrders()
  } catch (e) { /* 拦截器已提示 */ }
}

// ==================== 驳回 ====================
async function handleReject(row) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回理由', '驳回工单', {
      inputValue: '证据不足，驳回',
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消'
    })
    await request.post(`/api/orders/${row.id}/reject`, { reviewComment: value })
    ElMessage.success('已驳回')
    loadOrders()
  } catch (e) {
    if (e !== 'cancel') { /* 拦截器已提示 */ }
  }
}

// ==================== 接单 ====================
async function handleStart(row) {
  try {
    await ElMessageBox.confirm(`确定接单工单 #${row.id} 吗？`, '接单', { type: 'info' })
    await request.post(`/api/orders/${row.id}/start`)
    ElMessage.success('接单成功')
    loadOrders()
  } catch (e) {
    if (e !== 'cancel') { /* 拦截器已提示 */ }
  }
}

// ==================== 完成维修 ====================
async function handleComplete(row) {
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入维修备注和真实原因，格式：清洗冷凝器,冷凝器积尘严重导致散热不良',
      '完成维修',
      {
        inputValue: '清洗冷凝器并更换风扇,冷凝器积尘严重导致散热不良',
        confirmButtonText: '提交',
        cancelButtonText: '取消'
      }
    )
    const [comment, ...rest] = value.split(',')
    const repairComment = comment.trim()
    const repairReason = rest.join(',').trim() || repairComment
    await request.post(`/api/orders/${row.id}/complete`, { repairComment, repairReason })
    ElMessage.success('维修已完成，等待验证')
    loadOrders()
  } catch (e) {
    if (e !== 'cancel') { /* 拦截器已提示 */ }
  }
}

// ==================== 验证通过 ====================
async function handleVerify(row) {
  try {
    await ElMessageBox.confirm(
      `确认工单 #${row.id} 验证通过？验证后设备状态将恢复为 NORMAL。`,
      '验证通过',
      { type: 'warning' }
    )
    await request.post(`/api/orders/${row.id}/verify`)
    ElMessage.success('验证通过，工单已完成')
    loadOrders()
  } catch (e) {
    if (e !== 'cancel') { /* 拦截器已提示 */ }
  }
}

onMounted(() => {
  loadOrders()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="orders-page">
    <el-card class="filter-card">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="工单状态" style="width: 160px" @change="loadOrders()">
          <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-button type="primary" @click="loadOrders()">刷新</el-button>
        <el-button v-if="canCreate" type="success" @click="openCreate">创建工单</el-button>

        <div class="auto-refresh">
          <el-switch v-model="autoRefresh" />
          <span class="refresh-label">自动刷新（5秒）</span>
          <span class="last-update" v-if="lastUpdateTime">最后更新：{{ lastUpdateTime }}</span>
        </div>

        <span class="total-hint">
          共 {{ total }} 条 · {{ userStore.userInfo.username }}（{{ userStore.role }}）
        </span>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table :data="orders" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" fixed="left" />
        <el-table-column
          prop="description"
          label="问题描述"
          min-width="220"
          fixed="left"
          show-overflow-tooltip
        />
        <el-table-column prop="deviceId" label="设备ID" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reporterId" label="报修人" width="80" />
        <el-table-column prop="repairerId" label="维修工" width="80" />
        <el-table-column label="维修原因" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.repairReason">{{ row.repairReason }}</span>
            <span v-else style="color:#c0c4cc">（维修未完成）</span>
          </template>
        </el-table-column>
        <el-table-column label="审核意见" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.reviewComment">{{ row.reviewComment }}</span>
            <span v-else style="color:#c0c4cc">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'PENDING_REVIEW' && isAdmin">
              <el-button size="small" type="primary" @click="openAssignDialog(row)">派单</el-button>
              <el-button size="small" type="danger" @click="handleReject(row)">驳回</el-button>
            </template>
            <template v-else-if="row.status === 'PENDING_REVIEW'">
              <span class="waiting">等待管理员审核</span>
            </template>

            <template v-else-if="row.status === 'ASSIGNED' && isRepairer">
              <el-button size="small" type="primary" @click="handleStart(row)">接单</el-button>
            </template>
            <template v-else-if="row.status === 'ASSIGNED'">
              <span class="waiting">等待维修工接单</span>
            </template>

            <template v-else-if="row.status === 'REPAIRING' && isRepairer">
              <el-button size="small" type="success" @click="handleComplete(row)">完成维修</el-button>
            </template>
            <template v-else-if="row.status === 'REPAIRING'">
              <span class="waiting">维修中</span>
            </template>

            <template v-else-if="row.status === 'VERIFYING' && isAdmin">
              <el-button size="small" type="warning" @click="handleVerify(row)">验证通过</el-button>
            </template>
            <template v-else-if="row.status === 'VERIFYING'">
              <span class="waiting">等待管理员验证</span>
            </template>

            <span v-else class="waiting">无操作</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建工单弹窗 -->
    <el-dialog v-model="createVisible" title="创建工单" width="520px">
      <el-form :model="createForm" label-width="110px">
        <el-form-item label="设备ID">
          <el-input-number v-model="createForm.deviceId" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="问题描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="例如：DEV-空调-001 温度持续升高" />
        </el-form-item>
        <el-form-item label="AI 诊断摘要">
          <el-input v-model="createForm.aiDiagnosisSummary" type="textarea" :rows="3" placeholder="选填，可粘贴 Agent 的诊断结论" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>

    <!-- 派单弹窗 -->
    <el-dialog v-model="assignVisible" title="派单" width="480px">
      <el-form :model="assignForm" label-width="100px">
        <el-form-item label="工单ID">
          <span style="font-weight:600">#{{ assignForm.orderId }}</span>
        </el-form-item>
        <el-form-item label="选择维修工">
          <el-select
            v-model="assignForm.repairerId"
            placeholder="请选择维修工"
            style="width: 100%"
            :loading="repairersLoading"
          >
            <el-option
              v-for="r in repairers"
              :key="r.id"
              :label="`${r.realName} (ID:${r.id})`"
              :value="r.id"
            >
              <div class="repairer-option">
                <span class="repairer-name">{{ r.realName }}</span>
                <span class="repairer-sub">ID:{{ r.id }} · {{ r.username }}</span>
              </div>
            </el-option>
          </el-select>
          <div v-if="repairers.length === 0 && !repairersLoading" class="no-repairer-hint">
            暂无可选维修工，请先注册维修工账号
          </div>
        </el-form-item>
        <el-form-item label="派单意见">
          <el-input
            v-model="assignForm.reviewComment"
            type="textarea"
            :rows="2"
            placeholder="例如：同意派单，请尽快处理"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!assignForm.repairerId" @click="submitAssign">
          确认派单
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.orders-page {
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
.auto-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  border-left: 1px solid #e6e6e6;
  border-right: 1px solid #e6e6e6;
}
.refresh-label {
  font-size: 13px;
  color: #606266;
}
.last-update {
  font-size: 12px;
  color: #909399;
}
.total-hint {
  margin-left: auto;
  color: #909399;
  font-size: 13px;
}
.table-card {
  min-height: 400px;
}
.waiting {
  color: #909399;
  font-size: 12px;
}
.repairer-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.repairer-name {
  font-weight: 600;
}
.repairer-sub {
  color: #909399;
  font-size: 12px;
  font-family: Consolas, monospace;
}
.no-repairer-hint {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 6px;
}
</style>