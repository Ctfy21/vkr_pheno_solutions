<!--
  Design approach: DATA-DENSE detail page
  Trial info cards + studies grid. All data from real API.
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'

const route = useRoute()
const api = useApi()
const programId = computed(() => route.params.programId as string)
const trialId = computed(() => route.params.trialId as string)

const program = ref<any>(null)
const trial = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const programs = await api.get<any[]>('/programs')
    program.value = programs.find(p => p.id === programId.value)
    if (program.value) trial.value = (program.value.trials || []).find((t: any) => t.id === trialId.value)
    if (!trial.value) {
      // Try direct API
      trial.value = await api.get<any>(`/trials/${trialId.value}`).catch(() => null)
    }
  } catch {}
  loading.value = false
})
</script>

<template>
  <div v-if="trial" class="space-y-6 fade-in">
    <div>
      <router-link to="/programs" class="text-xs text-(--color-accent-green) hover:underline mb-2 inline-flex items-center gap-1">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
        {{ program?.name || 'Программы' }}
      </router-link>
      <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary) mt-2">{{ trial.name }}</h1>
      <p class="text-sm text-(--color-text-secondary) mt-1">{{ trial.description }}</p>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4"><span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Начало</span><p class="text-sm font-medium text-(--color-text-primary) mt-1">{{ trial.start_date || trial.startDate }}</p></div>
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4"><span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Окончание</span><p class="text-sm font-medium text-(--color-text-primary) mt-1">{{ trial.end_date || trial.endDate }}</p></div>
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4"><span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Эксперименты</span><p class="text-sm font-medium text-(--color-text-primary) mt-1">{{ (trial.studies || []).length }}</p></div>
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4"><span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Статус</span><p class="text-sm font-medium mt-1" :class="trial.active ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)'">{{ trial.active ? 'Активно' : 'Завершено' }}</p></div>
    </div>

    <div>
      <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-4">Эксперименты</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <router-link v-for="study in (trial.studies || [])" :key="study.id" :to="`/experiments/${study.id}`" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 hover:border-(--color-border-default) hover:bg-(--color-bg-hover) transition-all group">
          <div class="flex items-start justify-between mb-3">
            <span :class="['px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border', study.status === 'active' ? 'bg-(--color-accent-green)/10 text-(--color-accent-green) border-(--color-accent-green)/20' : study.status === 'completed' ? 'bg-(--color-accent-sky)/10 text-(--color-accent-sky) border-(--color-accent-sky)/20' : 'bg-(--color-bg-elevated) text-(--color-text-muted) border-(--color-border-subtle)']">{{ study.status === 'active' ? 'Активен' : study.status === 'completed' ? 'Завершен' : 'Черновик' }}</span>
            <span class="text-xs text-(--color-text-muted)">{{ study.study_type || study.studyType }}</span>
          </div>
          <h3 class="text-sm font-medium text-(--color-text-primary) group-hover:text-(--color-accent-green) transition-colors">{{ study.name }}</h3>
          <p class="text-xs text-(--color-text-muted) mt-1.5 line-clamp-2">{{ study.description }}</p>
          <div class="mt-4 flex items-center gap-4 text-xs text-(--color-text-muted)">
            <span>{{ study.plant_count || study.plantCount || 0 }} растений</span><span>&middot;</span>
            <span>{{ (study.observation_variables || study.observationVariables || []).length }} переменных</span>
          </div>
        </router-link>
      </div>
      <div v-if="(trial.studies || []).length === 0" class="text-center py-8 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl"><p class="text-sm text-(--color-text-muted)">Нет экспериментов</p></div>
    </div>
  </div>
  <div v-else-if="loading" class="space-y-6 fade-in"><div class="h-8 bg-(--color-bg-surface) rounded w-1/3 animate-pulse"></div></div>
  <div v-else class="text-center py-16"><p class="text-sm text-(--color-text-muted)">Испытание не найдено</p></div>
</template>
