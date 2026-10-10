// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'devices',
        name: 'Devices',
        component: () => import('../views/Devices.vue'),
        meta: { title: '设备管理' }
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('../views/Orders.vue'),
        meta: { title: '工单管理' }
      },
      {
        path: '/register',
        name: 'Register',
        component: () => import('../views/Register.vue'),
        meta: { public: true, title: '注册' }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/Chat.vue'),
        meta: { title: 'AI 诊断助手' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { public: true, title: '404' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫：未登录跳登录
router.beforeEach((to) => {
  const token = sessionStorage.getItem('token')
  if (to.meta.public) {
    return true
  }
  if (!token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router