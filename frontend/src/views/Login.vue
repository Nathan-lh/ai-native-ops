<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import request from '../api/request'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = ref({ username: 'admin', password: '123456' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await request.post('/api/auth/login', {
      username: form.value.username,
      password: form.value.password
    })
    userStore.setLogin(res.token, {
      username: res.username,
      realName: res.realName,
      role: res.role
    })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/dashboard'
    router.push(redirect)
  } catch (e) {
    // 登录接口的 401 不走全局拦截器，这里手动显示后端返回的具体错误
    const msg = e.response?.data?.message
    if (msg) ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <div class="title">AI-Native 设备智能运维平台</div>
      <div class="subtitle">Java + Agent 双引擎诊断</div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="'User'" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="'Lock'"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" style="width: 100%; margin-top: 12px" @click="handleLogin">
          登录
        </el-button>
      </el-form>

      <div class="register-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>

      <div class="hint">
        测试账号：admin / 123456 · repairer / 123456 · student / 123456
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2c3e50 100%);
}
.login-card { width: 420px; padding: 20px; }
.title { font-size: 20px; font-weight: bold; text-align: center; color: #303133; }
.subtitle { text-align: center; color: #909399; font-size: 13px; margin-top: 8px; margin-bottom: 24px; }
.register-link { margin-top: 16px; text-align: center; color: #606266; font-size: 13px; }
.hint { margin-top: 16px; text-align: center; color: #909399; font-size: 12px; }
</style>