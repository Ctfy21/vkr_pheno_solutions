<!--
  Design approach: HYBRID (split manual/upload with progressive disclosure)
  Tab switcher for manual entry vs image upload. Real API calls for observations and image processing.
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'

const route = useRoute()
const api = useApi()
const studyId = computed(() => route.params.studyId as string)

const study = ref<any>(null)
const plants = ref<any[]>([])
const containers = ref<any[]>([])
const recentObs = ref<any[]>([])
const loading = ref(true)

const mode = ref<'manual' | 'upload'>('manual')
const selectedPlant = ref('')
const selectedVariable = ref('')
const manualValue = ref('')
const saving = ref(false)

// Upload state
const selectedAlgorithm = ref('')
const processing = ref(false)
const processingStage = ref('')
const uploadProgress = ref(0)

onMounted(async () => {
  try {
    const [s, p, c] = await Promise.all([
      api.get<any>(`/studies/${studyId.value}`),
      api.get<any[]>(`/studies/${studyId.value}/observation-units`).catch(() => []),
      api.get<any[]>('/container-images').catch(() => []),
    ])
    study.value = s; plants.value = p; containers.value = c
    // Build recent observations from plants
    const obs: any[] = []
    for (const pl of p) {
      for (const o of (pl.observations || []).slice(-3)) {
        obs.push({ ...o, plantName: pl.name })
      }
    }
    recentObs.value = obs.slice(-15)
  } catch {}
  loading.value = false
})

const obsVars = computed(() => study.value?.observation_variables || study.value?.observationVariables || [])

async function saveObservation() {
  if (!selectedPlant.value || !selectedVariable.value || !manualValue.value) return
  saving.value = true
  try {
    const obs = await api.post<any>(`/studies/${studyId.value}/observations`, {
      observation_unit_id: selectedPlant.value,
      variable_id: selectedVariable.value,
      value: manualValue.value,
    })
    recentObs.value.unshift({ ...obs, plantName: plants.value.find(p => p.id === selectedPlant.value)?.name })
    manualValue.value = ''
  } catch {}
  saving.value = false
}

async function handleImageUpload(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files?.length || !selectedAlgorithm.value) return
  processing.value = true; processingStage.value = 'Загрузка файлов...'; uploadProgress.value = 0
  const formData = new FormData()
  for (const f of files) formData.append('files', f)
  formData.append('container_image_id', selectedAlgorithm.value)
  try {
    processingStage.value = 'Создание Kubernetes Job...'
    uploadProgress.value = 30
    await api.upload(`/studies/${studyId.value}/process-images`, formData)
    processingStage.value = 'Обработка запущена'
    uploadProgress.value = 100
  } catch { processingStage.value = 'Ошибка' }
  setTimeout(() => { processing.value = false; uploadProgress.value = 0 }, 3000)
}
</script>

