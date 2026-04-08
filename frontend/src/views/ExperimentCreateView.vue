<!--
  4-step wizard: Info → Variables → Plants → Review
  Program comes from useProgram (sidebar selector), no separate step needed.
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useProgram } from '@/composables/useProgram'

const router = useRouter()
const api = useApi()
const { currentProgram } = useProgram()

const currentStep = ref(0)
const steps = [
  { id: 'info', label: 'Информация', desc: 'Название и тип' },
  { id: 'variables', label: 'Переменные', desc: 'Что измеряем' },
  { id: 'plants', label: 'Растения', desc: 'Объекты наблюдения' },
  { id: 'review', label: 'Обзор', desc: 'Запуск эксперимента' },
]

// Data from API
const variables = ref<any[]>([])
const germplasms = ref<any[]>([])
const chambers = ref<any[]>([])

onMounted(async () => {
  const [v, g, c] = await Promise.all([
    api.get<any[]>('/variables').catch(() => []),
    api.get<any[]>('/germplasms').catch(() => []),
    api.get<any[]>('/climate-chambers').catch(() => []),
  ])
  variables.value = v
  germplasms.value = g
  chambers.value = c
})

// Step 1: Info
const expName = ref('')
const expDescription = ref('')
const expType = ref('phenotyping')
const expStartDate = ref('')
const expEndDate = ref('')
const selectedChamber = ref('')
const studyTypes = [
  { value: 'phenotyping', label: 'Фенотипирование', icon: '🌿' },
  { value: 'breeding', label: 'Селекция', icon: '🧬' },
  { value: 'stress', label: 'Стресс-тестирование', icon: '🔥' },
  { value: 'genotyping', label: 'Генотипирование', icon: '🧪' },
]

// Step 2: Variables
const selectedVars = ref<string[]>([])
const varSearch = ref('')
function toggleVar(id: string) {
  const idx = selectedVars.value.indexOf(id)
  if (idx >= 0) selectedVars.value.splice(idx, 1)
  else selectedVars.value.push(id)
}

// Step 3: Plants
const plantMode = ref<'manual' | 'csv'>('manual')
const manualPlants = ref([{ name: '', germplasmId: '', position: '', treatment: 'Контроль' }])
function addPlantRow() { manualPlants.value.push({ name: '', germplasmId: '', position: '', treatment: 'Контроль' }) }
function removePlantRow(i: number) { manualPlants.value.splice(i, 1) }

// Navigation
const canNext = computed(() => {
  switch (currentStep.value) {
    case 0: return expName.value.trim() && expType.value
    case 1: return selectedVars.value.length > 0
    case 2: return true
    default: return true
  }
})

function next() { if (currentStep.value < steps.length - 1) currentStep.value++ }
function prev() { if (currentStep.value > 0) currentStep.value-- }

const submitting = ref(false)
async function create() {
  submitting.value = true
  try {
    const plants = manualPlants.value.filter(p => p.name).map(p => ({
      name: p.name,
      germplasm_id: p.germplasmId,
      position: p.position,
      treatment: p.treatment,
    }))
    const body: any = {
      name: expName.value,
      description: expDescription.value,
      study_type: expType.value,
      trial_id: '',
      start_date: expStartDate.value || undefined,
      end_date: expEndDate.value || undefined,
      climate_chamber_id: selectedChamber.value || undefined,
      observation_variable_ids: selectedVars.value,
      program_id: currentProgram.value?.id || '',
      plants,
    }
    await api.post('/studies', body)
    router.push('/experiments')
  } catch {}
  submitting.value = false
}

const filteredVariables = computed(() => {
  if (!varSearch.value) return variables.value
  const q = varSearch.value.toLowerCase()
  return variables.value.filter((v: any) => (v.name || '').toLowerCase().includes(q) || (v.co_term_id || v.coTermId || '').toLowerCase().includes(q) || (v.trait?.traitName || v.trait?.trait_name || '').toLowerCase().includes(q))
})
const selectedVarObjects = computed(() => variables.value.filter(v => selectedVars.value.includes(v.id)))
const selectedChamberObj = computed(() => chambers.value.find(c => c.id === selectedChamber.value))
</script>

