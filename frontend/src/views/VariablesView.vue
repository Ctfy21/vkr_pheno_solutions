<!--
  Variables view with Trait/Method/Scale population and delete button
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'

const api = useApi()
const variables = ref<any[]>([])
const traits = ref<any[]>([])
const methods = ref<any[]>([])
const scales = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const showCreateModal = ref(false)
const createStep = ref(0)
const creating = ref(false)
const deleting = ref<string | null>(null)

onMounted(async () => {
  try {
    const [v, t, m, s] = await Promise.all([
      api.get<any[]>('/variables'),
      api.get<any[]>('/traits').catch(() => []),
      api.get<any[]>('/methods').catch(() => []),
      api.get<any[]>('/scales').catch(() => []),
    ])
    variables.value = v; traits.value = t; methods.value = m; scales.value = s
  } catch {}
  loading.value = false
})

const filtered = computed(() => {
  if (!search.value) return variables.value
  const q = search.value.toLowerCase()
  return variables.value.filter(ov =>
    ov.name.toLowerCase().includes(q) ||
    (ov.trait?.traitName || ov.trait?.trait_name || '').toLowerCase().includes(q) ||
    (ov.co_term_id || ov.coTermId || '').toLowerCase().includes(q)
  )
})

async function deleteVariable(id: string) {
  if (!confirm('Удалить переменную?')) return
  deleting.value = id
  try {
    await api.del('/variables/' + id)
    variables.value = variables.value.filter(v => v.id !== id)
  } catch {}
  deleting.value = null
}

function animDelay(i: number): string {
  return (i * 50) + 'ms'
}

// Create form state
const traitMode = ref<'select' | 'create'>('select')
const selectedTraitId = ref('')
const newTrait = ref({ name: '', description: '', traitClass: '', entity: '', attribute: '', coTermId: '' })
const methodMode = ref<'select' | 'create'>('select')
const selectedMethodId = ref('')
const newMethod = ref({ name: '', methodClass: '', description: '', formula: '', reference: '' })
const scaleMode = ref<'select' | 'create'>('select')
const selectedScaleId = ref('')
const newScale = ref({ name: '', dataType: '', units: '', decimalPlaces: 2 })

const traitClasses = [
  { value: 'morphological', label: 'Морфологический' },
  { value: 'physiological', label: 'Физиологический' },
  { value: 'biochemical', label: 'Биохимический' },
  { value: 'phenological', label: 'Фенологический' },
  { value: 'agronomic', label: 'Агрономический' },
]
const methodClasses = [
  { value: 'measurement', label: 'Измерение' },
  { value: 'counting', label: 'Подсчет' },
  { value: 'estimation', label: 'Оценка' },
  { value: 'computation', label: 'Вычисление' },
  { value: 'observation', label: 'Наблюдение' },
]
const dataTypes = [
  { value: 'numerical', label: 'Числовой' },
  { value: 'ordinal', label: 'Порядковый' },
  { value: 'nominal', label: 'Номинальный' },
  { value: 'date', label: 'Дата' },
  { value: 'text', label: 'Текст' },
]
const stepLabels = [
  { label: 'Признак', desc: 'Trait' },
  { label: 'Метод', desc: 'Method' },
  { label: 'Шкала', desc: 'Scale' },
  { label: 'Обзор', desc: 'Переменная' },
]

const canNext = computed(() => {
  switch (createStep.value) {
    case 0: return traitMode.value === 'select' ? !!selectedTraitId.value : !!(newTrait.value.name && newTrait.value.traitClass && newTrait.value.entity && newTrait.value.attribute)
    case 1: return methodMode.value === 'select' ? !!selectedMethodId.value : !!(newMethod.value.name && newMethod.value.methodClass && newMethod.value.description)
    case 2: return scaleMode.value === 'select' ? !!selectedScaleId.value : !!(newScale.value.name && newScale.value.dataType)
    default: return true
  }
})

const resolvedTrait = computed(() => traitMode.value === 'select' ? traits.value.find(t => t.id === selectedTraitId.value) : { traitName: newTrait.value.name, traitClass: newTrait.value.traitClass, entity: newTrait.value.entity, attribute: newTrait.value.attribute })
const resolvedMethod = computed(() => methodMode.value === 'select' ? methods.value.find(m => m.id === selectedMethodId.value) : { methodName: newMethod.value.name, methodClass: newMethod.value.methodClass })
const resolvedScale = computed(() => scaleMode.value === 'select' ? scales.value.find(s => s.id === selectedScaleId.value) : { scaleName: newScale.value.name, dataType: newScale.value.dataType, units: newScale.value.units })

