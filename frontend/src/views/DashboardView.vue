<!--
  Design approach: DATA-DENSE
  Dashboard is the overview hub — maximum information density at a glance.
  6 stat cards in a single row, active experiments list, programs grid, team section.
  All data from real API. No mock fallbacks.
  Progressive loading with staggered animations for perceived speed.
-->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { useApi } from '@/composables/useApi'

const { user } = useAuth()
const api = useApi()
const loaded = ref(false)
const error = ref('')

const dashboardData = ref<any>({ programs: 0, trials: 0, experiments: 0, plants: 0, observations: 0, images: 0, organization_name: '' })
const studies = ref<any[]>([])
const programs = ref<any[]>([])
const members = ref<any[]>([])

const activeStudies = computed(() => studies.value.filter((s: any) => s.status === 'active'))

onMounted(async () => {
  try {
    const [d, s, p] = await Promise.all([
      api.get<any>('/dashboard'),
      api.get<any[]>('/studies').catch(() => []),
      api.get<any[]>('/programs').catch(() => []),
    ])
    dashboardData.value = d
    studies.value = s
    programs.value = p
    if (d.members) members.value = d.members
  } catch (e: any) {
    error.value = e.message
  }
  setTimeout(() => (loaded.value = true), 100)
})

const today = new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
</script>

<template>
  <div :class="['space-y-6', loaded ? 'fade-in' : 'opacity-0']">
    <!-- Welcome header -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">
          Добро пожаловать, {{ user?.name }}
        </h1>
        <p class="text-sm text-(--color-text-secondary) mt-1">
          {{ dashboardData.organization_name || 'PhenoPlant' }} &middot; {{ today }}
        </p>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="px-4 py-3 rounded-lg bg-(--color-accent-rose)/10 border border-(--color-accent-rose)/20 text-sm text-(--color-accent-rose)">
      {{ error }}
    </div>

    <!-- Active experiments -->
    <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
      <div class="px-5 py-4 border-b border-(--color-border-subtle) flex items-center justify-between">
        <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary)">Активные эксперименты</h3>
        <router-link to="/experiments" class="text-xs text-(--color-accent-green) hover:underline">Все эксперименты</router-link>
      </div>
      <div v-if="activeStudies.length" class="divide-y divide-(--color-border-subtle)">
        <router-link
          v-for="study in activeStudies"
          :key="study.id"
          :to="'/experiments/' + study.id"
          class="flex items-center gap-4 px-5 py-4 hover:bg-(--color-bg-hover) transition-colors group"
        >
          <div class="w-10 h-10 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center flex-shrink-0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-accent-green)">
              <path d="M9 3h6v4l3 8H6l3-8V3z" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M6 15v4a2 2 0 002 2h8a2 2 0 002-2v-4" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-(--color-text-primary) truncate group-hover:text-(--color-accent-green) transition-colors">{{ study.name }}</p>
            <p class="text-xs text-(--color-text-muted) mt-0.5">{{ study.plantCount || study.plant_count || 0 }} растений &middot; {{ study.studyType || study.study_type || '' }}</p>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20">Активен</span>
        </router-link>
      </div>
      <div v-else class="px-5 py-8 text-center text-(--color-text-muted) text-sm">Нет активных экспериментов</div>
    </div>

    <!-- Team members -->
    <div v-if="members.length" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
      <div class="px-5 py-4 border-b border-(--color-border-subtle)">
        <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary)">Команда</h3>
      </div>
      <div class="p-5 flex flex-wrap gap-4">
        <div v-for="m in members" :key="m.id || m.email" class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-gradient-to-br from-(--color-accent-green-muted) to-(--color-bg-elevated) flex items-center justify-center text-xs font-semibold text-(--color-accent-green)">
            {{ m.name?.charAt(0) || '?' }}
          </div>
          <div>
            <p class="text-xs font-medium text-(--color-text-primary)">{{ m.name }}</p>
            <p class="text-[10px] text-(--color-text-muted)">{{ m.role === 'admin' ? 'Администратор' : m.role === 'researcher' ? 'Исследователь' : 'Наблюдатель' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
