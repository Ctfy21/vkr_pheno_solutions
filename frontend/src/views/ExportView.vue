<!--
  Design approach: GUIDED (2-column: settings left, summary right)
  Left: format selector, experiments, variables, dates. Right: sticky summary + download.
  Real API call: POST /api/export (XLSX, PDF, CSV, BrAPI-style JSON)
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'

const api = useApi()
const studies = ref<any[]>([])
const variables = ref<any[]>([])
const loading = ref(true)

type Format = 'xlsx' | 'pdf' | 'csv' | 'json'
const formats: { id: Format; title: string; hint: string; tags: string[] }[] = [
  { id: 'xlsx', title: 'Excel (XLSX)', hint: 'Результаты, статистика, динамика, графики', tags: ['Excel', 'LibreOffice', 'R', 'Python'] },
  { id: 'pdf', title: 'PDF-отчёт', hint: 'Сводка, графики, аннотированные снимки', tags: ['Печать', 'Отчётность'] },
  { id: 'csv', title: 'CSV', hint: 'Плоская таблица для R, Python, Excel', tags: ['R', 'Python', 'SPSS'] },
  { id: 'json', title: 'BrAPI JSON', hint: 'Наблюдения с CropOntology ID', tags: ['BreedBase', 'BMS', 'MIAPPE'] },
]
const format = ref<Format>('xlsx')
const formatInfo = computed(() => formats.find(f => f.id === format.value)!)
const selectedStudies = ref<string[]>([])
const selectedVariables = ref<string[]>([])
const dateFrom = ref('')
const dateTo = ref('')
const exporting = ref(false)
const exported = ref(false)
const exportError = ref('')

onMounted(async () => {
  try {
    const [s, v] = await Promise.all([
      api.get<any[]>('/studies').catch(() => []),
      api.get<any[]>('/variables').catch(() => []),
    ])
    studies.value = s; variables.value = v
    if (s.length) selectedStudies.value = [s[0].id]
  } catch {}
  loading.value = false
})

function toggleStudy(id: string) { const i = selectedStudies.value.indexOf(id); i >= 0 ? selectedStudies.value.splice(i, 1) : selectedStudies.value.push(id) }
function toggleVariable(id: string) { const i = selectedVariables.value.indexOf(id); i >= 0 ? selectedVariables.value.splice(i, 1) : selectedVariables.value.push(id) }