<template>
  <div v-if="study" class="space-y-6 fade-in">
    <div>
      <router-link :to="`/experiments/${studyId}`" class="text-xs text-(--color-accent-green) hover:underline mb-2 inline-flex items-center gap-1">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
        {{ study.name }}
      </router-link>
      <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary) mt-2">Сбор данных</h1>
      <p class="text-sm text-(--color-text-secondary) mt-1">Ручной ввод наблюдений или загрузка изображений для автоматической обработки</p>
    </div>

    <div class="flex bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-1 max-w-md">
      <button @click="mode = 'manual'" :class="['flex-1 py-2.5 px-4 rounded-lg text-sm transition-all flex items-center justify-center gap-2', mode === 'manual' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        Ручной ввод
      </button>
      <button @click="mode = 'upload'" :class="['flex-1 py-2.5 px-4 rounded-lg text-sm transition-all flex items-center justify-center gap-2', mode === 'upload' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
        Загрузка изображений
      </button>
    </div>

    <!-- Manual mode -->
    <div v-if="mode === 'manual'" class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div class="lg:col-span-1 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 space-y-4 h-fit">
        <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary)">Новое наблюдение</h3>
        <div>
          <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Растение</label>
          <select v-model="selectedPlant" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all">
            <option value="">Выберите растение...</option>
            <option v-for="p in plants" :key="p.id" :value="p.id">{{ p.name }} — {{ p.germplasm?.germplasmName || p.germplasm?.germplasm_name || '' }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Переменная</label>
          <select v-model="selectedVariable" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all">
            <option value="">Выберите переменную...</option>
            <option v-for="v in obsVars" :key="v.id" :value="v.id">{{ v.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Значение</label>
          <input v-model="manualValue" type="text" placeholder="Введите значение" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
        </div>
        <button @click="saveObservation" :disabled="!selectedPlant || !selectedVariable || !manualValue || saving" class="w-full py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30">
          {{ saving ? 'Сохранение...' : 'Сохранить наблюдение' }}
        </button>
      </div>
      <div class="lg:col-span-2 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div class="px-5 py-4 border-b border-(--color-border-subtle)"><h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary)">Последние наблюдения</h3></div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-(--color-border-subtle)">
              <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Растение</th>
              <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Переменная</th>
              <th class="px-5 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Значение</th>
              <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Наблюдатель</th>
              <th class="px-5 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Дата</th>
            </tr></thead>
            <tbody class="divide-y divide-(--color-border-subtle)">
              <tr v-for="obs in recentObs" :key="obs.id" class="hover:bg-(--color-bg-hover) transition-colors">
                <td class="px-5 py-2.5 text-(--color-text-primary) text-xs font-medium">{{ obs.plantName || obs.plant_name }}</td>
                <td class="px-5 py-2.5 text-(--color-text-secondary) text-xs">{{ obs.variableName || obs.variable_name }}</td>
                <td class="px-5 py-2.5 text-right font-mono text-xs text-(--color-accent-green)">{{ obs.value }}</td>
                <td class="px-5 py-2.5 text-(--color-text-muted) text-xs"><span :class="(obs.collector || '').startsWith('auto') ? 'text-(--color-accent-sky)' : ''">{{ obs.collector }}</span></td>
                <td class="px-5 py-2.5 text-right text-(--color-text-muted) text-xs">{{ (obs.observationTimeStamp || obs.observation_timestamp || '').split('T')[0] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="recentObs.length === 0" class="px-5 py-8 text-center text-(--color-text-muted) text-sm">Нет наблюдений</div>
      </div>
    </div>

    <!-- Upload mode -->
    <div v-if="mode === 'upload'" class="space-y-5">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Загрузка изображений</h3>
          <label class="block border-2 border-dashed border-(--color-border-default) rounded-xl p-8 text-center hover:border-(--color-accent-green)/30 transition-colors cursor-pointer">
            <input type="file" multiple accept="image/*" class="hidden" @change="handleImageUpload" :disabled="!selectedAlgorithm" />
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="mx-auto text-(--color-text-muted) mb-3" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
            <p class="text-sm text-(--color-text-secondary)">Перетащите изображения сюда</p>
            <p class="text-xs text-(--color-text-muted) mt-1">JPG, PNG, TIFF. До 100 файлов.</p>
          </label>
        </div>
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Алгоритм обработки</h3>
          <div class="space-y-2">
            <label v-for="ci in containers" :key="ci.id" :class="['block p-4 rounded-lg border cursor-pointer transition-all', selectedAlgorithm === ci.id ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
              <input type="radio" v-model="selectedAlgorithm" :value="ci.id" class="hidden" />
              <div class="flex items-start justify-between"><div><p class="text-sm font-medium text-(--color-text-primary)">{{ ci.name }}</p><p class="text-xs text-(--color-text-muted) mt-0.5">{{ ci.description }}</p></div><span class="text-[10px] font-mono text-(--color-text-muted) bg-(--color-bg-surface) px-2 py-0.5 rounded">{{ ci.tag }}</span></div>
            </label>
          </div>
          <p v-if="containers.length === 0" class="text-center py-4 text-sm text-(--color-text-muted)">Нет зарегистрированных образов</p>
        </div>
      </div>

      <div v-if="processing" class="bg-(--color-bg-surface) border border-(--color-accent-green)/20 rounded-xl p-5 glow-green">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <svg class="animate-spin w-4 h-4 text-(--color-accent-green)" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
            <span class="text-sm font-medium text-(--color-accent-green)">{{ processingStage }}</span>
          </div>
          <span class="text-sm font-mono text-(--color-text-primary)">{{ Math.round(uploadProgress) }}%</span>
        </div>
        <div class="w-full h-2 bg-(--color-bg-base) rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) rounded-full transition-all duration-300" :style="{ width: `${Math.min(uploadProgress, 100)}%` }"></div>
        </div>
        <div class="mt-3 flex gap-4 text-xs text-(--color-text-muted)"><span>Namespace: phenoplant</span></div>
      </div>
    </div>
  </div>
</template>
