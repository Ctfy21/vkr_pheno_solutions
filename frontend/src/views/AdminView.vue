<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useApi } from "@/composables/useApi"
import { useAuth } from "@/composables/useAuth"

const api = useApi()
const { user } = useAuth()

const activeTab = ref<"solutions" | "users" | "brapi">("solutions")
const solutions = ref<any[]>([])
const allVariables = ref<any[]>([])
const users = ref<any[]>([])
const loading = ref(true)
const loadingUsers = ref(false)

// BrAPI state
const brapiServers = ref<any[]>([])
const loadingBrapi = ref(false)
const showBrapiModal = ref(false)
const brapiForm = ref({ name: '', url: '', description: '' })
const addingBrapi = ref(false)

// BrAPI browse state
const browseServerId = ref<string | null>(null)
const browseTab = ref<'programs' | 'studies' | 'variables'>('programs')
const browseData = ref<any[]>([])
const loadingBrowse = ref(false)
const importingItem = ref<string | null>(null)

// Create user modal
const showUserModal = ref(false)
const creatingUser = ref(false)
const userForm = ref({ email: '', password: '', firstName: '', lastName: '', role: 'researcher' })

function openCreateUser() {
  userForm.value = { email: '', password: '', firstName: '', lastName: '', role: 'researcher' }
  showUserModal.value = true
}

async function createUser() {
  creatingUser.value = true
  try {
    const newUser = await api.post<any>('/admin/users', userForm.value)
    users.value.push(newUser)
    showUserModal.value = false
  } catch {}
  creatingUser.value = false
}

const deletingUserId = ref<string | null>(null)

async function deleteUser(userId: string) {
  if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) return
  deletingUserId.value = userId
  try {
    await api.del('/admin/users/' + userId)
    users.value = users.value.filter((u: any) => u.id !== userId)
  } catch {}
  deletingUserId.value = null
}

// Modal state
const showModal = ref(false)
const editingId = ref<string | null>(null)
const form = ref({
  name: "",
  description: "",
  version: "1.0.0",
  dockerfile: "",
  resources: {
    cpuRequest: "500m",
    cpuLimit: "2000m",
    memRequest: "256Mi",
    memLimit: "1Gi",
    gpu: false,
    timeoutMinutes: 30,
  },
  outputVariables: [] as any[],
})
const saving = ref(false)
const buildingId = ref<string | null>(null)
const deletingId = ref<string | null>(null)

// Update version modal
const showUpdateModal = ref(false)
const updatingId = ref<string | null>(null)
const updateForm = ref({
  version: "",
  dockerfile: "",
  resources: {
    cpuRequest: "500m",
    cpuLimit: "2000m",
    memRequest: "256Mi",
    memLimit: "1Gi",
    gpu: false,
    timeoutMinutes: 30,
  },
  outputVariables: [] as any[],
})
const updatingSaving = ref(false)

onMounted(async () => {
  await Promise.all([loadSolutions(), loadVariables()])
})

async function loadSolutions() {
  loading.value = true
  try {
    solutions.value = await api.get<any[]>("/admin/solutions")
  } catch { solutions.value = [] }
  loading.value = false
}

async function loadVariables() {
  try {
    allVariables.value = await api.get<any[]>("/variables")
  } catch { allVariables.value = [] }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    users.value = await api.get<any[]>("/admin/users")
  } catch { users.value = [] }
  loadingUsers.value = false
}

// ─── BrAPI functions ─────────────────────────────────────────
async function loadBrapiServers() {
  loadingBrapi.value = true
  try {
    brapiServers.value = await api.get<any[]>('/admin/brapi-servers')
  } catch { brapiServers.value = [] }
  loadingBrapi.value = false
}

function openAddBrapi() {
  brapiForm.value = { name: '', url: '', description: '' }
  showBrapiModal.value = true
}

async function addBrapiServer() {
  addingBrapi.value = true
  try {
    const srv = await api.post<any>('/admin/brapi-servers', brapiForm.value)
    brapiServers.value.push(srv)
    showBrapiModal.value = false
  } catch (e: any) {
    alert(e.message || 'Error adding server')
  }
  addingBrapi.value = false
}

async function deleteBrapiServer(id: string) {
  if (!confirm('Удалить сервер?')) return
  try {
    await api.del('/admin/brapi-servers/' + id)
    brapiServers.value = brapiServers.value.filter(s => s.id !== id)
    if (browseServerId.value === id) {
      browseServerId.value = null
      browseData.value = []
    }
  } catch {}
}