function openCreate() {
  createStep.value = 0; traitMode.value = 'select'; methodMode.value = 'select'; scaleMode.value = 'select'
  selectedTraitId.value = ''; selectedMethodId.value = ''; selectedScaleId.value = ''
  newTrait.value = { name: '', description: '', traitClass: '', entity: '', attribute: '', coTermId: '' }
  newMethod.value = { name: '', methodClass: '', description: '', formula: '', reference: '' }
  newScale.value = { name: '', dataType: '', units: '', decimalPlaces: 2 }
  showCreateModal.value = true
}

async function submitVariable() {
  creating.value = true
  try {
    const body: any = {}
    if (traitMode.value === 'select') { body.trait_id = selectedTraitId.value } else {
      body.trait = { trait_name: newTrait.value.name, trait_description: newTrait.value.description, trait_class: newTrait.value.traitClass, entity: newTrait.value.entity, attribute: newTrait.value.attribute, co_term_id: newTrait.value.coTermId }
    }
    if (methodMode.value === 'select') { body.method_id = selectedMethodId.value } else {
      body.method = { method_name: newMethod.value.name, method_class: newMethod.value.methodClass, description: newMethod.value.description, formula: newMethod.value.formula, reference: newMethod.value.reference }
    }
    if (scaleMode.value === 'select') { body.scale_id = selectedScaleId.value } else {
      body.scale = { scale_name: newScale.value.name, data_type: newScale.value.dataType, units: newScale.value.units, decimal_places: newScale.value.decimalPlaces }
    }
    const v = await api.post<any>('/variables', body)
    variables.value.push(v)
    showCreateModal.value = false
  } catch {}
  creating.value = false
}

const traitClassColors: Record<string, string> = {
  morphological: 'bg-(--color-accent-green)/10 text-(--color-accent-green)',
  physiological: 'bg-(--color-accent-sky)/10 text-(--color-accent-sky)',
  biochemical: 'bg-(--color-accent-violet)/10 text-(--color-accent-violet)',
  phenological: 'bg-(--color-accent-amber)/10 text-(--color-accent-amber)',
  agronomic: 'bg-(--color-accent-rose)/10 text-(--color-accent-rose)',
}
const traitClassLabels: Record<string, string> = { morphological: 'Морфология', physiological: 'Физиология', biochemical: 'Биохимия', phenological: 'Фенология', agronomic: 'Агрономия' }
</script>

