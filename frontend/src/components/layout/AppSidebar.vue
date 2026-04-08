<script setup lang="ts">
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useAuth } from "@/composables/useAuth"

import { useProgram } from "@/composables/useProgram"

const route = useRoute()
const router = useRouter()
const { user, logout } = useAuth()
const { currentProgram, setProgram } = useProgram()

const isAdmin = computed(() => user.value?.role === "admin")

function goToSelectProgram() {
  router.push('/programs/select')
}

const navItems = computed(() => {
  const items = [
    { label: "Обзор", icon: "grid", to: "/dashboard" },
    { label: "Эксперименты", icon: "flask", to: "/experiments" },
    { label: "Переменные", icon: "variable", to: "/variables" },
    { label: "Фенотипические решения", icon: "box", to: "/containers" },
  ]
  if (isAdmin.value) {
    items.push({ label: "Админ", icon: "shield", to: "/admin" })
  }
  return items
})

const isActive = (path: string) => computed(() => route.path.startsWith(path))

function handleLogout() {
  logout()
  router.push("/auth")
}
</script>

<template>
  <aside
    class="fixed left-0 top-0 bottom-0 w-64 bg-(--color-bg-base) border-r border-(--color-border-subtle) flex flex-col z-40"
  >
    <!-- Logo -->
    <div class="px-5 pt-6 pb-3">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-(--color-accent-green) to-(--color-accent-green-dim) flex items-center justify-center">
          <span class="material-symbols-outlined text-(--color-text-inverse)" style="font-size: 20px">eco</span>
        </div>
        <div>
          <h1 class="text-sm font-semibold tracking-tight text-(--color-text-primary)">PhenoPlant</h1>
          <p class="text-[10px] text-(--color-text-muted) tracking-wider uppercase">Digital Phenotyping</p>
        </div>
      </div>
    </div>

    <!-- Program selector -->
    <div class="px-3 pb-3">
      <button @click="goToSelectProgram"
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-(--color-bg-surface) border border-(--color-border-subtle) hover:border-(--color-border-default) transition-all text-left group">
        <div class="w-7 h-7 rounded-md bg-(--color-accent-green)/10 flex items-center justify-center flex-shrink-0">
          <span class="text-[10px] font-mono font-bold text-(--color-accent-green)">{{ currentProgram?.abbreviation || '?' }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-(--color-text-primary) truncate">{{ currentProgram?.name || 'Выберите программу' }}</p>
          <p class="text-[10px] text-(--color-text-muted)">Программа</p>
        </div>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted)" stroke-linecap="round">
          <polyline points="9,6 15,12 9,18"/>
        </svg>
      </button>
    </div>

    <div class="mx-5 glow-line"></div>

    <!-- Navigation -->
    <nav class="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group',
          isActive(item.to).value
            ? 'bg-(--color-bg-elevated) text-(--color-accent-green)'
            : 'text-(--color-text-secondary) hover:text-(--color-text-primary) hover:bg-(--color-bg-surface)',
        ]"
      >
        <svg v-if="item.icon === 'grid'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7" rx="1"/>
          <rect x="14" y="3" width="7" height="7" rx="1"/>
          <rect x="3" y="14" width="7" height="7" rx="1"/>
          <rect x="14" y="14" width="7" height="7" rx="1"/>
        </svg>
        <svg v-else-if="item.icon === 'flask'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 3h6v4l3 8H6l3-8V3z"/>
          <path d="M6 15v4a2 2 0 002 2h8a2 2 0 002-2v-4"/>
        </svg>
        <svg v-else-if="item.icon === 'variable'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 7h4l4 10 4-10h4"/>
          <path d="M3 17h18"/>
        </svg>
        <svg v-else-if="item.icon === 'box'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
          <polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
          <line x1="12" y1="22.08" x2="12" y2="12"/>
        </svg>
        <svg v-else-if="item.icon === 'shield'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>

        <span>{{ item.label }}</span>
        <span
          v-if="isActive(item.to).value"
          class="ml-auto w-1.5 h-1.5 rounded-full bg-(--color-accent-green)"
        />
      </router-link>
    </nav>

    <!-- User section -->
    <div class="p-3 border-t border-(--color-border-subtle)">
      <div class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-(--color-bg-surface) transition-colors cursor-pointer group" @click="handleLogout">
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-(--color-accent-green-muted) to-(--color-bg-elevated) flex items-center justify-center text-xs font-semibold text-(--color-accent-green)">
          {{ user?.name?.charAt(0) }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-(--color-text-primary) truncate">{{ user?.name }}</p>
          <p class="text-[10px] text-(--color-text-muted)">{{ user?.role === 'admin' ? 'Администратор' : user?.role === 'researcher' ? 'Исследователь' : 'Наблюдатель' }}</p>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-text-muted) opacity-0 group-hover:opacity-100 transition-opacity" stroke-linecap="round">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
          <polyline points="16,17 21,12 16,7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
      </div>
    </div>
  </aside>
</template>