async function activateBrapiServer(id: string) {
  try {
    await api.put('/admin/brapi-servers/' + id + '/activate', {})
    brapiServers.value = brapiServers.value.map(s => ({ ...s, active: s.id === id }))
  } catch (e: any) {
    alert('Ошибка: ' + (e.message || 'unknown'))
  }
}

async function browseServer(serverId: string) {
  if (browseServerId.value === serverId) {
    browseServerId.value = null
    browseData.value = []
    return
  }
  browseServerId.value = serverId
  browseTab.value = 'programs'
  await loadBrowseData(serverId, 'programs')
}

async function loadBrowseData(serverId: string, tab: string) {
  loadingBrowse.value = true
  browseData.value = []
  try {
    browseData.value = await api.get<any[]>(`/admin/brapi-servers/${serverId}/${tab}`)
  } catch (e: any) {
    browseData.value = []
  }
  loadingBrowse.value = false
}

async function switchBrowseTab(tab: 'programs' | 'studies' | 'variables') {
  browseTab.value = tab
  if (browseServerId.value) {
    await loadBrowseData(browseServerId.value, tab)
  }
}

async function importItems(type: 'programs' | 'studies' | 'observations') {
  if (!browseServerId.value) return
  importingItem.value = type
  try {
    const result = await api.post<any>(`/admin/brapi-servers/${browseServerId.value}/import/${type}`)
    alert(result.message || `Импортировано: ${result.imported}`)
  } catch (e: any) {
    alert('Ошибка импорта: ' + (e.message || 'unknown'))
  }
  importingItem.value = null
}

async function checkServerStatus(server: any): Promise<string> {
  try {
    await api.get(`/admin/brapi-servers/${server.id}/programs`)
    return 'online'
  } catch {
    return 'offline'
  }
}

function defaultResources() {
  return { cpuRequest: "500m", cpuLimit: "2000m", memRequest: "256Mi", memLimit: "1Gi", gpu: false, timeoutMinutes: 30 }
}

function openCreate() {
  editingId.value = null
  form.value = { name: "", description: "", version: "1.0.0", dockerfile: "", resources: defaultResources(), outputVariables: [] }
  showModal.value = true
}

function openEdit(sol: any) {
  editingId.value = sol.id
  form.value = {
    name: sol.name,
    description: sol.description,
    version: sol.version,
    dockerfile: sol.dockerfile,
    resources: sol.resources ? { ...defaultResources(), ...sol.resources } : defaultResources(),
    outputVariables: sol.outputVariables ? [...sol.outputVariables] : [],
  }
  showModal.value = true
}

function openUpdate(sol: any) {
  updatingId.value = sol.id
  updateForm.value = {
    version: sol.version,
    dockerfile: sol.dockerfile,
    resources: sol.resources ? { ...defaultResources(), ...sol.resources } : defaultResources(),
    outputVariables: sol.outputVariables ? [...sol.outputVariables] : [],
  }
  showUpdateModal.value = true
}

async function handleFileUpload(event: Event, target: 'form' | 'update') {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  const file = input.files[0]
  const text = await file.text()
  if (target === 'form') {
    form.value.dockerfile = text
  } else {
    updateForm.value.dockerfile = text
  }
  input.value = ""
}

async function saveSolution() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
      version: form.value.version,
      dockerfile: form.value.dockerfile,
      resources: form.value.resources,
      outputVariables: form.value.outputVariables,
    }
    if (editingId.value) {
      await api.put("/admin/solutions/" + editingId.value, payload)
    } else {
      await api.post("/admin/solutions", payload)
    }
    showModal.value = false
    await Promise.all([loadSolutions(), loadVariables()])
  } catch (e: any) {
    alert(e.message || "Error saving")
  }
  saving.value = false
}

async function saveUpdate() {
  if (!updatingId.value) return
  updatingSaving.value = true
  try {
    await api.put("/admin/solutions/" + updatingId.value, {
      version: updateForm.value.version,
      dockerfile: updateForm.value.dockerfile,
      resources: updateForm.value.resources,
    })
    showUpdateModal.value = false
    await Promise.all([loadSolutions(), loadVariables()])
  } catch (e: any) {
    alert(e.message || "Error updating")
  }
  updatingSaving.value = false
}

