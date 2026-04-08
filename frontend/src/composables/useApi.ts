const API_BASE = import.meta.env.VITE_API_URL || '/api'

function getToken(): string | null {
  return localStorage.getItem('token')
}

function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false
    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
    return true
  } catch {
    return false
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: authHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  })

  // If 401, try refreshing token once
  if (res.status === 401) {
    const refreshed = await tryRefreshToken()
    if (refreshed) {
      res = await fetch(`${API_BASE}${path}`, {
        method,
        headers: authHeaders(),
        body: body ? JSON.stringify(body) : undefined,
      })
    }
  }

  if (!res.ok) {
    if (res.status === 401) {
      // Token expired and refresh failed — clear auth
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      // Use history API to avoid full page reload
      if (window.location.pathname !== '/auth') {
        window.history.replaceState({}, '', '/auth')
        window.location.reload()
      }
      throw new Error('Session expired')
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

async function uploadFile<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export function useApi() {
  return {
    get: <T>(path: string) => request<T>('GET', path),
    post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
    put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
    del: <T>(path: string) => request<T>('DELETE', path),
    upload: <T>(path: string, formData: FormData) => uploadFile<T>(path, formData),
    getToken,
    setToken: (token: string) => localStorage.setItem('token', token),
    clearToken: () => { localStorage.removeItem('token'); localStorage.removeItem('refresh_token') },
  }
}
