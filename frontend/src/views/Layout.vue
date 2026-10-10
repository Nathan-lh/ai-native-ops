<script setup>
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const menus = [
  { path: '/dashboard', title: '首页', icon: 'HomeFilled' },
  { path: '/devices', title: '设备管理', icon: 'Monitor' },
  { path: '/orders', title: '工单管理', icon: 'Tickets' },
  { path: '/chat', title: 'AI 诊断助手', icon: 'ChatDotRound' }
]

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta.title || '')

function handleLogout() {
  ElMessageBox.confirm('确定退出登录吗？', '提示', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
  }).catch(() => {})
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">AI 智能运维</div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
        background-color="#001529"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="title">{{ pageTitle }}</div>
        <div class="user">
          <span class="username">{{ userStore.userInfo.realName || userStore.userInfo.username || '未登录' }}</span>
          <el-button link type="primary" @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background-color: #001529;
  overflow: hidden;
}
.logo {
  height: 60px;
  line-height: 60px;
  color: #fff;
  text-align: center;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #1f2d3d;
}
.menu {
  border-right: none;
}
.header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-size: 16px;
  font-weight: 500;
}
.user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: #606266;
}
.main {
  background: #f0f2f5;
}
</style>