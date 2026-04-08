import { ref } from 'vue'
import type { User } from '@/types'
import { useApi } from './useApi'

const isAuthenticated = ref(!!localStorage.getItem('token'))
const user = ref<User | null>(null)

const savedUser = localStorage.getItem('user')
if (savedUser) {
  try { user.value = JSON.parse(savedUser) } catch {}
}

export function useAuth() {
  const api = useApi()

  async function login(email: string, password: string): Promise<boolean> {
    try {
      const data: any = await api.post('/auth/login', { email, password })
      api.setToken(data.access_token)
      if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
      user.value = { id: data.user_id, name: data.name, email: data.email, role: data.role, organizationId: '' }
      localStorage.setItem('user', JSON.stringify(user.value))
      isAuthenticated.value = true
      return true
    } catch {
      return false
    }
  }

  function logout() {
    api.clearToken()
    localStorage.removeItem('user')
    localStorage.removeItem('refresh_token')
    isAuthenticated.value = false
    user.value = null
  }

  async function register(name: string, email: string, password: string): Promise<boolean> {
    try {
      const data: any = await api.post('/auth/register', { email, password, name })
      api.setToken(data.access_token)
      if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
      user.value = { id: data.user_id, name: data.name, email: data.email, role: data.role, organizationId: '' }
      localStorage.setItem('user', JSON.stringify(user.value))
      isAuthenticated.value = true
      return true
    } catch {
      return false
    }
  }

  return { isAuthenticated, user, login, logout, register }
}
