<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useApi } from "@/composables/useApi"
import { useAuth } from "@/composables/useAuth"

const api = useApi()
const { user } = useAuth()
const solutions = ref<any[]>([])
const studies = ref<any[]>([])
const loading = ref(true)
const detailSolution = ref<any>(null)
const useModal = ref<any>(null)
const selectedStudyId = ref("")
const linkSuccess = ref(false)

onMounted(async () => {
  try {
    const [s, st] = await Promise.all([
      api.get<any[]>("/admin/solutions").catch(() => []),
      api.get<any[]>("/studies").catch(() => []),
    ])
    solutions.value = s
    studies.value = st
  } catch {}
  loading.value = false
})

const activeStudies = computed(() => studies.value.filter((s: any) => s.status === "active"))
const builtSolutions = computed(() => solutions.value.filter((s: any) => s.imageBuilt))

async function linkToExperiment() {
  if (!selectedStudyId.value || !useModal.value) return
  try {
    await api.post("/studies/" + selectedStudyId.value + "/container-images", {
      container_image_id: useModal.value.id,
    })
    linkSuccess.value = true
    setTimeout(() => { linkSuccess.value = false; useModal.value = null; selectedStudyId.value = "" }, 2000)
  } catch {}
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <div>
      <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">Фенотипические решения</h1>
      <p class="text-sm text-(--color-text-secondary) mt-1">Алгоритмы машинного обучения для обработки изображений растений</p>
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
          </div>
        </div>

        <h3 class="text-sm font-semibold text-(--color-text-primary)">{{ sol.name }}</h3>
        <p class="text-xs text-(--color-text-muted) mt-1.5 line-clamp-2">{{ sol.description }}</p>

        <div v-if="sol.outputVariables && sol.outputVariables.length" class="mt-3 flex flex-wrap gap-1.5">
          <span v-for="ov in sol.outputVariables" :key="ov.coTermId || ov.name"
            class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20">
            {{ ov.name }}<span v-if="ov.coTermId" class="ml-1 opacity-60">({{ ov.coTermId }})</span>
          </span>
        </div>

        <div class="mt-4 pt-3 border-t border-(--color-border-subtle) space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="text-(--color-text-muted)">Образ</span>
            <span class="font-mono text-(--color-text-secondary) truncate max-w-[200px]">{{ sol.imageName }}</span>
          </div>
          <div class="flex items-center justify-between text-xs">
            <span class="text-(--color-text-muted)">Создан</span>
            <span class="text-(--color-text-secondary)">{{ sol.createdAt?.slice(0, 10) }}</span>
          </div>
        </div>

        <div class="mt-4 flex gap-2">
          <button @click="detailSolution = sol" class="flex-1 py-2 rounded-lg text-xs border border-(--color-border-default) text-(--color-text-secondary) hover:bg-(--color-bg-hover) transition-colors">Подробнее</button>

        </div>
      </div>

      <div v-if="solutions.length === 0" class="col-span-full text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
        <p class="text-sm text-(--color-text-muted)">Нет доступных решений</p>
        <p v-if="user?.role === 'admin'" class="text-xs text-(--color-text-muted) mt-1">
          <router-link to="/admin" class="text-(--color-accent-green) hover:underline">Добавьте решение</router-link> через панель администратора
        </p>
      </div>
    </div>

    <!-- Detail Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="detailSolution" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="detailSolution = null"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <div class="flex items-start justify-between mb-5">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-(--color-accent-sky)/10 flex items-center justify-center">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-accent-sky)" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27,6.96 12,12.01 20.73,6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                </div>
                <div>
                  <h2 class="font-(family-name:--font-display) text-lg text-(--color-text-primary)">{{ detailSolution.name }}</h2>
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-(--color-bg-elevated) text-(--color-accent-green) border border-(--color-accent-green)/20">v{{ detailSolution.version }}</span>
                </div>
              </div>
              <button @click="detailSolution = null" class="text-(--color-text-muted) hover:text-(--color-text-primary) transition-colors p-1">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div class="space-y-4">
              <div>
                <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Описание</span>
                <p class="text-sm text-(--color-text-secondary) mt-1">{{ detailSolution.description }}</p>
              </div>
              <div class="bg-(--color-bg-base) rounded-xl p-4 space-y-3">
                <div class="flex items-center justify-between text-xs"><span class="text-(--color-text-muted)">Docker образ</span><span class="font-mono text-(--color-text-primary)">{{ detailSolution.imageName }}</span></div>
                <div class="flex items-center justify-between text-xs"><span class="text-(--color-text-muted)">Статус</span><span :class="detailSolution.imageBuilt ? 'text-emerald-400' : 'text-amber-400'">{{ detailSolution.imageBuilt ? 'Собран' : 'Не собран' }}</span></div>
                <div class="flex items-center justify-between text-xs"><span class="text-(--color-text-muted)">Автор</span><span class="text-(--color-text-secondary)">{{ detailSolution.createdBy }}</span></div>
                <div class="flex items-center justify-between text-xs"><span class="text-(--color-text-muted)">Создан</span><span class="text-(--color-text-secondary)">{{ detailSolution.createdAt?.slice(0, 10) }}</span></div>
              </div>
            </div>
            <div class="flex gap-3 mt-5">
              <button @click="detailSolution = null" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Закрыть</button>

            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Use Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="useModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="useModal = null"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-1">Использовать в эксперименте</h2>
            <p class="text-xs text-(--color-text-muted) mb-5">Привязать <span class="font-mono text-(--color-accent-green)">{{ useModal.name }} v{{ useModal.version }}</span></p>
            <div v-if="linkSuccess" class="py-8 text-center">
              <div class="w-14 h-14 mx-auto mb-4 rounded-full bg-(--color-accent-green)/10 flex items-center justify-center">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-(--color-accent-green)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
              </div>
              <p class="text-sm font-medium text-(--color-text-primary)">Решение привязано!</p>
            </div>
            <div v-else class="space-y-4">
              <div class="space-y-2 max-h-64 overflow-y-auto">
                <label v-for="s in activeStudies" :key="s.id" :class="['block p-4 rounded-xl border cursor-pointer transition-all', selectedStudyId === s.id ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']" >
                  <input type="radio" v-model="selectedStudyId" :value="s.id" class="hidden" />
                  <div class="flex items-center gap-3">
                    <div :class="['w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0', selectedStudyId === s.id ? 'border-(--color-accent-green) bg-(--color-accent-green)' : 'border-(--color-text-muted)']" >
                      <svg v-if="selectedStudyId === s.id" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" class="text-(--color-text-inverse)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                    </div>
                    <div>
                      <p class="text-sm font-medium text-(--color-text-primary)">{{ s.name }}</p>
                      <p class="text-xs text-(--color-text-muted)">{{ s.plant_count || s.plantCount || 0 }} растений</p>
                    </div>
                  </div>
                </label>
              </div>
              <div class="flex gap-3 pt-2">
                <button @click="useModal = null" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
                <button @click="linkToExperiment" :disabled="!selectedStudyId" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30">Привязать</button>
              </div>
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
