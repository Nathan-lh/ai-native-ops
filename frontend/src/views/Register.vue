<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const router = useRouter()

const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
  realName: '',
  phone: '',
  role: 'STUDENT',
  inviteCode: ''
})

const loading = ref(false)

// 管理员和维修工需要邀请码
const needInvite = computed(() => ['ADMIN', 'REPAIRER'].includes(form.value.role))

const roleOptions = [
  { label: '学生', value: 'STUDENT' },
  { label: '老师', value: 'TEACHER' },
  { label: '维修工（需邀请码）', value: 'REPAIRER' },
  { label: '管理员（需邀请码）', value: 'ADMIN' }
]

async function handleRegister() {
  if (!form.value.username || form.value.username.length < 3) {
    ElMessage.warning('用户名至少 3 位')
    return
  }
  if (!form.value.password || form.value.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (form.value.password !== form.value.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (!form.value.realName) {
    ElMessage.warning('请填写真实姓名')
    return
  }
  if (needInvite.value && !form.value.inviteCode) {
    ElMessage.warning('该角色需要邀请码')
    return
  }

  loading.value = true
  try {
    await request.post('/api/auth/register', {
      username: form.value.username,
      password: form.value.password,
      realName: form.value.realName,
      phone: form.value.phone,
      role: form.value.role,
      inviteCode: form.value.inviteCode
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    const msg = e.response?.data?.message
    if (msg) ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <el-card class="register-card">
      <div class="title">注册账号</div>
      <div class="subtitle">AI-Native 设备智能运维平台</div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="至少 3 位" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" size="large" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" size="large" show-password />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="form.realName" placeholder="例如：张三" size="large" />
        </el-form-item>
        <el-form-item label="手机号（选填）">
          <el-input v-model="form.phone" placeholder="选填" size="large" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%" size="large">
            <el-option v-for="o in roleOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="needInvite" label="邀请码">
          <el-input
            v-model="form.inviteCode"
            placeholder="请联系管理员获取邀请码"
            size="large"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%; margin-top: 12px"
          @click="handleRegister"
        >
          注册
        </el-button>
      </el-form>

      <div class="login-link">
        已有账号？<router-link to="/login">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.register-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2c3e50 100%);
}
.register-card {
  width: 460px;
  padding: 20px;
  max-height: 90vh;
  overflow-y: auto;
}
.title {
  font-size: 20px;
  font-weight: bold;
  text-align: center;
}
.subtitle {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
  margin-bottom: 20px;
}
.invite-hint {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
}
.invite-hint code {
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 3px;
  color: #e6a23c;
}
.login-link {
  margin-top: 16px;
  text-align: center;
  color: #606266;
  font-size: 13px;
}
</style>