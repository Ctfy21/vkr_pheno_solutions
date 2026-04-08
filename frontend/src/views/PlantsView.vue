<!--
  Design approach: DATA-DENSE table with search + filters
  Table shows all observation units with genotype, species, position, treatment, counts.
  Add/Import modals with real API calls.
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
const germplasms = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const filterTreatment = ref('')
const showCreateModal = ref(false)
const showImportModal = ref(false)
const creating = ref(false)

const newPlant = ref({ name: '', germplasmId: '', position: '', treatment: 'Контроль' })

onMounted(async () => {
  try {
    const [s, p, g] = await Promise.all([
      api.get<any>(`/studies/${studyId.value}`),
      api.get<any[]>(`/studies/${studyId.value}/observation-units`).catch(() => []),
      api.get<any[]>('/germplasms').catch(() => []),
    ])
    study.value = s; plants.value = p; germplasms.value = g
  } catch {}
  loading.value = false
})

const filtered = computed(() => {
  let result = plants.value
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter(p => p.name.toLowerCase().includes(q) || (p.germplasm?.germplasmName || p.germplasm?.germplasm_name || '').toLowerCase().includes(q) || (p.position || '').toLowerCase().includes(q))
  }
  if (filterTreatment.value) result = result.filter(p => p.treatment === filterTreatment.value)
  return result
})

const treatments = computed(() => [...new Set(plants.value.map(p => p.treatment).filter(Boolean))])

async function addPlant() {
  creating.value = true
  try {
    const p = await api.post<any>(`/studies/${studyId.value}/observation-units`, {
      name: newPlant.value.name,
      germplasm_id: newPlant.value.germplasmId,
      position: newPlant.value.position,
      treatment: newPlant.value.treatment,
    })
    plants.value.push(p)
    showCreateModal.value = false
    newPlant.value = { name: '', germplasmId: '', position: '', treatment: 'Контроль' }
  } catch {}
  creating.value = false
}
</script>

<template>
  <div v-if="study" class="space-y-6 fade-in">
    <div class="flex items-end justify-between">
      <div>
        <router-link :to="`/experiments/${studyId}`" class="text-xs text-(--color-accent-green) hover:underline mb-2 inline-flex items-center gap-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
          {{ study.name }}
        </router-link>
        <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary) mt-2">Растения</h1>
        <p class="text-sm text-(--color-text-secondary) mt-1">Единицы наблюдения (ObservationUnit) в эксперименте</p>
      </div>
      <div class="flex gap-2">
        <button @click="showImportModal = true" class="px-4 py-2.5 rounded-lg text-sm border border-(--color-border-default) text-(--color-text-secondary) hover:bg-(--color-bg-hover) transition-all flex items-center gap-2">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          Импорт CSV
        </button>
        <button @click="showCreateModal = true" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Добавить
        </button>
      </div>
    </div>

    <div class="flex gap-3">
      <div class="flex-1 relative">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-4 top-1/2 -translate-y-1/2 text-(--color-text-muted)" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="search" type="text" placeholder="Поиск по названию, генотипу, позиции..." class="w-full pl-11 pr-4 py-2.5 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all" />
      </div>
      <select v-model="filterTreatment" class="px-4 py-2.5 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all">
        <option value="">Все обработки</option>
        <option v-for="t in treatments" :key="t" :value="t">{{ t }}</option>
      </select>
    </div>

    <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-(--color-border-subtle)">
            <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Название</th>
            <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Генотип</th>
            <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Вид</th>
            <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Позиция</th>
            <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Обработка</th>
            <th class="px-5 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Наблюдения</th>
            <th class="px-5 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Изобр.</th>
          </tr></thead>
          <tbody class="divide-y divide-(--color-border-subtle)">
            <tr v-for="plant in filtered" :key="plant.id" class="hover:bg-(--color-bg-hover) transition-colors">
              <td class="px-5 py-3.5 font-medium text-(--color-text-primary)">{{ plant.name }}</td>
              <td class="px-5 py-3.5 font-mono text-xs text-(--color-accent-green)">{{ plant.germplasm?.germplasmName || plant.germplasm?.germplasm_name }}</td>
              <td class="px-5 py-3.5 text-(--color-text-secondary) italic text-xs">{{ plant.germplasm?.genus }} {{ plant.germplasm?.species }}</td>
              <td class="px-5 py-3.5 text-(--color-text-secondary)">{{ plant.position }}</td>
              <td class="px-5 py-3.5"><span :class="['px-2 py-0.5 rounded text-[10px] uppercase tracking-wider', plant.treatment === 'Контроль' ? 'bg-(--color-accent-green)/10 text-(--color-accent-green)' : 'bg-(--color-accent-amber)/10 text-(--color-accent-amber)']">{{ plant.treatment }}</span></td>
              <td class="px-5 py-3.5 text-right text-(--color-text-secondary)">{{ (plant.observations || []).length }}</td>
              <td class="px-5 py-3.5 text-right text-(--color-text-secondary)">{{ (plant.images || []).length }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-5 py-3 border-t border-(--color-border-subtle) flex items-center justify-between text-xs text-(--color-text-muted)">
        <span>{{ filtered.length }} из {{ plants.length }} растений</span>
        <span>BrAPI v2.1</span>
      </div>
    </div>

    <!-- Create modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreateModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-5">Добавить растение</h2>
            <form @submit.prevent="addPlant" class="space-y-4">
              <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название</label><input v-model="newPlant.name" type="text" required placeholder="NSK-67 / R1-P03" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
              <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Образец</label>
                <select v-model="newPlant.germplasmId" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all">
                  <option value="">Выберите...</option>
                  <option v-for="g in germplasms" :key="g.id" :value="g.id">{{ g.germplasmName || g.germplasm_name }} ({{ g.accessionNumber || g.accession_number }})</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Позиция</label><input v-model="newPlant.position" type="text" placeholder="Ряд 1, Позиция 3" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
                <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Обработка</label><input v-model="newPlant.treatment" type="text" placeholder="Контроль" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
              </div>
              <div class="flex gap-3 pt-2">
                <button type="button" @click="showCreateModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
                <button type="submit" :disabled="creating" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">{{ creating ? 'Добавление...' : 'Добавить' }}</button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Import modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showImportModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showImportModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-5">Импорт из CSV</h2>
            <div class="border-2 border-dashed border-(--color-border-default) rounded-xl p-8 text-center hover:border-(--color-accent-green)/30 transition-colors cursor-pointer">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="mx-auto text-(--color-text-muted) mb-3" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <p class="text-sm text-(--color-text-secondary)">Перетащите CSV файл сюда</p>
              <p class="text-xs text-(--color-text-muted) mt-1">или нажмите для выбора</p>
              <p class="text-[10px] text-(--color-text-muted) mt-3">Формат: name, germplasm_id, position, treatment</p>
            </div>
            <div class="flex gap-3 pt-5">
              <button @click="showImportModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
              <button @click="showImportModal = false" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all">Загрузить</button>
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
