import { computed, reactive } from 'vue'
import api from './api'
import type { User } from './types'

function storedUser(): User | null {
  const stored = localStorage.getItem('wms_user')
  if (!stored) return null
  try {
    return JSON.parse(stored) as User
  } catch {
    localStorage.removeItem('wms_user')
    localStorage.removeItem('wms_token')
    return null
  }
}

export const auth = reactive<{ user: User | null; ready: boolean }>({
  user: storedUser(),
  ready: false,
})

export const isLoggedIn = computed(() => Boolean(localStorage.getItem('wms_token') && auth.user))

export function has(permission?: string): boolean {
  if (!permission) return true
  return Boolean(auth.user?.is_superadmin || auth.user?.permissions.includes(permission))
}

export async function loadMe() {
  if (!localStorage.getItem('wms_token')) {
    auth.user = null
    auth.ready = true
    return null
  }
  try {
    const { data } = await api.get<User>('/auth/me')
    auth.user = data
    localStorage.setItem('wms_user', JSON.stringify(data))
    return data
  } catch (error) {
    logout()
    throw error
  } finally {
    auth.ready = true
  }
}

export function setSession(token: string, user: User) {
  localStorage.setItem('wms_token', token)
  localStorage.setItem('wms_user', JSON.stringify(user))
  auth.user = user
  auth.ready = true
}

export function logout() {
  localStorage.removeItem('wms_token')
  localStorage.removeItem('wms_user')
  auth.user = null
  auth.ready = true
}