async function deleteSolution(id: string) {
  if (!confirm("Удалить решение?")) return
  deletingId.value = id
  try {
    await api.del("/admin/solutions/" + id)
    await Promise.all([loadSolutions(), loadVariables()])
  } catch {}
  deletingId.value = null
}

async function buildSolution(id: string) {
  buildingId.value = id
  try {
    await api.post("/admin/solutions/" + id + "/build")
    await Promise.all([loadSolutions(), loadVariables()])
  } catch (e: any) {
    alert("Ошибка сборки: " + (e.message || "unknown"))
  }
  buildingId.value = null
}

function switchTab(tab: "solutions" | "users" | "brapi") {
  activeTab.value = tab
  if (tab === "users" && users.value.length === 0) {
    loadUsers()
  }
  if (tab === "brapi" && brapiServers.value.length === 0) {
    loadBrapiServers()
  }
}

const roleLabel = (role: string) => {
  if (role === "admin") return "Администратор"
  if (role === "researcher") return "Исследователь"
  return "Наблюдатель"
}

const roleBadgeClass = (role: string) => {
  if (role === "admin") return "bg-red-500/10 text-red-400 border-red-500/20"
  if (role === "researcher") return "bg-sky-500/10 text-sky-400 border-sky-500/20"
  return "bg-gray-500/10 text-gray-400 border-gray-500/20"
}

function formatResources(sol: any) {
  if (!sol.resources) return 'Не указаны'
  const r = sol.resources
  let parts = [`CPU: ${r.cpuRequest || '?'}/${r.cpuLimit || '?'}`, `Mem: ${r.memRequest || '?'}/${r.memLimit || '?'}`]
  if (r.gpu) parts.push('GPU')
  if (r.timeoutMinutes) parts.push(`${r.timeoutMinutes} мин`)
  return parts.join(' · ')
}

function getBrowseItemName(item: any): string {
  if (browseTab.value === 'programs') return item.programName || item.name || '—'
  if (browseTab.value === 'studies') return item.studyName || item.name || '—'
  if (browseTab.value === 'variables') return item.observationVariableName || item.name || '—'
  return '—'
}

function getBrowseItemId(item: any): string {
  if (browseTab.value === 'programs') return item.programDbId || ''
  if (browseTab.value === 'studies') return item.studyDbId || ''
  if (browseTab.value === 'variables') return item.observationVariableDbId || ''
  return ''
}

