// src/stores/user.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref(sessionStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(sessionStorage.getItem('userInfo') || '{}'))

  const isLogin = computed(() => !!token.value)
  const role = computed(() => userInfo.value.role || '')

  // 清掉所有和聊天相关的 sessionStorage（防止跨账号共享）
  function clearChatData() {
    const keys = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (k && (k.startsWith('chat_messages_') || k === 'chat_session_id')) {
        keys.push(k)
      }
    }
    keys.forEach((k) => sessionStorage.removeItem(k))
    console.log('[User] 已清理聊天数据', keys.length, '条')
  }

  function setLogin(newToken, info) {
    // 登录前先清掉上一位用户的聊天数据
    clearChatData()
    token.value = newToken
    userInfo.value = info
    sessionStorage.setItem('token', newToken)
    sessionStorage.setItem('userInfo', JSON.stringify(info))
  }

  function logout() {
    // 登出也清掉聊天数据
    clearChatData()
    token.value = ''
    userInfo.value = {}
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('userInfo')
  }

  return { token, userInfo, isLogin, role, setLogin, logout }
})