<template>
  <div class="space-y-6 fade-in">
    <div class="flex items-end justify-between">
      <div>
        <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">Переменные наблюдения</h1>
        <p class="text-sm text-(--color-text-secondary) mt-1">Каталог CropOntology: Признак + Метод + Шкала</p>
      </div>
      <button @click="openCreate" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Новая переменная
      </button>
    </div>

    <div class="relative">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-4 top-1/2 -translate-y-1/2 text-(--color-text-muted)" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="search" type="text" placeholder="Поиск по названию, признаку или CO идентификатору..." class="w-full pl-11 pr-4 py-3 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 focus:ring-1 focus:ring-(--color-accent-green)/20 transition-all" />
    </div>

    <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 animate-pulse">
        <div class="h-4 bg-(--color-bg-elevated) rounded w-1/3 mb-3"></div>
        <div class="grid grid-cols-3 gap-3 mt-4"><div v-for="j in 3" :key="j" class="h-16 bg-(--color-bg-base) rounded-lg"></div></div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="(ov, i) in filtered" :key="ov.id" class="slide-up bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 hover:border-(--color-border-default) transition-colors" :style="{ animationDelay: animDelay(i) }">
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="text-sm font-medium text-(--color-text-primary)">{{ ov.name }}</h3>
            <p class="text-xs font-mono text-(--color-text-muted) mt-0.5">{{ ov.co_term_id || ov.coTermId }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span :class="['px-2 py-0.5 rounded text-[10px] uppercase tracking-wider', traitClassColors[ov.trait?.traitClass || ov.trait?.trait_class] || '']"
            >{{ traitClassLabels[ov.trait?.traitClass || ov.trait?.trait_class] || ov.trait?.traitClass || ov.trait?.trait_class || '' }}</span>
            <button @click.stop="deleteVariable(ov.id)" :disabled="deleting === ov.id"
              class="p-1.5 rounded-lg text-(--color-text-muted) hover:text-(--color-accent-rose) hover:bg-(--color-accent-rose)/10 transition-all disabled:opacity-30"
              title="Удалить переменную">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/></svg>
            </button>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3 mt-4">
          <div class="bg-(--color-bg-base) rounded-lg p-3">
            <div class="flex items-center gap-1.5 mb-1.5"><div class="w-1.5 h-1.5 rounded-full bg-(--color-accent-green)"></div><span class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Признак</span></div>
            <p class="text-xs text-(--color-text-primary) font-medium">{{ ov.trait?.traitName || ov.trait?.trait_name || '—' }}</p>
            <p class="text-[10px] text-(--color-text-muted) mt-1">{{ ov.trait?.entity || '—' }} / {{ ov.trait?.attribute || '—' }}</p>
          </div>
          <div class="bg-(--color-bg-base) rounded-lg p-3">
            <div class="flex items-center gap-1.5 mb-1.5"><div class="w-1.5 h-1.5 rounded-full bg-(--color-accent-sky)"></div><span class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Метод</span></div>
            <p class="text-xs text-(--color-text-primary) font-medium">{{ ov.method?.methodName || ov.method?.method_name || '—' }}</p>
            <p class="text-[10px] text-(--color-text-muted) mt-1">{{ ov.method?.methodClass || ov.method?.method_class || '—' }}</p>
          </div>
          <div class="bg-(--color-bg-base) rounded-lg p-3">
            <div class="flex items-center gap-1.5 mb-1.5"><div class="w-1.5 h-1.5 rounded-full bg-(--color-accent-amber)"></div><span class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Шкала</span></div>
            <p class="text-xs text-(--color-text-primary) font-medium">{{ ov.scale?.scaleName || ov.scale?.scale_name || '—' }}</p>
            <p class="text-[10px] text-(--color-text-muted) mt-1">{{ ov.scale?.dataType || ov.scale?.data_type || '—' }}{{ ov.scale?.units ? ' (' + ov.scale.units + ')' : '' }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreateModal = false"></div>
          <div class="relative w-full max-w-2xl mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl slide-up max-h-[90vh] overflow-hidden flex flex-col">
            <div class="px-6 pt-5 pb-4 border-b border-(--color-border-subtle) flex-shrink-0">
              <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-4">Новая переменная наблюдения</h2>
              <div class="flex gap-2">
                <button v-for="(s, idx) in stepLabels" :key="s.label" @click="idx <= createStep ? (createStep = idx) : null"
                  :class="['flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all',
                    idx === createStep ? 'bg-(--color-bg-elevated) text-(--color-text-primary) border border-(--color-border-default)'
                    : idx < createStep ? 'text-(--color-accent-green) cursor-pointer hover:bg-(--color-bg-hover)'
                    : 'text-(--color-text-muted) cursor-default opacity-40']"
                >
                  <div :class="['w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold',
                    idx < createStep ? 'bg-(--color-accent-green) text-(--color-text-inverse)' : idx === createStep ? 'border-2 border-current' : 'border border-(--color-text-muted)']"
                  >
                    <svg v-if="idx < createStep" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                    <span v-else>{{ idx + 1 }}</span>
                  </div>
                  <span>{{ s.label }}</span>
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto p-6">
              <!-- Step 0: Trait -->
              <div v-if="createStep === 0" class="space-y-4">
                <div class="flex bg-(--color-bg-base) rounded-lg p-1 max-w-xs">
                  <button @click="traitMode = 'select'" :class="['flex-1 py-2 px-3 rounded-md text-xs transition-all', traitMode === 'select' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Выбрать</button>
                  <button @click="traitMode = 'create'" :class="['flex-1 py-2 px-3 rounded-md text-xs transition-all', traitMode === 'create' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Создать</button>
                </div>
                <div v-if="traitMode === 'select'" class="space-y-2">
                  <label v-for="t in traits" :key="t.id" :class="['block p-4 rounded-xl border cursor-pointer transition-all', selectedTraitId === t.id ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
                    <input type="radio" v-model="selectedTraitId" :value="t.id" class="hidden" />
                    <div class="flex items-center justify-between"><div><p class="text-sm font-medium text-(--color-text-primary)">{{ t.traitName || t.trait_name }}</p><p class="text-xs text-(--color-text-muted) mt-0.5">{{ t.entity }} / {{ t.attribute }}</p></div><span class="text-[10px] font-mono text-(--color-text-muted)">{{ t.coTermId || t.co_term_id }}</span></div>
                    <p class="text-xs text-(--color-text-muted) mt-1.5">{{ t.traitDescription || t.trait_description }}</p>
                  </label>
                </div>
                <div v-if="traitMode === 'create'" class="space-y-4">
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название <span class="text-(--color-accent-rose)">*</span></label><input v-model="newTrait.name" type="text" placeholder="Длина колоса" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Класс <span class="text-(--color-accent-rose)">*</span></label>
                    <div class="flex flex-wrap gap-2"><button v-for="tc in traitClasses" :key="tc.value" @click="newTrait.traitClass = tc.value" :class="['px-3 py-2 rounded-lg border text-xs transition-all', newTrait.traitClass === tc.value ? 'bg-(--color-accent-green)/10 border-(--color-accent-green)/30 text-(--color-accent-green)' : 'bg-(--color-bg-base) border-(--color-border-subtle) text-(--color-text-secondary) hover:border-(--color-border-default)']">{{ tc.label }}</button></div>
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Сущность <span class="text-(--color-accent-rose)">*</span></label><input v-model="newTrait.entity" type="text" placeholder="Колос" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                    <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Атрибут <span class="text-(--color-accent-rose)">*</span></label><input v-model="newTrait.attribute" type="text" placeholder="Длина" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                  </div>
                </div>
              </div>
              <!-- Step 1: Method -->
              <div v-if="createStep === 1" class="space-y-4">
                <div class="flex bg-(--color-bg-base) rounded-lg p-1 max-w-xs">
                  <button @click="methodMode = 'select'" :class="['flex-1 py-2 px-3 rounded-md text-xs transition-all', methodMode === 'select' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Выбрать</button>
                  <button @click="methodMode = 'create'" :class="['flex-1 py-2 px-3 rounded-md text-xs transition-all', methodMode === 'create' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Создать</button>
                </div>
                <div v-if="methodMode === 'select'" class="space-y-2">
                  <label v-for="m in methods" :key="m.id" :class="['block p-4 rounded-xl border cursor-pointer transition-all', selectedMethodId === m.id ? 'bg-(--color-accent-sky)/5 border-(--color-accent-sky)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
                    <input type="radio" v-model="selectedMethodId" :value="m.id" class="hidden" />
                    <div class="flex items-center justify-between"><p class="text-sm font-medium text-(--color-text-primary)">{{ m.methodName || m.method_name }}</p><span class="px-2 py-0.5 rounded text-[10px] bg-(--color-accent-sky)/10 text-(--color-accent-sky)">{{ m.methodClass || m.method_class }}</span></div>
                    <p class="text-xs text-(--color-text-muted) mt-1">{{ m.description }}</p>
                  </label>
                </div>
                <div v-if="methodMode === 'create'" class="space-y-4">
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название <span class="text-(--color-accent-rose)">*</span></label><input v-model="newMethod.name" type="text" placeholder="Анализ изображений CNN" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Класс <span class="text-(--color-accent-rose)">*</span></label>
                    <div class="flex flex-wrap gap-2"><button v-for="mc in methodClasses" :key="mc.value" @click="newMethod.methodClass = mc.value" :class="['px-3 py-2 rounded-lg border text-xs transition-all', newMethod.methodClass === mc.value ? 'bg-(--color-accent-sky)/10 border-(--color-accent-sky)/30 text-(--color-accent-sky)' : 'bg-(--color-bg-base) border-(--color-border-subtle) text-(--color-text-secondary) hover:border-(--color-border-default)']">{{ mc.label }}</button></div>
                  </div>
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Описание <span class="text-(--color-accent-rose)">*</span></label><textarea v-model="newMethod.description" rows="2" placeholder="Протокол" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-none"></textarea></div>
                </div>
              </div>
              <!-- Step 2: Scale -->
              <div v-if="createStep === 2" class="space-y-4">
                <div class="flex bg-(--color-bg-base) rounded-lg p-1 max-w-xs">
                  <button @click="scaleMode = 'select'" :class="['flex-1 py-2 px-3 rounded-md text-xs transition-all', scaleMode === 'select' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Выбрать</button>
                  <button @click="scaleMode = 'create'" :class="['flex-1 py-2 px-3 rounded-md text-xs transition-all', scaleMode === 'create' ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm' : 'text-(--color-text-muted)']">Создать</button>
                </div>
                <div v-if="scaleMode === 'select'" class="space-y-2">
                  <label v-for="s in scales" :key="s.id" :class="['block p-4 rounded-xl border cursor-pointer transition-all', selectedScaleId === s.id ? 'bg-(--color-accent-amber)/5 border-(--color-accent-amber)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
                    <input type="radio" v-model="selectedScaleId" :value="s.id" class="hidden" />
                    <div class="flex items-center justify-between"><p class="text-sm font-medium text-(--color-text-primary)">{{ s.scaleName || s.scale_name }}</p><div class="flex gap-2 text-[10px]"><span class="px-2 py-0.5 rounded bg-(--color-accent-amber)/10 text-(--color-accent-amber)">{{ s.dataType || s.data_type }}</span><span v-if="s.units" class="px-2 py-0.5 rounded bg-(--color-bg-elevated) text-(--color-text-secondary)">{{ s.units }}</span></div></div>
                  </label>
                </div>
                <div v-if="scaleMode === 'create'" class="space-y-4">
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название <span class="text-(--color-accent-rose)">*</span></label><input v-model="newScale.name" type="text" placeholder="Миллиметры" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                  <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Тип <span class="text-(--color-accent-rose)">*</span></label>
                    <div class="flex flex-wrap gap-2"><button v-for="dt in dataTypes" :key="dt.value" @click="newScale.dataType = dt.value" :class="['px-3 py-2 rounded-lg border text-xs transition-all', newScale.dataType === dt.value ? 'bg-(--color-accent-amber)/10 border-(--color-accent-amber)/30 text-(--color-accent-amber)' : 'bg-(--color-bg-base) border-(--color-border-subtle) text-(--color-text-secondary) hover:border-(--color-border-default)']">{{ dt.label }}</button></div>
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Единица</label><input v-model="newScale.units" type="text" placeholder="мм" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                    <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Десятичных</label><input v-model.number="newScale.decimalPlaces" type="number" min="0" max="10" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                  </div>
                </div>
              </div>
              <!-- Step 3: Review -->
              <div v-if="createStep === 3" class="space-y-4">
                <div class="bg-(--color-bg-base) rounded-xl p-5 border border-(--color-accent-green)/20">
                  <div class="grid grid-cols-3 gap-4">
                    <div><div class="flex items-center gap-1.5 mb-2"><div class="w-2 h-2 rounded-full bg-(--color-accent-green)"></div><span class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Признак</span></div><p class="text-sm font-medium text-(--color-text-primary)">{{ resolvedTrait?.traitName || resolvedTrait?.trait_name }}</p></div>
                    <div><div class="flex items-center gap-1.5 mb-2"><div class="w-2 h-2 rounded-full bg-(--color-accent-sky)"></div><span class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Метод</span></div><p class="text-sm font-medium text-(--color-text-primary)">{{ resolvedMethod?.methodName || resolvedMethod?.method_name }}</p></div>
                    <div><div class="flex items-center gap-1.5 mb-2"><div class="w-2 h-2 rounded-full bg-(--color-accent-amber)"></div><span class="text-[9px] uppercase tracking-widest text-(--color-text-muted)">Шкала</span></div><p class="text-sm font-medium text-(--color-text-primary)">{{ resolvedScale?.scaleName || resolvedScale?.scale_name }}</p></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="px-6 py-4 border-t border-(--color-border-subtle) flex items-center justify-between flex-shrink-0">
              <button v-if="createStep > 0" @click="createStep--" class="px-4 py-2 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Назад</button>
              <button v-else @click="showCreateModal = false" class="px-4 py-2 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
              <button v-if="createStep < 3" @click="createStep++" :disabled="!canNext" class="px-5 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed">Далее</button>
              <button v-else @click="submitVariable" :disabled="creating" class="px-5 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">{{ creating ? 'Создание...' : 'Создать переменную' }}</button>
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