function getBrowseItemExtra(item: any): string {
  if (browseTab.value === 'programs') return item.commonCropName || item.abbreviation || ''
  if (browseTab.value === 'studies') return item.studyType || item.studyDescription?.slice(0, 60) || ''
  if (browseTab.value === 'variables') {
    const trait = item.trait?.traitName || ''
    const method = item.method?.methodName || ''
    return [trait, method].filter(Boolean).join(' / ')
  }
  return ''
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <!-- Header -->
    <div>
      <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">Панель администратора</h1>
      <p class="text-sm text-(--color-text-secondary) mt-1">Управление фенотипическими решениями, пользователями и BrAPI серверами</p>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 bg-(--color-bg-surface) p-1 rounded-xl border border-(--color-border-subtle) w-fit">
      <button
        @click="switchTab('solutions')"
        :class="[
          'px-5 py-2 rounded-lg text-sm font-medium transition-all',
          activeTab === 'solutions'
            ? 'bg-(--color-bg-elevated) text-(--color-accent-green) shadow-sm'
            : 'text-(--color-text-muted) hover:text-(--color-text-secondary)'
        ]"
      >Фенотипические решения</button>
      <button
        @click="switchTab('users')"
        :class="[
          'px-5 py-2 rounded-lg text-sm font-medium transition-all',
          activeTab === 'users'
            ? 'bg-(--color-bg-elevated) text-(--color-accent-green) shadow-sm'
            : 'text-(--color-text-muted) hover:text-(--color-text-secondary)'
        ]"
      >Пользователи</button>
      <button
        @click="switchTab('brapi')"
        :class="[
          'px-5 py-2 rounded-lg text-sm font-medium transition-all',
          activeTab === 'brapi'
            ? 'bg-(--color-bg-elevated) text-(--color-accent-green) shadow-sm'
            : 'text-(--color-text-muted) hover:text-(--color-text-secondary)'
        ]"
      >BrAPI серверы</button>
    </div>

    <!-- Solutions Tab -->
    <div v-if="activeTab === 'solutions'">
      <div class="flex items-center justify-between mb-4">
        <span class="text-sm text-(--color-text-muted)">{{ solutions.length }} решений</span>
        <button @click="openCreate" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Добавить решение
        </button>
      </div>

      <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 animate-pulse">
          <div class="h-10 w-10 bg-(--color-bg-elevated) rounded-lg mb-3"></div>
          <div class="h-4 bg-(--color-bg-elevated) rounded w-2/3"></div>
        </div>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="sol in solutions" :key="sol.id" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 hover:border-(--color-border-default) transition-colors">
          <div class="flex items-start justify-between mb-3">
            <div class="w-10 h-10 rounded-lg bg-(--color-accent-sky)/10 flex items-center justify-center flex-shrink-0">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-accent-sky)" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
                <polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
            </div>
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-(--color-bg-elevated) text-(--color-accent-green) border border-(--color-accent-green)/20">v{{ sol.version }}</span>
              <span :class="['px-2 py-0.5 rounded text-[10px] font-semibold border', sol.imageBuilt ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20']">
                {{ sol.imageBuilt ? 'Собран' : 'Не собран' }}
              </span>
            </div>
          </div>

          <h3 class="text-sm font-semibold text-(--color-text-primary)">{{ sol.name }}</h3>
          <p class="text-xs text-(--color-text-muted) mt-1.5 line-clamp-2">{{ sol.description }}</p>

          <div class="mt-4 pt-3 border-t border-(--color-border-subtle) space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-(--color-text-muted)">Образ</span>
              <span class="font-mono text-(--color-text-secondary) truncate max-w-[200px]">{{ sol.imageName }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-(--color-text-muted)">Ресурсы</span>
              <span class="text-(--color-text-secondary)">{{ formatResources(sol) }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-(--color-text-muted)">Создан</span>
              <span class="text-(--color-text-secondary)">{{ sol.createdAt?.slice(0, 10) }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-(--color-text-muted)">Автор</span>
              <span class="text-(--color-text-secondary)">{{ sol.createdBy }}</span>
            </div>
            <div v-if="sol.outputVariables && sol.outputVariables.length" class="mt-2">
              <span class="text-[10px] text-(--color-text-muted) uppercase tracking-wider">Crop Ontology</span>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="ov in sol.outputVariables" :key="ov.coTermId" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-sky)/10 text-(--color-accent-sky) border border-(--color-accent-sky)/20">
                  {{ ov.name }} <span class="font-mono opacity-60">{{ ov.coTermId }}</span>
                </span>
              </div>
            </div>
          </div>

          <div class="mt-4 flex gap-2">
            <button @click="openEdit(sol)" class="flex-1 py-2 rounded-lg text-xs border border-(--color-border-default) text-(--color-text-secondary) hover:bg-(--color-bg-hover) transition-colors">Редактировать</button>
            <button @click="openUpdate(sol)" class="flex-1 py-2 rounded-lg text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors">Обновить</button>
            <button
              @click="buildSolution(sol.id)"
              :disabled="buildingId === sol.id || sol.imageBuilt === true"
              :class="[
                'flex-1 py-2 rounded-lg text-xs border transition-colors',
                sol.imageBuilt === true
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 cursor-default opacity-70'
                  : 'bg-(--color-accent-sky)/10 text-(--color-accent-sky) border-(--color-accent-sky)/20 hover:bg-(--color-accent-sky)/20 disabled:opacity-40'
              ]"
            >{{ sol.imageBuilt === true ? 'Собрано ✓' : buildingId === sol.id ? 'Сборка...' : 'Собрать образ' }}</button>
            <button
              @click="deleteSolution(sol.id)"
              :disabled="deletingId === sol.id"
              class="py-2 px-3 rounded-lg text-xs border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </div>

        <div v-if="solutions.length === 0" class="col-span-full text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
          <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-(--color-bg-elevated) flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-(--color-text-muted)" stroke-linecap="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>
          </div>
          <p class="text-sm text-(--color-text-muted)">Нет фенотипических решений</p>
          <p class="text-xs text-(--color-text-muted) mt-1">Добавьте первое решение с Dockerfile</p>
        </div>
      </div>
    </div>

    <!-- Users Tab -->
    <div v-if="activeTab === 'users'">
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-(--color-text-muted)">{{ users.length }} пользователей</p>
        <button @click="openCreateUser" class="px-4 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Новый пользователь
        </button>
      </div>
      <div v-if="loadingUsers" class="space-y-3">
        <div v-for="i in 4" :key="i" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4 animate-pulse">
          <div class="h-4 bg-(--color-bg-elevated) rounded w-1/3"></div>
        </div>
      </div>
      <div v-else class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div class="grid grid-cols-[1.2fr_1fr_1.2fr_auto_auto_auto] gap-4 px-5 py-3 border-b border-(--color-border-subtle) text-[10px] uppercase tracking-wider text-(--color-text-muted)">
          <span>ФИО</span>
          <span>Email</span>
          <span>Роль</span>
          <span>Статус</span>
          <span></span>
        </div>
        <div v-for="u in users" :key="u.id" class="grid grid-cols-[1.2fr_1fr_1.2fr_auto_auto_auto] gap-4 px-5 py-3.5 border-b border-(--color-border-subtle) last:border-b-0 hover:bg-(--color-bg-hover) transition-colors">
          <span class="text-sm text-(--color-text-primary) font-medium truncate">{{ u.name || u.username }}</span>
          <span class="text-sm text-(--color-text-secondary) font-mono truncate">{{ u.email }}</span>
          <span><span :class="['px-2 py-0.5 rounded text-[10px] font-semibold border', roleBadgeClass(u.role)]">{{ roleLabel(u.role) }}</span></span>
          <span :class="['w-2 h-2 rounded-full mt-1.5', u.enabled ? 'bg-emerald-400' : 'bg-red-400']"></span>
          <button @click="deleteUser(u.id)" :disabled="deletingUserId === u.id" class="p-1.5 rounded-lg text-xs border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-30" title="Удалить пользователя">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
          </button>
        </div>
        <div v-if="users.length === 0" class="px-5 py-8 text-center text-sm text-(--color-text-muted)">Нет пользователей</div>
      </div>
    </div>

    <!-- BrAPI Servers Tab -->
    <div v-if="activeTab === 'brapi'">
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-(--color-text-muted)">{{ brapiServers.length }} серверов</p>
        <button @click="openAddBrapi" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Добавить сервер
        </button>
      </div>

      <div v-if="loadingBrapi" class="space-y-3">
        <div v-for="i in 3" :key="i" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 animate-pulse">
          <div class="h-5 bg-(--color-bg-elevated) rounded w-1/3 mb-2"></div>
          <div class="h-4 bg-(--color-bg-elevated) rounded w-2/3"></div>
        </div>
      </div>

      <div v-else class="space-y-4">
        <div v-for="srv in brapiServers" :key="srv.id" :class="['bg-(--color-bg-surface) border rounded-xl overflow-hidden transition-colors', srv.active ? 'border-(--color-accent-green)/50 ring-1 ring-(--color-accent-green)/20' : 'border-(--color-border-subtle) hover:border-(--color-border-default)']">
          <div class="p-5">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-violet-400" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
                    <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
                    <line x1="6" y1="6" x2="6.01" y2="6"/>
                    <line x1="6" y1="18" x2="6.01" y2="18"/>
                  </svg>
                </div>
                <div>
                  <h3 class="text-sm font-semibold text-(--color-text-primary)">{{ srv.name }}</h3>
                  <p class="text-xs text-(--color-text-muted) font-mono mt-0.5">{{ srv.url }}</p>
                  <p v-if="srv.description" class="text-xs text-(--color-text-secondary) mt-1">{{ srv.description }}</p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button @click="browseServer(srv.id)" :class="['px-3 py-1.5 rounded-lg text-xs border transition-colors', browseServerId === srv.id ? 'bg-violet-500/10 text-violet-400 border-violet-500/20' : 'border-(--color-border-default) text-(--color-text-secondary) hover:bg-(--color-bg-hover)']">
                  {{ browseServerId === srv.id ? 'Скрыть' : 'Обзор' }}
                </button>
                <button v-if="!srv.active" @click="activateBrapiServer(srv.id)" class="px-2.5 py-1.5 rounded-lg text-xs border border-(--color-accent-green)/30 text-(--color-accent-green) hover:bg-(--color-accent-green)/10 transition-colors font-medium">Активировать</button>
                <span v-else class="px-2.5 py-1.5 rounded-lg text-xs bg-(--color-accent-green)/15 text-(--color-accent-green) font-semibold">Активный</span>
                <button @click="deleteBrapiServer(srv.id)" class="p-1.5 rounded-lg text-xs border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Browse Panel -->
          <div v-if="browseServerId === srv.id" class="border-t border-(--color-border-subtle) p-5 bg-(--color-bg-base)/50">
            <!-- Browse tabs -->
            <div class="flex items-center gap-4 mb-4">
              <div class="flex gap-1 bg-(--color-bg-surface) p-0.5 rounded-lg border border-(--color-border-subtle)">
                <button @click="switchBrowseTab('programs')" :class="['px-3 py-1.5 rounded-md text-xs transition-all', browseTab === 'programs' ? 'bg-(--color-bg-elevated) text-(--color-accent-green) shadow-sm' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">Программы</button>
                <button @click="switchBrowseTab('studies')" :class="['px-3 py-1.5 rounded-md text-xs transition-all', browseTab === 'studies' ? 'bg-(--color-bg-elevated) text-(--color-accent-green) shadow-sm' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">Эксперименты</button>
                <button @click="switchBrowseTab('variables')" :class="['px-3 py-1.5 rounded-md text-xs transition-all', browseTab === 'variables' ? 'bg-(--color-bg-elevated) text-(--color-accent-green) shadow-sm' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">Переменные</button>
              </div>
              <button
                @click="importItems(browseTab === 'variables' ? 'observations' : browseTab)"
                :disabled="importingItem !== null || browseData.length === 0"
                class="px-3 py-1.5 rounded-lg text-xs bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20 hover:bg-(--color-accent-green)/20 transition-colors disabled:opacity-40"
              >
                {{ importingItem ? 'Импорт...' : `Импортировать все ${browseTab === 'programs' ? 'программы' : browseTab === 'studies' ? 'эксперименты' : 'наблюдения'}` }}
              </button>
            </div>

            <div v-if="loadingBrowse" class="space-y-2">
              <div v-for="i in 3" :key="i" class="h-10 bg-(--color-bg-elevated) rounded-lg animate-pulse"></div>
            </div>

            <div v-else-if="browseData.length === 0" class="text-center py-8">
              <p class="text-sm text-(--color-text-muted)">Нет данных</p>
            </div>

            <div v-else class="space-y-1.5 max-h-80 overflow-y-auto">
              <div v-for="(item, idx) in browseData" :key="idx" class="flex items-center justify-between px-4 py-2.5 bg-(--color-bg-surface) rounded-lg border border-(--color-border-subtle)">
                <div class="min-w-0 flex-1">
                  <span class="text-sm text-(--color-text-primary) font-medium">{{ getBrowseItemName(item) }}</span>
                  <span class="text-xs text-(--color-text-muted) ml-2">{{ getBrowseItemExtra(item) }}</span>
                </div>
                <span class="text-[10px] font-mono text-(--color-text-muted) flex-shrink-0 ml-3">{{ getBrowseItemId(item) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Local BrAPI server info -->
        <div class="bg-(--color-bg-surface) border border-(--color-accent-green)/20 rounded-xl p-5 mb-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-accent-green)" stroke-linecap="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <h4 class="text-sm font-medium text-(--color-text-primary)">Локальный BrAPI сервер</h4>
                  <span class="px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20">Активен</span>
                </div>
                <p class="text-xs text-(--color-text-muted) mt-0.5 font-mono">/brapi/v2/ — 9 endpoints (programs, trials, studies, observations, variables, germplasm, observationunits, serverinfo)</p>
              </div>
            </div>
            <a href="/brapi/v2/serverinfo" target="_blank" class="text-xs text-(--color-accent-green) hover:underline">serverinfo →</a>
          </div>
          <p class="text-xs text-(--color-text-muted) mt-3">Внешние BrAPI-клиенты (BreedBase, BMS, R/brapi) могут подключиться к этому серверу по адресу текущего хоста. Ниже можно подключить внешние BrAPI серверы для импорта данных.</p>
        </div>

        <div v-if="brapiServers.length === 0" class="text-center py-10 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
          <p class="text-sm text-(--color-text-muted)">Нет подключённых внешних BrAPI серверов</p>
          <p class="text-xs text-(--color-text-muted) mt-1">Нажмите «Добавить сервер» для подключения к внешнему BrAPI v2.1 серверу</p>
        </div>
      </div>
    </div>

    <!-- Add BrAPI Server Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showBrapiModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showBrapiModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-5">Добавить BrAPI сервер</h2>
            <form @submit.prevent="addBrapiServer" class="space-y-4">
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название</label>
                <input v-model="brapiForm.name" type="text" required placeholder="Breeding Management System"
                  class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">URL сервера</label>
                <input v-model="brapiForm.url" type="url" required placeholder="https://brapi.example.com"
                  class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) font-mono placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                <p class="text-[10px] text-(--color-text-muted) mt-1">Базовый URL без /brapi/v2</p>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Описание</label>
                <textarea v-model="brapiForm.description" rows="2" placeholder="Описание сервера (опционально)"
                  class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-none"></textarea>
              </div>
              <div class="flex gap-3 pt-2">
                <button type="button" @click="showBrapiModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
                <button type="submit" :disabled="addingBrapi || !brapiForm.name || !brapiForm.url" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">
                  {{ addingBrapi ? 'Добавление...' : 'Добавить' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Create User Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showUserModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showUserModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-5">Новый пользователь</h2>
            <form @submit.prevent="createUser" class="space-y-4">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Фамилия</label>
                  <input v-model="userForm.lastName" type="text" required placeholder="Иванов" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                </div>
                <div>
                  <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Имя</label>
                  <input v-model="userForm.firstName" type="text" required placeholder="Иван" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                </div>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Email</label>
                <input v-model="userForm.email" type="email" required placeholder="ivanov@institute.ru" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Пароль</label>
                <input v-model="userForm.password" type="password" required minlength="6" placeholder="Минимум 6 символов" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Роль</label>
                <div class="flex gap-2">
                  <button v-for="r in [{value:'researcher',label:'Исследователь'},{value:'observer',label:'Наблюдатель'},{value:'admin',label:'Администратор'}]" :key="r.value" type="button" @click="userForm.role = r.value"
                    :class="['px-4 py-2.5 rounded-lg border text-sm transition-all',
                      userForm.role === r.value ? 'bg-(--color-accent-green)/10 border-(--color-accent-green)/30 text-(--color-accent-green)' : 'bg-(--color-bg-base) border-(--color-border-subtle) text-(--color-text-secondary) hover:border-(--color-border-default)']">
                    {{ r.label }}
                  </button>
                </div>
              </div>
              <div class="flex gap-3 pt-2">
                <button type="button" @click="showUserModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
                <button type="submit" :disabled="creatingUser" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">
                  {{ creatingUser ? 'Создание...' : 'Создать' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Create/Edit Solution Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showModal = false"></div>
          <div class="relative w-full max-w-2xl mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl slide-up max-h-[90vh] flex flex-col">
            <div class="px-6 pt-6 pb-4 border-b border-(--color-border-subtle) flex-shrink-0">
              <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary)">
                {{ editingId ? 'Редактировать решение' : 'Новое фенотипическое решение' }}
              </h2>
              <p class="text-xs text-(--color-text-muted) mt-1">Dockerfile и параметры ресурсов для обработки изображений</p>
            </div>

            <div class="px-6 py-4 overflow-y-auto flex-1 space-y-4">
              <div class="grid grid-cols-[1fr_auto] gap-4">
                <div>
                  <label class="block text-[10px] text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название</label>
                  <input v-model="form.name" type="text" required placeholder="Wheat Ear Counter"
                    class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                </div>
                <div>
                  <label class="block text-[10px] text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Версия</label>
                  <input v-model="form.version" type="text" placeholder="1.0.0"
                    class="w-32 px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) font-mono placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                </div>
              </div>

              <div>
                <label class="block text-[10px] text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Описание</label>
                <textarea v-model="form.description" rows="2" placeholder="Описание алгоритма..."
                  class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-none"></textarea>
              </div>

              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <label class="text-[10px] text-(--color-text-muted) uppercase tracking-wider">Dockerfile</label>
                  <label class="text-[10px] text-(--color-accent-green) cursor-pointer hover:underline">
                    <input type="file" accept="Dockerfile,*" class="hidden" @change="(e) => handleFileUpload(e, 'form')" />
                    Загрузить из файла
                  </label>
                </div>
                <textarea v-model="form.dockerfile" rows="8" placeholder="FROM python:3.12-slim&#10;WORKDIR /app&#10;COPY . .&#10;RUN pip install -r requirements.txt&#10;CMD [&quot;python&quot;, &quot;run.py&quot;]"
                  class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) font-mono leading-relaxed placeholder:text-(--color-text-muted)/40 focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-y" spellcheck="false"></textarea>
              </div>

              <div>
                <label class="block text-[10px] text-(--color-text-muted) mb-3 uppercase tracking-wider">Требования к ресурсам</label>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">CPU запрос</label>
                    <input v-model="form.resources.cpuRequest" type="text" placeholder="500m"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">CPU лимит</label>
                    <input v-model="form.resources.cpuLimit" type="text" placeholder="2000m"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">Память запрос</label>
                    <input v-model="form.resources.memRequest" type="text" placeholder="256Mi"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">Память лимит</label>
                    <input v-model="form.resources.memLimit" type="text" placeholder="1Gi"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                </div>
                <div class="flex items-center gap-6 mt-3">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" v-model="form.resources.gpu" class="w-4 h-4 rounded border border-(--color-border-default) accent-emerald-500" />
                    <span class="text-xs text-(--color-text-secondary)">Требуется GPU</span>
                  </label>
                  <div class="flex items-center gap-2">
                    <label class="text-[10px] text-(--color-text-muted)">Таймаут (мин)</label>
                    <input v-model.number="form.resources.timeoutMinutes" type="number" min="1" max="1440" placeholder="30"
                      class="w-20 px-3 py-1.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                </div>
              </div>
            </div>

            <div class="px-6 py-4 border-t border-(--color-border-subtle) flex gap-3 flex-shrink-0">
              <button @click="showModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
              <button
                @click="saveSolution"
                :disabled="!form.name || !form.dockerfile || saving"
                class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30"
              >{{ saving ? 'Сохранение...' : editingId ? 'Сохранить' : 'Создать' }}</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Update Version Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showUpdateModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showUpdateModal = false"></div>
          <div class="relative w-full max-w-2xl mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl slide-up max-h-[90vh] flex flex-col">
            <div class="px-6 pt-6 pb-4 border-b border-(--color-border-subtle) flex-shrink-0">
              <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary)">Обновить версию</h2>
              <p class="text-xs text-(--color-text-muted) mt-1">После обновления потребуется пересборка образа</p>
            </div>

            <div class="px-6 py-4 overflow-y-auto flex-1 space-y-4">
              <div>
                <label class="block text-[10px] text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Новая версия</label>
                <input v-model="updateForm.version" type="text" placeholder="1.1.0"
                  class="w-48 px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) font-mono placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
              </div>

              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <label class="text-[10px] text-(--color-text-muted) uppercase tracking-wider">Dockerfile</label>
                  <label class="text-[10px] text-(--color-accent-green) cursor-pointer hover:underline">
                    <input type="file" accept="Dockerfile,*" class="hidden" @change="(e) => handleFileUpload(e, 'update')" />
                    Загрузить из файла
                  </label>
                </div>
                <textarea v-model="updateForm.dockerfile" rows="8"
                  class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) font-mono leading-relaxed focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-y" spellcheck="false"></textarea>
              </div>

              <div>
                <label class="block text-[10px] text-(--color-text-muted) mb-3 uppercase tracking-wider">Требования к ресурсам</label>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">CPU запрос</label>
                    <input v-model="updateForm.resources.cpuRequest" type="text" placeholder="500m"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">CPU лимит</label>
                    <input v-model="updateForm.resources.cpuLimit" type="text" placeholder="2000m"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">Память запрос</label>
                    <input v-model="updateForm.resources.memRequest" type="text" placeholder="256Mi"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-(--color-text-muted) mb-1">Память лимит</label>
                    <input v-model="updateForm.resources.memLimit" type="text" placeholder="1Gi"
                      class="w-full px-3 py-2 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                </div>
                <div class="flex items-center gap-6 mt-3">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" v-model="updateForm.resources.gpu" class="w-4 h-4 rounded border border-(--color-border-default) accent-emerald-500" />
                    <span class="text-xs text-(--color-text-secondary)">Требуется GPU</span>
                  </label>
                  <div class="flex items-center gap-2">
                    <label class="text-[10px] text-(--color-text-muted)">Таймаут (мин)</label>
                    <input v-model.number="updateForm.resources.timeoutMinutes" type="number" min="1" max="1440" placeholder="30"
                      class="w-20 px-3 py-1.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
                  </div>
                </div>
              </div>
            </div>

            <div class="px-6 py-4 border-t border-(--color-border-subtle) flex gap-3 flex-shrink-0">
              <button @click="showUpdateModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
              <button
                @click="saveUpdate"
                :disabled="!updateForm.version || updatingSaving"
                class="flex-1 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30"
              >{{ updatingSaving ? 'Сохранение...' : 'Обновить версию' }}</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