<template>
  <div class="fade-in">
    <!-- Header -->
    <div class="mb-8">
      <router-link to="/experiments" class="text-xs text-(--color-accent-green) hover:underline mb-3 inline-flex items-center gap-1">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
        Эксперименты
      </router-link>
      <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary) mt-2">Создание эксперимента</h1>
      <p class="text-sm text-(--color-text-secondary) mt-1">
        Программа: <span class="text-(--color-accent-green) font-medium">{{ currentProgram?.name || '—' }}</span>
      </p>
    </div>

    <div class="flex gap-6">
      <!-- Sidebar stepper -->
      <div class="w-56 flex-shrink-0">
        <div class="sticky top-20 space-y-1">
          <button
            v-for="(step, i) in steps" :key="step.id"
            @click="i <= currentStep ? (currentStep = i) : null"
            :class="['w-full flex items-start gap-3 px-3 py-3 rounded-lg text-left transition-all',
              i === currentStep ? 'bg-(--color-bg-surface) border border-(--color-accent-green)/30'
              : i < currentStep ? 'hover:bg-(--color-bg-surface) cursor-pointer'
              : 'opacity-40 cursor-default']"
          >
            <div :class="['w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 transition-all border',
              i === currentStep ? 'bg-(--color-accent-green) text-(--color-text-inverse) border-(--color-accent-green)'
              : i < currentStep ? 'bg-(--color-accent-green)/20 text-(--color-accent-green) border-(--color-accent-green)/30'
              : 'bg-(--color-bg-elevated) text-(--color-text-muted) border-(--color-border-subtle)']"
            >
              <svg v-if="i < currentStep" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <div>
              <p :class="['text-sm font-medium', i === currentStep ? 'text-(--color-text-primary)' : i < currentStep ? 'text-(--color-text-secondary)' : 'text-(--color-text-muted)']">{{ step.label }}</p>
              <p class="text-[10px] text-(--color-text-muted) mt-0.5">{{ step.desc }}</p>
            </div>
          </button>
        </div>
      </div>

      <!-- Content area -->
      <div class="flex-1 min-w-0">
        <!-- Step 1: Info -->
        <div v-if="currentStep === 0" class="space-y-5 slide-left">
          <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-6">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-1">Основная информация</h2>
            <p class="text-xs text-(--color-text-muted) mb-6">Укажите название и сроки проведения эксперимента</p>
            <div class="space-y-5">
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название эксперимента <span class="text-(--color-accent-rose)">*</span></label>
                <input v-model="expName" type="text" placeholder="Например: Оценка засухоустойчивости яровой пшеницы 2025" class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 focus:ring-1 focus:ring-(--color-accent-green)/20 transition-all" />
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Описание</label>
                <textarea v-model="expDescription" rows="3" placeholder="Краткое описание целей и методологии" class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 focus:ring-1 focus:ring-(--color-accent-green)/20 transition-all resize-none"></textarea>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Дата начала</label>
                  <input v-model="expStartDate" type="date" class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                </div>
                <div>
                  <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Дата окончания</label>
                  <input v-model="expEndDate" type="date" class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                </div>
              </div>
              <div v-if="chambers.length">
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Климатическая камера</label>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <button v-for="cc in chambers" :key="cc.id" @click="selectedChamber = selectedChamber === cc.id ? '' : cc.id"
                    :class="['p-4 rounded-lg border text-left transition-all',
                      selectedChamber === cc.id ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']"
                  >
                    <p class="text-sm font-medium text-(--color-text-primary)">{{ cc.name }}</p>
                    <p class="text-xs text-(--color-text-muted) mt-1">{{ (cc.sensors || []).length }} датчиков</p>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Variables -->
        <div v-if="currentStep === 1" class="space-y-5 slide-left">
          <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-6">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-1">Переменные наблюдения</h2>
            <p class="text-xs text-(--color-text-muted) mb-4">Выберите из каталога CropOntology переменные, которые будут измеряться</p>
            <!-- Search + top nav -->
            <div class="flex items-center gap-3 mb-4">
              <div class="flex-1 relative">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="absolute left-3 top-1/2 -translate-y-1/2 text-(--color-text-muted)"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input v-model="varSearch" type="text" placeholder="Поиск переменных..." class="w-full pl-9 pr-3 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-xs text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
              </div>
              <button v-if="currentStep < steps.length - 1" @click="next" :disabled="!canNext" class="px-5 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2">
                Далее
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9,6 15,12 9,18"/></svg>
              </button>
            </div>
            <div class="space-y-2">
              <button v-for="ov in filteredVariables" :key="ov.id" @click="toggleVar(ov.id)"
                :class="['w-full p-4 rounded-xl border text-left transition-all',
                  selectedVars.includes(ov.id) ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']"
              >
                <div class="flex items-center gap-3">
                  <div :class="['w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0', selectedVars.includes(ov.id) ? 'border-(--color-accent-green) bg-(--color-accent-green)' : 'border-(--color-text-muted)']">
                    <svg v-if="selectedVars.includes(ov.id)" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" class="text-(--color-text-inverse)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <h4 class="text-sm font-medium text-(--color-text-primary)">{{ ov.name }}</h4>
                      <span class="text-[10px] font-mono text-(--color-text-muted)">{{ ov.co_term_id || ov.coTermId }}</span>
                    </div>
                    <div class="flex gap-4 mt-1 text-xs text-(--color-text-muted)">
                      <span>{{ ov.trait?.traitName || ov.trait?.trait_name || '' }}</span>
                      <span>&middot;</span>
                      <span>{{ ov.method?.methodName || ov.method?.method_name || '' }}</span>
                      <span>&middot;</span>
                      <span>{{ ov.scale?.scaleName || ov.scale?.scale_name || '' }}{{ (ov.scale?.units) ? ' (' + ov.scale.units + ')' : '' }}</span>
                    </div>
                  </div>
                </div>
              </button>
              <div v-if="variables.length === 0" class="text-center py-8 text-sm text-(--color-text-muted)">Нет доступных переменных</div>
            </div>
            <p class="text-xs text-(--color-text-muted) mt-4">Выбрано: <span class="text-(--color-accent-green) font-semibold">{{ selectedVars.length }}</span> переменных</p>
          </div>
        </div>

        <!-- Step 3: Plants -->
        <div v-if="currentStep === 2" class="space-y-5 slide-left">
          <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-6">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-1">Регистрация растений</h2>
            <p class="text-xs text-(--color-text-muted) mb-6">Добавьте единицы наблюдения вручную или импортируйте из CSV</p>

            <div class="flex bg-(--color-bg-base) rounded-lg p-1 max-w-xs mb-6">
              <button @click="plantMode = 'manual'" :class="['flex-1 py-2 px-3 rounded-md text-sm transition-all', plantMode === 'manual' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Ручной ввод</button>
              <button @click="plantMode = 'csv'" :class="['flex-1 py-2 px-3 rounded-md text-sm transition-all', plantMode === 'csv' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Импорт CSV</button>
            </div>

            <div v-if="plantMode === 'manual'" class="space-y-3">
              <div class="grid grid-cols-[1fr_1fr_6rem_7rem_32px] gap-3 text-[10px] uppercase tracking-wider text-(--color-text-muted) px-1">
                <span>Название</span><span>Образец (Germplasm)</span><span>Позиция</span><span>Обработка</span><span></span>
              </div>
              <div v-for="(plant, i) in manualPlants" :key="i" class="grid grid-cols-[1fr_1fr_6rem_7rem_32px] gap-3 items-center">
                <input v-model="plant.name" type="text" placeholder="NSK-67/R1-P01" class="px-3 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-xs text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                <select v-model="plant.germplasmId" class="px-3 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-xs text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all">
                  <option value="">Выбрать...</option>
                  <option v-for="g in germplasms" :key="g.id" :value="g.id">{{ g.germplasmName || g.germplasm_name }}</option>
                </select>
                <input v-model="plant.position" type="text" placeholder="R1-P01" class="w-24 px-3 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-xs text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                <input v-model="plant.treatment" type="text" placeholder="Контроль" class="w-28 px-3 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-xs text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                <button @click="removePlantRow(i)" :disabled="manualPlants.length <= 1" class="w-8 h-8 rounded-lg flex items-center justify-center text-(--color-text-muted) hover:text-(--color-accent-rose) hover:bg-(--color-accent-rose)/10 transition-colors disabled:opacity-20">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
              <button @click="addPlantRow" class="w-full py-2.5 rounded-lg border border-dashed border-(--color-border-default) text-xs text-(--color-text-muted) hover:text-(--color-accent-green) hover:border-(--color-accent-green)/30 transition-all flex items-center justify-center gap-1.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Добавить строку
              </button>
            </div>

            <div v-if="plantMode === 'csv'">
              <div class="border-2 border-dashed border-(--color-border-default) rounded-xl p-10 text-center hover:border-(--color-accent-green)/30 transition-colors cursor-pointer">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="mx-auto text-(--color-text-muted) mb-3" stroke-linecap="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p class="text-sm text-(--color-text-secondary)">Перетащите CSV файл сюда</p>
                <p class="text-xs text-(--color-text-muted) mt-1">или нажмите для выбора файла</p>
                <p class="text-[10px] text-(--color-text-muted) mt-3 font-mono">Формат: name, germplasm_id, position, treatment</p>
              </div>
            </div>
            <p class="text-xs text-(--color-text-muted) mt-4">Этот шаг можно пропустить и добавить растения позже.</p>
          </div>
        </div>

        <!-- Step 4: Review -->
        <div v-if="currentStep === 3" class="space-y-5 slide-left">
          <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-6">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-1">Обзор и запуск</h2>
            <p class="text-xs text-(--color-text-muted) mb-6">Проверьте настройки перед созданием эксперимента</p>
            <div class="space-y-4">
              <div class="bg-(--color-bg-base) rounded-xl p-5 border border-(--color-border-subtle)">
                <div class="flex items-center justify-between mb-3">
                  <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Основная информация</span>
                  <button @click="currentStep = 0" class="text-[10px] text-(--color-accent-green) hover:underline">Изменить</button>
                </div>
                <h3 class="text-base font-medium text-(--color-text-primary)">{{ expName }}</h3>
                <p v-if="expDescription" class="text-xs text-(--color-text-muted) mt-1">{{ expDescription }}</p>
                <div class="flex flex-wrap gap-3 mt-3 text-xs text-(--color-text-secondary)">

                  <span v-if="expStartDate">{{ expStartDate }}</span>
                  <span v-if="expStartDate && expEndDate"> — </span>
                  <span v-if="expEndDate">{{ expEndDate }}</span>
                </div>
                <p v-if="selectedChamberObj" class="text-xs text-(--color-text-muted) mt-2">Камера: {{ selectedChamberObj.name }}</p>
              </div>

              <div class="bg-(--color-bg-base) rounded-xl p-5 border border-(--color-border-subtle)">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Программа</span>
                </div>
                <p class="text-sm text-(--color-text-primary)">{{ currentProgram?.name || '—' }}</p>
              </div>

              <div class="bg-(--color-bg-base) rounded-xl p-5 border border-(--color-border-subtle)">
                <div class="flex items-center justify-between mb-3">
                  <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Переменные ({{ selectedVars.length }})</span>
                  <button @click="currentStep = 1" class="text-[10px] text-(--color-accent-green) hover:underline">Изменить</button>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span v-for="ov in selectedVarObjects" :key="ov.id" class="px-2.5 py-1 rounded-lg text-xs bg-(--color-bg-surface) text-(--color-text-secondary) border border-(--color-border-subtle)">
                    {{ ov.trait?.traitName || ov.trait?.trait_name || ov.name }}
                  </span>
                </div>
              </div>

              <div class="bg-(--color-bg-base) rounded-xl p-5 border border-(--color-border-subtle)">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Растения</span>
                  <button @click="currentStep = 2" class="text-[10px] text-(--color-accent-green) hover:underline">Изменить</button>
                </div>
                <p class="text-sm text-(--color-text-secondary)">{{ manualPlants.filter(p => p.name).length }} растений зарегистрировано</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Navigation buttons -->
        <div class="flex items-center justify-between mt-6 pt-6 border-t border-(--color-border-subtle)">
          <button v-if="currentStep > 0" @click="prev" class="px-5 py-2.5 rounded-lg text-sm border border-(--color-border-default) text-(--color-text-secondary) hover:bg-(--color-bg-hover) transition-all flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
            Назад
          </button>
          <div v-else></div>
          <div class="flex items-center gap-3">
            <span class="text-xs text-(--color-text-muted)">Шаг {{ currentStep + 1 }} из {{ steps.length }}</span>
            <button v-if="currentStep < steps.length - 1" @click="next" :disabled="!canNext" class="px-5 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2">
              Далее
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9,6 15,12 9,18"/></svg>
            </button>
            <button v-else @click="create" :disabled="submitting" class="px-6 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 active:scale-[0.98] transition-all flex items-center gap-2 glow-green disabled:opacity-50">
              <svg v-if="submitting" class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
              {{ submitting ? 'Создание...' : 'Создать эксперимент' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
