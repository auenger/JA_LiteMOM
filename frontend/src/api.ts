import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || '/api', timeout: 15000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('wms_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('wms_token')
      localStorage.removeItem('wms_user')
      if (location.pathname !== '/login') location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join('；')
    return detail || error.message
  }
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export default api

