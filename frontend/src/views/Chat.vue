<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const AGENT_URL = 'http://localhost:8000'
const userStore = useUserStore()

const sessionId = ref('')
const input = ref('')
const sending = ref(false)
const messages = ref([])
const scrollBox = ref(null)

const quickQuestions = [
  '现在有多少台故障设备？',
  '有一台空调温度持续升高，可能是什么原因？',
  '电机振动越来越大，帮我分析一下',
  '列出所有配电柜'
]

// 生成带用户名前缀的 key，实现"按账号隔离"
function keyOf(name) {
  const uid = userStore.userInfo.username || 'anonymous'
  return `chat_${name}_${uid}`
}

// ============ 显式保存 ============
function saveMessages() {
  if (!sessionId.value) return
  const cleaned = messages.value
    .filter((m) => {
      if (m.role === 'user') return true
      const hasContent = m.content && m.content.trim()
      const hasTools = m.toolCalls && m.toolCalls.length > 0
      return hasContent || hasTools
    })
    .map((m) => JSON.parse(JSON.stringify(m)))

  localStorage.setItem(keyOf('messages') + '_' + sessionId.value, JSON.stringify(cleaned))
  console.log('[Chat] 已保存消息数：', cleaned.length)
}

let saveTimer = null
function scheduleSave() {
  if (saveTimer) return
  saveTimer = setTimeout(() => {
    saveMessages()
    saveTimer = null
  }, 500)
}

onMounted(() => {
  // 1. 恢复或新建 session_id（按用户名隔离）
  let sid = localStorage.getItem(keyOf('session_id'))
  if (!sid) {
    sid = 'web_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(keyOf('session_id'), sid)
  }
  sessionId.value = sid

  // 2. 从 localStorage 恢复聊天记录
  const saved = localStorage.getItem(keyOf('messages') + '_' + sid)
  if (saved) {
    try {
      messages.value = JSON.parse(saved)
      scrollToBottom()
      return
    } catch (e) {
      console.warn('恢复聊天记录失败', e)
    }
  }

  // 3. 欢迎消息
  messages.value.push({
    role: 'assistant',
    content: '你好，我是 AI 设备运维助手。可以帮你查询设备状态、诊断故障、生成维修工单。请问有什么可以帮你？',
    toolCalls: [],
    toolResults: []
  })
})

function scrollToBottom() {
  nextTick(() => {
    if (scrollBox.value) {
      scrollBox.value.scrollTop = scrollBox.value.scrollHeight
    }
  })
}

function newSession() {
  if (sessionId.value) {
    localStorage.removeItem(keyOf('messages') + '_' + sessionId.value)
  }
  const sid = 'web_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
  localStorage.setItem(keyOf('session_id'), sid)
  sessionId.value = sid
  messages.value = [{
    role: 'assistant',
    content: '已开启新会话，请问有什么可以帮你？',
    toolCalls: [],
    toolResults: []
  }]
}

