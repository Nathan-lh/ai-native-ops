// src/api/request.js
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import router from '../router'

const request = axios.create({
  baseURL: 'http://localhost:8080',
  timeout: 15000
})

request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''

    // 登录/注册接口的 401/400 直接抛给调用方（让页面显示具体错误）
    const isAuthApi = url.includes('/api/auth/login') || url.includes('/api/auth/register')
    if (isAuthApi) {
      return Promise.reject(error)
    }

    if (status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
    } else if (status === 403) {
      ElMessage.error(error.response?.data?.message || '没有权限')
    } else if (status >= 500) {
      ElMessage.error('服务器错误')
    } else {
      ElMessage.error(error.response?.data?.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default request