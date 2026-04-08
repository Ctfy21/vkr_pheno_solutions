import { ref, onMounted } from 'vue'
import { useApi } from './useApi'

export function useCollection<T>(path: string, fallback: T[] = []) {
  const items = ref<T[]>(fallback)
  const loading = ref(false)
  const api = useApi()

  async function load() {
    if (!api.getToken()) return
    loading.value = true
    try {
      items.value = await api.get<T[]>(path)
    } catch {
      // keep fallback data
    } finally {
      loading.value = false
    }
  }

  async function create(data: Partial<T>): Promise<T | null> {
    try {
      const created = await api.post<T>(path, data)
      items.value = [...items.value, created]
      return created
    } catch {
      return null
    }
  }

  onMounted(load)

  return { items, loading, load, create }
}

export function useDashboard() {
  const stats = ref({ programs: 0, trials: 0, experiments: 0, plants: 0, observations: 0, images: 0 })
  const loading = ref(false)
  const api = useApi()

  async function load() {
    if (!api.getToken()) return
    loading.value = true
    try {
      stats.value = await api.get('/dashboard')
    } catch {}
    loading.value = false
  }

  onMounted(load)

  return { stats, loading, load }
}
