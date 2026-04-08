<!--
  Experiments grid with delete button
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useProgram } from '@/composables/useProgram'

const api = useApi()
const { currentProgram } = useProgram()
const studies = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const filterStatus = ref('')
const deleting = ref<string | null>(null)

onMounted(async () => {
  try { studies.value = await api.get<any[]>('/studies') } catch {}
  loading.value = false
})

const filtered = computed(() => {
  let result = studies.value
  // Filter by current program
  if (currentProgram.value?.id) {
    result = result.filter(s => s.programId === currentProgram.value?.id || !s.programId)
  }
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter(s => s.name.toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q) || (s.study_type || s.studyType || '').toLowerCase().includes(q))
  }
  if (filterStatus.value) result = result.filter(s => s.status === filterStatus.value)
  return result
})

async function deleteStudy(id: string, e: Event) {
  e.preventDefault()
  e.stopPropagation()
  if (!confirm('Удалить эксперимент?')) return
  deleting.value = id
  try {
    await api.del('/studies/' + id)
    studies.value = studies.value.filter(s => s.id !== id)
  } catch {}
  deleting.value = null
}

function animDelay(i: number): string {
  return (i * 60) + 'ms'
}

const statusLabel: Record<string, string> = { active: 'Активен', completed: 'Завершен', draft: 'Черновик', archived: 'Архив' }
</script>

<template>
  <div class="space-y-6 fade-in">
    <div class="flex items-end justify-between">
      <div>
        <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">Эксперименты</h1>
        <p class="text-sm text-(--color-text-secondary) mt-1">Все эксперименты (BrAPI Study) вашей организации</p>
      </div>
      <router-link to="/experiments/create" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 active:scale-[0.98] transition-all flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Новый эксперимент
      </router-link>
    </div>

    <div class="flex gap-3">
      <div class="flex-1 relative">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-4 top-1/2 -translate-y-1/2 text-(--color-text-muted)" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="search" type="text" placeholder="Поиск по названию, описанию, типу..." class="w-full pl-11 pr-4 py-2.5 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
      </div>
      <select v-model="filterStatus" class="px-4 py-2.5 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all">
        <option value="">Все статусы</option>
        <option value="active">Активные</option>
        <option value="completed">Завершенные</option>
        <option value="draft">Черновики</option>
      </select>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 animate-pulse">
        <div class="h-4 bg-(--color-bg-elevated) rounded w-1/4 mb-3"></div>
        <div class="h-5 bg-(--color-bg-elevated) rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-(--color-bg-elevated) rounded w-full"></div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <router-link v-for="(study, i) in filtered" :key="study.id" :to="'/experiments/' + study.id"
        class="slide-up bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 hover:border-(--color-border-default) hover:bg-(--color-bg-hover) transition-all group relative"
        :style="{ animationDelay: animDelay(i) }">
        <div class="flex items-center justify-between mb-3">
          <span :class="['px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border',
            study.status === 'active' ? 'bg-(--color-accent-green)/10 text-(--color-accent-green) border-(--color-accent-green)/20'
            : study.status === 'completed' ? 'bg-(--color-accent-sky)/10 text-(--color-accent-sky) border-(--color-accent-sky)/20'
            : 'bg-(--color-bg-elevated) text-(--color-text-muted) border-(--color-border-subtle)']"
          >{{ statusLabel[study.status] || study.status }}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-(--color-text-muted)">{{ study.study_type || study.studyType }}</span>
            <button @click="deleteStudy(study.id, $event)" :disabled="deleting === study.id"
              class="p-1.5 rounded-lg text-(--color-text-muted) hover:text-(--color-accent-rose) hover:bg-(--color-accent-rose)/10 transition-all disabled:opacity-30 opacity-0 group-hover:opacity-100"
              title="Удалить эксперимент">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/></svg>
            </button>
          </div>
        </div>
        <h3 class="text-sm font-medium text-(--color-text-primary) group-hover:text-(--color-accent-green) transition-colors line-clamp-2">{{ study.name }}</h3>
        <p class="text-xs text-(--color-text-muted) mt-1.5 line-clamp-2">{{ study.description }}</p>
        <div class="mt-4 pt-3 border-t border-(--color-border-subtle) grid grid-cols-3 gap-2 text-center">
          <div>
            <p class="text-lg font-semibold text-(--color-text-primary)">{{ study.plant_count || study.plantCount || 0 }}</p>
            <p class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Растений</p>
          </div>
          <div>
            <p class="text-lg font-semibold text-(--color-text-primary)">{{ (study.observation_variables || study.observationVariables || []).length }}</p>
            <p class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Переменных</p>
          </div>
          <div>
            <p class="text-xs font-medium text-(--color-text-secondary) mt-1">{{ study.start_date || study.startDate }}</p>
            <p class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Начало</p>
          </div>
        </div>
      </router-link>

      <router-link to="/experiments/create" class="border-2 border-dashed border-(--color-border-default) rounded-xl p-5 flex flex-col items-center justify-center text-center hover:border-(--color-accent-green)/30 hover:bg-(--color-bg-surface) transition-all group min-h-[200px]">
        <div class="w-12 h-12 rounded-xl bg-(--color-bg-surface) border border-(--color-border-subtle) flex items-center justify-center mb-3 group-hover:border-(--color-accent-green)/30 transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted) group-hover:text-(--color-accent-green) transition-colors" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </div>
        <p class="text-sm text-(--color-text-secondary) group-hover:text-(--color-text-primary) transition-colors">Создать эксперимент</p>
        <p class="text-xs text-(--color-text-muted) mt-1">Пошаговый мастер настройки</p>
      </router-link>
    </div>
  </div>
</template>