async function sendMessage(text) {
  const content = (text || input.value).trim()
  if (!content || sending.value) return

  messages.value.push({ role: 'user', content })
  saveMessages()
  input.value = ''

  const aiMsg = {
    role: 'assistant',
    content: '',
    thinking: false,
    toolCalls: [],
    toolResults: []
  }
  messages.value.push(aiMsg)
  scrollToBottom()

  sending.value = true
  try {
    const resp = await fetch(`${AGENT_URL}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: content })
    })

    if (!resp.ok) throw new Error('HTTP ' + resp.status)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop()
      for (const chunk of chunks) {
        handleEvent(chunk, aiMsg)
      }
    }
  } catch (e) {
    ElMessage.error('请求失败：' + e.message)
    aiMsg.content = aiMsg.content || '（请求失败，请检查 Agent 服务是否启动）'
  } finally {
    sending.value = false
    saveMessages()
    scrollToBottom()
  }
}

function handleEvent(raw, aiMsg) {
  const lines = raw.split('\n')
  let eventType = 'message'
  let dataStr = ''
  for (const line of lines) {
    if (line.startsWith('event:')) eventType = line.slice(6).trim()
    else if (line.startsWith('data:')) dataStr = line.slice(5).trim()
  }
  if (!dataStr) return

  let data
  try { data = JSON.parse(dataStr) } catch { return }

  if (eventType === 'thinking') {
    aiMsg.thinking = true
  } else if (eventType === 'tool_call') {
    aiMsg.toolCalls.push({ name: data.name, args: data.args })
    scheduleSave()
    scrollToBottom()
  } else if (eventType === 'tool_result') {
    aiMsg.toolResults.push(data.preview)
  } else if (eventType === 'token') {
    aiMsg.thinking = false
    aiMsg.content += data.text
    scheduleSave()
    scrollToBottom()
  } else if (eventType === 'done') {
    if (!aiMsg.content && data.answer) aiMsg.content = data.answer
    if (data.tool_calls && aiMsg.toolCalls.length === 0) aiMsg.toolCalls = data.tool_calls
    aiMsg.thinking = false
    saveMessages()
    scrollToBottom()
  } else if (eventType === 'error') {
    ElMessage.error('Agent 错误：' + data.message)
    aiMsg.content = aiMsg.content || ('（错误：' + data.message + '）')
    saveMessages()
  }
}

function getToolLabel(name) {
  const map = {
    list_devices: '查询设备列表',
    get_device_status: '查询设备状态',
    get_device_telemetry: '查询遥测数据',
    get_device_summary: '设备统计汇总',
    search_manual: '检索知识库手册'
  }
  return map[name] || name
}
</script>

<template>
  <div class="chat-page">
    <div class="chat-card">
      <div class="chat-header">
        <div class="title">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 设备运维助手</span>
          <el-tag size="small" type="info" style="margin-left:8px">{{ userStore.userInfo.username }}</el-tag>
        </div>
        <div class="actions">
          <span class="sid">会话：{{ sessionId.slice(-8) }}</span>
          <el-button size="small" @click="newSession">新会话</el-button>
        </div>
      </div>

      <div ref="scrollBox" class="chat-body">
        <div v-for="(msg, i) in messages" :key="i" :class="['msg-row', msg.role]">
          <div v-if="msg.role === 'assistant'" class="avatar ai">AI</div>
          <div class="bubble-wrap">
            <div v-if="msg.toolCalls && msg.toolCalls.length" class="tool-calls">
              <div v-for="(tc, j) in msg.toolCalls" :key="j" class="tool-call">
                <el-icon><Tools /></el-icon>
                <span class="tool-name">{{ getToolLabel(tc.name) }}</span>
                <span class="tool-args">{{ JSON.stringify(tc.args) }}</span>
              </div>
            </div>
            <div v-if="msg.thinking" class="thinking">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>AI 正在思考...</span>
            </div>
            <div v-if="msg.content" class="bubble">{{ msg.content }}</div>
            <el-collapse v-if="msg.toolResults && msg.toolResults.length" class="tool-results">
              <el-collapse-item title="查看工具返回详情">
                <div v-for="(tr, k) in msg.toolResults" :key="k" class="tool-result-item">
                  {{ tr }}
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
          <div v-if="msg.role === 'user'" class="avatar user">我</div>
        </div>
      </div>

      <div class="quick-bar">
        <el-tag v-for="q in quickQuestions" :key="q" class="quick-tag" @click="sendMessage(q)">
          {{ q }}
        </el-tag>
      </div>

      <div class="chat-input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
          @keydown.enter.exact.prevent="sendMessage()"
        />
        <el-button type="primary" :loading="sending" @click="sendMessage()">发送</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 样式不变，照旧 */
.chat-page { height: calc(100vh - 60px - 40px); padding: 20px; }
.chat-card { height: 100%; background: #fff; border-radius: 8px; display: flex; flex-direction: column; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; }
.chat-header { padding: 12px 20px; border-bottom: 1px solid #e6e6e6; display: flex; justify-content: space-between; align-items: center; }
.chat-header .title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 16px; }
.chat-header .actions { display: flex; align-items: center; gap: 12px; }
.sid { font-size: 12px; color: #909399; }
.chat-body { flex: 1; overflow-y: auto; padding: 20px; background: #f7f8fa; }
.msg-row { display: flex; margin-bottom: 20px; align-items: flex-start; }
.msg-row.user { justify-content: flex-end; }
.avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #fff; flex-shrink: 0; }
.avatar.ai { background: #409eff; margin-right: 10px; }
.avatar.user { background: #67c23a; margin-left: 10px; }
.bubble-wrap { max-width: 70%; display: flex; flex-direction: column; gap: 6px; }
.bubble { background: #fff; padding: 10px 14px; border-radius: 8px; white-space: pre-wrap; word-break: break-word; line-height: 1.6; color: #303133; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.msg-row.user .bubble { background: #409eff; color: #fff; }
.tool-calls { display: flex; flex-direction: column; gap: 4px; }
.tool-call { background: #ecf5ff; color: #409eff; padding: 6px 10px; border-radius: 6px; font-size: 12px; display: flex; align-items: center; gap: 6px; }
.tool-name { font-weight: 600; }
.tool-args { color: #606266; font-family: Consolas, monospace; }
.thinking { display: flex; align-items: center; gap: 6px; color: #909399; font-size: 13px; padding: 6px 0; }
.tool-results { margin-top: 4px; }
.tool-result-item { font-family: Consolas, monospace; font-size: 12px; white-space: pre-wrap; color: #606266; padding: 4px 0; }
.quick-bar { padding: 8px 20px; display: flex; gap: 8px; flex-wrap: wrap; border-top: 1px solid #f0f0f0; }
.quick-tag { cursor: pointer; }
.quick-tag:hover { background: #409eff; color: #fff; }
.chat-input { padding: 12px 20px 16px; display: flex; gap: 10px; border-top: 1px solid #e6e6e6; }
.chat-input :deep(.el-textarea) { flex: 1; }
</style>