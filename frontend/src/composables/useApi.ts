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

function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback
  const utf = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utf && utf[1]) return decodeURIComponent(utf[1])
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain && plain[1] ? plain[1] : fallback
}

// Download a file produced by the API (export, archives) and hand it to the browser
async function downloadFile(path: string, fallbackName: string, init: { method?: string; body?: unknown } = {}): Promise<void> {
  const doFetch = () => fetch(`${API_BASE}${path}`, {
    method: init.method || 'GET',
    headers: authHeaders(),
    body: init.body ? JSON.stringify(init.body) : undefined,
  })
  let res = await doFetch()
  if (res.status === 401 && await tryRefreshToken()) res = await doFetch()
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : res.statusText)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filenameFromDisposition(res.headers.get('Content-Disposition'), fallbackName)
  a.click()
  URL.revokeObjectURL(url)
}

export function useApi() {
  return {
    get: <T>(path: string) => request<T>('GET', path),
    post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
    put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
    del: <T>(path: string) => request<T>('DELETE', path),
    upload: <T>(path: string, formData: FormData) => uploadFile<T>(path, formData),
    download: downloadFile,
    getToken,
    setToken: (token: string) => localStorage.setItem('token', token),
    clearToken: () => { localStorage.removeItem('token'); localStorage.removeItem('refresh_token') },
  }
}