async function doExport() {
  exporting.value = true
  exportError.value = ''
  try {
    await api.download('/export', `phenotyping_export.${format.value}`, {
      method: 'POST',
      body: {
        format: format.value,
        study_ids: selectedStudies.value,
        variable_ids: selectedVariables.value,
        date_from: dateFrom.value,
        date_to: dateTo.value,
      },
    })
    exported.value = true
    setTimeout(() => (exported.value = false), 4000)
  } catch (e: any) {
    exportError.value = e.message || 'Ошибка экспорта'
  }
  exporting.value = false
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <div>
      <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">Экспорт данных</h1>
      <p class="text-sm text-(--color-text-secondary) mt-1">Выгрузка результатов фенотипирования в XLSX, PDF, CSV или BrAPI JSON</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div class="lg:col-span-2 space-y-5">
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Формат</h3>
          <div class="grid grid-cols-2 gap-3">
            <button v-for="f in formats" :key="f.id" @click="format = f.id" :class="['p-4 rounded-lg border text-left transition-all', format === f.id ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
              <div class="flex items-center gap-2 mb-2"><div :class="['w-3 h-3 rounded-full border-2', format === f.id ? 'border-(--color-accent-green) bg-(--color-accent-green)' : 'border-(--color-text-muted)']"></div><span class="text-sm font-semibold text-(--color-text-primary)">{{ f.title }}</span></div>
              <p class="text-xs text-(--color-text-muted)">{{ f.hint }}</p>
            </button>
          </div>
        </div>

        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Эксперименты</h3>
          <div class="space-y-2">
            <button v-for="study in studies" :key="study.id" @click="toggleStudy(study.id)" :class="['w-full p-3 rounded-lg border text-left transition-all flex items-center gap-3', selectedStudies.includes(study.id) ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
              <div :class="['w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0', selectedStudies.includes(study.id) ? 'border-(--color-accent-green) bg-(--color-accent-green)' : 'border-(--color-text-muted)']">
                <svg v-if="selectedStudies.includes(study.id)" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" class="text-(--color-text-inverse)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
              </div>
              <div><p class="text-sm text-(--color-text-primary)">{{ study.name }}</p><p class="text-xs text-(--color-text-muted)">{{ study.plant_count || study.plantCount || 0 }} растений &middot; {{ study.status }}</p></div>
            </button>
          </div>
        </div>

        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <div class="flex items-center justify-between mb-4"><h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary)">Переменные</h3><span class="text-xs text-(--color-text-muted)">{{ selectedVariables.length === 0 ? 'Все' : `${selectedVariables.length} выбрано` }}</span></div>
          <div class="flex flex-wrap gap-2">
            <button v-for="ov in variables" :key="ov.id" @click="toggleVariable(ov.id)" :class="['px-3 py-1.5 rounded-lg text-xs transition-all border', selectedVariables.includes(ov.id) ? 'bg-(--color-accent-green)/10 text-(--color-accent-green) border-(--color-accent-green)/20' : 'bg-(--color-bg-base) text-(--color-text-secondary) border-(--color-border-subtle) hover:border-(--color-border-default)']">{{ ov.name }}</button>
          </div>
        </div>

        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Временной диапазон</h3>
          <div class="grid grid-cols-2 gap-4">
            <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">От</label><input v-model="dateFrom" type="date" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
            <div><label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">До</label><input v-model="dateTo" type="date" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/></div>
          </div>
        </div>
      </div>

      <div class="space-y-5">
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 sticky top-20">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Сводка экспорта</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between text-sm"><span class="text-(--color-text-muted)">Формат</span><span class="text-(--color-text-primary) font-medium">{{ formatInfo.title }}</span></div>
            <div class="flex items-center justify-between text-sm"><span class="text-(--color-text-muted)">Эксперименты</span><span class="text-(--color-text-primary) font-medium">{{ selectedStudies.length }}</span></div>
            <div class="flex items-center justify-between text-sm"><span class="text-(--color-text-muted)">Переменные</span><span class="text-(--color-text-primary) font-medium">{{ selectedVariables.length === 0 ? 'Все' : selectedVariables.length }}</span></div>
            <div class="flex items-center justify-between text-sm"><span class="text-(--color-text-muted)">Период</span><span class="text-(--color-text-primary) font-medium text-xs">{{ dateFrom || dateTo ? `${dateFrom || '…'} — ${dateTo || '…'}` : 'Весь период' }}</span></div>
          </div>
          <div class="glow-line my-5"></div>
          <button @click="doExport" :disabled="selectedStudies.length === 0 || exporting" class="w-full py-3 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2">
            <svg v-if="exporting" class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            {{ exporting ? 'Формирование...' : 'Скачать файл' }}
          </button>
          <p v-if="exportError" class="mt-4 p-3 bg-(--color-accent-rose)/10 border border-(--color-accent-rose)/20 rounded-lg text-xs text-(--color-accent-rose)">{{ exportError }}</p>
          <transition name="modal"><div v-if="exported" class="mt-4 p-3 bg-(--color-accent-green)/10 border border-(--color-accent-green)/20 rounded-lg text-center"><p class="text-xs text-(--color-accent-green) font-medium">Файл сформирован!</p></div></transition>
          <div class="mt-5 p-3 bg-(--color-bg-base) rounded-lg">
            <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mb-1">Совместимость</p>
            <div class="flex flex-wrap gap-1.5 mt-2">
              <span v-for="tag in formatInfo.tags" :key="tag" class="px-2 py-0.5 rounded text-[10px] bg-(--color-bg-surface) text-(--color-text-secondary) border border-(--color-border-subtle)">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.modal-enter-active, .modal-leave-active { transition: all 0.3s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: translateY(4px); }
</style>
