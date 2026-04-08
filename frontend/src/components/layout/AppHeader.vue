<script setup lang="ts">
import { useRoute } from "vue-router"
import { computed, ref, watch, onMounted, onUnmounted } from "vue"
import { useApi } from "@/composables/useApi"

const route = useRoute()
const api = useApi()

// --- Breadcrumbs ---
const nameCache = ref<Record<string, string>>({})

const labelMap: Record<string, string> = {
  dashboard: "Обзор",
  programs: "Программы",
  experiments: "Эксперименты",
  variables: "Переменные",
  plants: "Растения",
  results: "Результаты",
  export: "Экспорт",
  containers: "Фенотипические решения",
  create: "Создание",
  select: "Выбор",
  admin: "Админ",
}

function isUUID(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s)
}

watch(() => route.params, async (params) => {
  const studyId = params.studyId as string
  if (studyId && isUUID(studyId) && !nameCache.value[studyId]) {
    try {
      const study = await api.get<any>("/studies/" + studyId)
      if (study?.name) nameCache.value[studyId] = study.name
    } catch {}
  }
}, { immediate: true })

const breadcrumbs = computed(() => {
  const crumbs: { label: string; to?: string }[] = []
  const segments = route.path.split("/").filter(Boolean)
  let pathAccum = ""
  for (const seg of segments) {
    pathAccum += "/" + seg
    let label = labelMap[seg] || seg
    if (isUUID(seg) && nameCache.value[seg]) {
      label = nameCache.value[seg]
    } else if (isUUID(seg)) {
      continue
    }
    crumbs.push({ label, to: pathAccum })
  }
  return crumbs
})

// --- Notifications ---
interface Notification {
  id: string
  type: string
  title: string
  message: string
  read: boolean
  createdAt: string
}

const notifications = ref<Notification[]>([])
const unreadCount = ref(0)
const showDropdown = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchNotifications() {
  try {
    const items = await api.get<Notification[]>("/notifications")
    notifications.value = items
    unreadCount.value = items.filter(n => !n.read).length
  } catch {}
}

async function fetchUnreadCount() {
  try {
    const res = await api.get<{ count: number }>("/notifications/unread-count")
    unreadCount.value = res.count
  } catch {}
}

async function markRead(id: string) {
  try {
    await api.put("/notifications/" + id + "/read")
    const n = notifications.value.find(x => x.id === id)
    if (n) {
      n.read = true
      unreadCount.value = notifications.value.filter(x => !x.read).length
    }
  } catch {}
}

async function markAllRead() {
  try {
    await api.put("/notifications/read-all")
    notifications.value.forEach(n => n.read = true)
    unreadCount.value = 0
  } catch {}
}

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    fetchNotifications()
  }
}

function closeDropdown(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest(".notif-container")) {
    showDropdown.value = false
  }
}

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diff < 60) return "только что"
  if (diff < 3600) return Math.floor(diff / 60) + " мин назад"
  if (diff < 86400) return Math.floor(diff / 3600) + " ч назад"
  return Math.floor(diff / 86400) + " дн назад"
}

onMounted(() => {
  fetchUnreadCount()
  pollTimer = setInterval(fetchUnreadCount, 30000)
  document.addEventListener("click", closeDropdown)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener("click", closeDropdown)
})
</script>

<template>
  <header class="h-14 border-b border-(--color-border-subtle) bg-(--color-bg-base)/80 backdrop-blur-md flex items-center px-6 sticky top-0 z-30">
    <nav class="flex items-center gap-2 text-sm flex-1">
      <template v-for="(crumb, i) in breadcrumbs" :key="crumb.to">
        <span v-if="i > 0" class="text-(--color-text-muted)">/</span>
        <router-link
          v-if="i < breadcrumbs.length - 1"
          :to="crumb.to!"
          class="text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
        >
          {{ crumb.label }}
        </router-link>
        <span v-else class="text-(--color-text-primary) font-medium">{{ crumb.label }}</span>
      </template>
    </nav>

    <!-- Notifications bell -->
    <div class="notif-container relative ml-4">
      <button
        @click.stop="toggleDropdown"
        class="relative p-2 rounded-lg hover:bg-(--color-bg-subtle) transition-colors"
        title="Уведомления"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             class="text-(--color-text-secondary)">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span
          v-if="unreadCount > 0"
          class="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1 font-medium"
        >
          {{ unreadCount > 99 ? "99+" : unreadCount }}
        </span>
      </button>

      <!-- Dropdown -->
      <div
        v-if="showDropdown"
        class="absolute right-0 top-full mt-2 w-80 bg-(--color-bg-base) border border-(--color-border-subtle) rounded-xl shadow-xl z-50 overflow-hidden"
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-(--color-border-subtle)">
          <span class="text-sm font-semibold text-(--color-text-primary)">Уведомления</span>
          <button
            v-if="unreadCount > 0"
            @click="markAllRead"
            class="text-xs text-(--color-accent) hover:underline"
          >
            Прочитать все
          </button>
        </div>
        <div class="max-h-80 overflow-y-auto">
          <div
            v-for="n in notifications"
            :key="n.id"
            @click="markRead(n.id)"
            class="px-4 py-3 border-b border-(--color-border-subtle) last:border-b-0 cursor-pointer transition-colors"
            :class="n.read ? 'opacity-60' : 'bg-(--color-bg-subtle)'"
          >
            <div class="flex items-start gap-2">
              <span
                v-if="!n.read"
                class="mt-1.5 w-2 h-2 rounded-full bg-(--color-accent) shrink-0"
              ></span>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-(--color-text-primary) truncate">{{ n.title }}</div>
                <div class="text-xs text-(--color-text-secondary) mt-0.5">{{ n.message }}</div>
                <div class="text-xs text-(--color-text-muted) mt-1">{{ timeAgo(n.createdAt) }}</div>
              </div>
            </div>
          </div>
          <div
            v-if="notifications.length === 0"
            class="px-4 py-8 text-center text-sm text-(--color-text-muted)"
          >
            Нет уведомлений
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
