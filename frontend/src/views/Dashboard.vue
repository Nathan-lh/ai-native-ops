<script setup>
import { useUserStore } from '../stores/user'
const userStore = useUserStore()
</script>

<template>
  <div class="dashboard">
    <el-card>
      <h2>欢迎回来，{{ userStore.userInfo.realName || userStore.userInfo.username }}</h2>
      <p>这是 AI-Native 设备智能运维平台的首页。</p>
      <p>左侧菜单可以进入设备管理、工单管理、AI 诊断助手。</p>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
}
</style>