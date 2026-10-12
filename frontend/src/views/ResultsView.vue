<!--
  ResultsView — redesigned with:
  1. Multiple measurements per image (PlantCV-style)
  2. CSV export
  3. Image viewing from GridFS
  4. Folder-based browsing of phenotyped images
-->
<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useSignedImages } from '@/composables/useSignedImages'
import TraitSummaryPanel from '@/components/TraitSummaryPanel.vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const route = useRoute()
const api = useApi()
const signed = useSignedImages()
const studyId = computed(() => route.params.studyId as string)

const study = ref<any>(null)
const plants = ref<any[]>([])
const analysisRuns = ref<any[]>([])
const loading = ref(true)
const activeTab = ref<'runs' | 'images' | 'charts' | 'stats' | 'table'>('runs')

// Runs tab
const expandedRunId = ref<string | null>(null)

// Images tab
const selectedFolder = ref<string | null>(null)
const lightboxImage = ref<any>(null)

// Charts tab
const selectedVariable = ref('')
const chartCanvas = ref<HTMLCanvasElement | null>(null)
let chartInstance: Chart | null = null

onMounted(async () => {
  try {
    const [s, p, runs] = await Promise.all([
      api.get<any>(`/studies/${studyId.value}`),
      api.get<any[]>(`/studies/${studyId.value}/observation-units`).catch(() => []),
      api.get<any[]>(`/studies/${studyId.value}/analysis-runs`).catch(() => []),
    ])
    study.value = s
    plants.value = p
    analysisRuns.value = runs
    // Auto-select first folder
    if (folders.value.length) selectedFolder.value = folders.value[0]
    // Auto-select first variable for charts
    const varNames = [...new Set(p.flatMap((pl: any) => (pl.observations || []).map((o: any) => o.variableName || o.variable_name)))]
    if (varNames.length) selectedVariable.value = varNames[0]
  } catch {}
  loading.value = false
  await nextTick()
  if (activeTab.value === 'charts') setTimeout(buildChart, 200)
})

// ─── Computed ────────────────────────────────────────────────

const folders = computed(() => {
  const set = new Set<string>()
  for (const run of analysisRuns.value) {
    if (run.folderName) set.add(run.folderName)
  }
  return [...set]
})

const folderImages = computed(() => {
  if (!selectedFolder.value) return []
  const imgs: any[] = []
  for (const run of analysisRuns.value) {
    if (run.folderName !== selectedFolder.value) continue
    for (const res of run.results || []) {
      imgs.push({ ...res, runId: run.id, solutionName: run.solutionName, runDate: run.createdAt })
    }
  }
  return imgs
})

const folderStats = computed(() => {
  const stats: Record<string, { images: number; runs: number; solutions: Set<string> }> = {}
  for (const run of analysisRuns.value) {
    const f = run.folderName || 'default'
    if (!stats[f]) stats[f] = { images: 0, runs: 0, solutions: new Set() }
    stats[f].runs++
    stats[f].images += (run.results || []).length
    stats[f].solutions.add(run.solutionName || '')
  }
  return stats
})

const allObservations = computed(() => plants.value.flatMap(p => (p.observations || []).map((o: any) => ({ ...o, plantName: p.name, treatment: p.treatment }))))
const variableNames = computed(() => [...new Set(allObservations.value.map(o => o.variableName || o.variable_name))])
const filteredObs = computed(() => {
  if (!selectedVariable.value) return allObservations.value
  return allObservations.value.filter(o => (o.variableName || o.variable_name || '').includes(selectedVariable.value))
})

// All measurements flat table
const allMeasurements = computed(() => {
  const rows: any[] = []
  for (const run of analysisRuns.value) {
    for (const res of run.results || []) {
      for (const m of res.measurements || []) {
        rows.push({
          runDate: run.createdAt,
          solution: run.solutionName,
          folder: run.folderName,
          fileName: res.fileName,
          plantName: res.plantName,
          variable: m.variableName,
          value: m.value,
          unit: m.unit,
          coTermId: m.coTermId,
        })
      }
    }
  }
  return rows
})

const totalImages = computed(() => analysisRuns.value.reduce((s: number, r: any) => s + (r.results || []).length, 0))
const totalMeasurements = computed(() => allMeasurements.value.length)

// ─── Functions ───────────────────────────────────────────────

function toggleRun(id: string) {
  expandedRunId.value = expandedRunId.value === id ? null : id
}

function imageUrl(imageId: string) {
  return signed.imageUrl(imageId)
}

function openLightbox(img: any) {
  lightboxImage.value = img
}

function closeLightbox() {
  lightboxImage.value = null
}

const exporting = ref<string | null>(null)

async function downloadExport(kind: 'xlsx' | 'pdf' | 'csv') {
  exporting.value = kind
  try {
    await api.download(`/studies/${studyId.value}/export?format=${kind}`, `results_${studyId.value}.${kind}`)
  } catch (e: any) {
    alert('Ошибка экспорта: ' + (e.message || 'unknown'))
  }
  exporting.value = null
}
const downloadCsv = () => downloadExport('csv')

function buildChart() {
  if (!chartCanvas.value) return
  if (chartInstance) chartInstance.destroy()
  const datasets: any = {}
  const colors = ['#4ADE80', '#38BDF8', '#FBBF24', '#FB7185', '#A78BFA', '#F97316', '#14B8A6', '#E879F9']
  let ci = 0
  for (const plant of plants.value) {
    const obs = (plant.observations || []).filter((o: any) => (o.variableName || o.variable_name || '').includes(selectedVariable.value))
    if (!obs.length) continue
    const c = colors[ci % colors.length]
    datasets[plant.name] = { label: plant.name, data: obs.map((o: any) => ({ x: (o.observationTimeStamp || o.observation_timestamp || '').split('T')[0], y: parseFloat(o.value) })), borderColor: c, backgroundColor: c + '20' }
    ci++
  }
  chartInstance = new Chart(chartCanvas.value, {
    type: 'line', data: { datasets: Object.values(datasets) },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: '#8FA399', font: { family: 'Plus Jakarta Sans', size: 11 }, usePointStyle: true, pointStyle: 'circle' } },
        tooltip: { backgroundColor: '#1A2320', titleColor: '#E4EBE7', bodyColor: '#8FA399', borderColor: '#2A3A33', borderWidth: 1, cornerRadius: 8, padding: 10 } },
      scales: { x: { type: 'category', grid: { color: '#1E2B26' }, ticks: { color: '#5A7068', font: { family: 'Plus Jakarta Sans', size: 10 } } },
        y: { grid: { color: '#1E2B26' }, ticks: { color: '#5A7068', font: { family: 'Plus Jakarta Sans', size: 10 } } } },
      elements: { point: { radius: 3, hoverRadius: 6 }, line: { tension: 0.3, borderWidth: 2 } },
    },
  })
}

watch(selectedVariable, () => { setTimeout(buildChart, 100) })
watch(activeTab, (t) => { if (t === 'charts') nextTick(() => setTimeout(buildChart, 200)) })
</script>

<template>
  <div v-if="study" class="space-y-6 fade-in">
    <!-- Header -->
    <div class="flex items-end justify-between">
      <div>
        <router-link :to="`/experiments/${studyId}`" class="text-xs text-(--color-accent-green) hover:underline mb-2 inline-flex items-center gap-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
          {{ study.name }}
        </router-link>
        <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary) mt-2">Результаты</h1>
        <p class="text-sm text-(--color-text-secondary) mt-1">{{ analysisRuns.length }} запусков анализа · {{ totalImages }} изображений · {{ totalMeasurements }} измерений</p>
      </div>
      <div class="flex gap-2">
        <button v-for="fmt in (['xlsx', 'pdf', 'csv'] as const)" :key="fmt" @click="downloadExport(fmt)" :disabled="exporting !== null"
          class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2 disabled:opacity-50">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ exporting === fmt ? 'Формирование...' : fmt.toUpperCase() }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-0 border-b border-(--color-border-subtle)">
      <button v-for="tab in [{id:'runs',l:'Анализы'},{id:'images',l:'Изображения'},{id:'charts',l:'Графики'},{id:'stats',l:'Статистика'},{id:'table',l:'Таблица'}]" :key="tab.id" @click="activeTab = tab.id as any"
        :class="['px-4 py-3 text-sm transition-colors relative', activeTab === tab.id ? 'text-(--color-accent-green)' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">
        {{ tab.l }}<span v-if="activeTab === tab.id" class="absolute bottom-0 left-0 right-0 h-px bg-(--color-accent-green)"></span>
      </button>
    </div>

    <!-- ═══ TAB 1: Analysis Runs ═══ -->
    <div v-if="activeTab === 'runs'" class="space-y-4">
      <div v-if="!analysisRuns.length" class="text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="mx-auto text-(--color-text-muted) mb-3" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        <p class="text-sm text-(--color-text-muted)">Нет результатов анализа</p>
        <p class="text-xs text-(--color-text-muted) mt-1">Запустите анализ из экрана эксперимента</p>
      </div>

      <div v-for="run in analysisRuns" :key="run.id" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <!-- Run header -->
        <button @click="toggleRun(run.id)" class="w-full px-5 py-4 flex items-center justify-between hover:bg-(--color-bg-hover) transition-colors">
          <div class="flex items-center gap-4">
            <div class="w-9 h-9 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-(--color-accent-green)" stroke-linecap="round"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 14l2 2 4-4"/></svg>
            </div>
            <div class="text-left">
              <p class="text-sm font-medium text-(--color-text-primary)">{{ run.solutionName }}</p>
              <p class="text-xs text-(--color-text-muted)">{{ run.folderName }} · {{ (run.results || []).length }} изобр. · {{ run.createdAt }}</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-(--color-accent-green)/10 text-(--color-accent-green)">{{ run.status }}</span>
            <svg :class="['w-4 h-4 text-(--color-text-muted) transition-transform', expandedRunId === run.id ? 'rotate-180' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6,9 12,15 18,9"/></svg>
          </div>
        </button>

        <!-- Run details (expanded) -->
        <div v-if="expandedRunId === run.id" class="border-t border-(--color-border-subtle)">
          <!-- Output variables legend -->
          <div v-if="run.outputVariables?.length" class="px-5 py-3 bg-(--color-bg-base) border-b border-(--color-border-subtle) flex flex-wrap gap-2">
            <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mr-1 self-center">Переменные:</span>
            <span v-for="ov in run.outputVariables" :key="ov.coTermId" class="px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-green)/10 text-(--color-accent-green) font-medium">
              {{ ov.name }} <span class="opacity-60">({{ ov.coTermId }})</span>
            </span>
          </div>

          <!-- Per-image results -->
          <div class="divide-y divide-(--color-border-subtle)">
            <div v-for="(res, idx) in run.results" :key="idx" class="px-5 py-3 hover:bg-(--color-bg-hover) transition-colors">
              <div class="flex items-start gap-4">
                <!-- Thumbnail -->
                <div class="w-16 h-16 rounded-lg overflow-hidden bg-(--color-bg-base) flex-shrink-0 cursor-pointer border border-(--color-border-subtle) hover:border-(--color-accent-green)/50 transition-colors" @click="openLightbox(res)">
                  <img v-if="res.imageId" :src="imageUrl(res.imageId)" class="w-full h-full object-cover" loading="lazy" />
                  <div v-else class="w-full h-full flex items-center justify-center text-(--color-text-muted)">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
                  </div>
                </div>
                <!-- Info + measurements -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <p class="text-sm font-medium text-(--color-text-primary) truncate">{{ res.fileName }}</p>
                    <span v-if="res.plantName" class="px-1.5 py-0.5 rounded text-[10px] bg-(--color-accent-sky)/10 text-(--color-accent-sky)">{{ res.plantName }}</span>
                  </div>
                  <!-- Multiple measurements grid -->
                  <div class="mt-2 flex flex-wrap gap-x-5 gap-y-1">
                    <div v-for="m in res.measurements" :key="m.variableName" class="flex items-baseline gap-1.5">
                      <span class="text-[10px] text-(--color-text-muted)">{{ m.variableName }}:</span>
                      <span class="text-sm font-mono font-semibold text-(--color-accent-green)">{{ m.value }}</span>
                      <span class="text-[10px] text-(--color-text-muted)">{{ m.unit }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ TAB 2: Folder-based Image Browser ═══ -->
    <div v-if="activeTab === 'images'">
      <div v-if="!folders.length" class="text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
        <p class="text-sm text-(--color-text-muted)">Нет обработанных изображений</p>
      </div>

      <div v-else class="flex gap-5">
        <!-- Folder sidebar -->
        <div class="w-56 flex-shrink-0 space-y-1">
          <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) px-3 mb-2">Папки</p>
          <button v-for="folder in folders" :key="folder" @click="selectedFolder = folder"
            :class="['w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all flex items-center gap-3',
              selectedFolder === folder
                ? 'bg-(--color-accent-green)/10 text-(--color-accent-green) font-medium'
                : 'text-(--color-text-secondary) hover:bg-(--color-bg-hover)']">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" :stroke="selectedFolder === folder ? 'currentColor' : '#5A7068'" stroke-width="1.5" stroke-linecap="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
            <div class="flex-1 min-w-0">
              <p class="truncate">{{ folder }}</p>
              <p class="text-[10px] text-(--color-text-muted) mt-0.5">{{ folderStats[folder]?.images || 0 }} изобр. · {{ folderStats[folder]?.runs || 0 }} запусков</p>
            </div>
          </button>
        </div>

        <!-- Image grid -->
        <div class="flex-1">
          <div v-if="folderImages.length" class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div v-for="(img, idx) in folderImages" :key="idx" @click="openLightbox(img)"
              class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden cursor-pointer group hover:border-(--color-accent-green)/40 transition-all hover:shadow-lg hover:shadow-(--color-accent-green)/5">
              <!-- Image preview -->
              <div class="aspect-[4/3] bg-(--color-bg-base) relative overflow-hidden">
                <img v-if="img.imageId" :src="imageUrl(img.imageId)" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#5A7068" stroke-width="1"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
                </div>
                <!-- Measurements overlay -->
                <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3 pt-6">
                  <div class="flex flex-wrap gap-x-3 gap-y-0.5">
                    <span v-for="m in (img.measurements || []).slice(0, 3)" :key="m.variableName" class="text-[11px] text-white/90 font-mono">
                      {{ m.value }}<span class="text-white/50 text-[9px] ml-0.5">{{ m.unit }}</span>
                    </span>
                  </div>
                </div>
                <!-- Solution badge -->
                <div class="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[9px] bg-black/50 text-white/80 backdrop-blur-sm">
                  {{ img.solutionName }}
                </div>
              </div>
              <!-- Card footer -->
              <div class="p-3">
                <p class="text-xs font-medium text-(--color-text-primary) truncate">{{ img.fileName }}</p>
                <p v-if="img.plantName" class="text-[10px] text-(--color-text-muted) mt-0.5">{{ img.plantName }}</p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-(--color-text-muted) text-sm">Выберите папку</div>
        </div>
      </div>
    </div>

    <!-- ═══ TAB 3: Charts ═══ -->
    <div v-if="activeTab === 'charts'" class="space-y-5">
      <div v-if="!variableNames.length" class="text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
        <p class="text-sm text-(--color-text-muted)">Нет наблюдений для построения графиков</p>
      </div>
      <template v-else>
        <div class="flex items-center gap-3">
          <label class="text-xs text-(--color-text-muted) uppercase tracking-wider">Переменная:</label>
          <select v-model="selectedVariable" class="px-3 py-2 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50">
            <option v-for="vn in variableNames" :key="vn" :value="vn">{{ vn }}</option>
          </select>
        </div>
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
          <h3 class="font-(family-name:--font-display) text-lg text-(--color-text-primary) mb-4">Кривые роста: {{ selectedVariable }}</h3>
          <div class="h-80"><canvas ref="chartCanvas"></canvas></div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div v-for="plant in plants" :key="plant.id" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
            <p class="text-xs font-medium text-(--color-text-secondary) truncate">{{ plant.name }}</p>
            <p class="text-[10px] text-(--color-text-muted) mt-0.5">{{ plant.germplasm?.germplasmName || plant.germplasm?.germplasm_name }}</p>
            <div class="mt-2 flex items-baseline gap-1"><span class="text-lg font-semibold text-(--color-text-primary)">{{ (plant.observations || []).length }}</span><span class="text-[10px] text-(--color-text-muted)">набл.</span></div>
          </div>
        </div>
      </template>
    </div>

    <TraitSummaryPanel v-if="activeTab === 'stats'" :study-id="studyId" />

    <!-- ═══ TAB 4: Full Data Table ═══ -->
    <div v-if="activeTab === 'table'">
      <div v-if="!allMeasurements.length" class="text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
        <p class="text-sm text-(--color-text-muted)">Нет данных измерений</p>
      </div>
      <div v-else class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-(--color-border-subtle)">
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Дата</th>
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Решение</th>
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Папка</th>
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Файл</th>
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Растение</th>
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Переменная</th>
              <th class="px-4 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Значение</th>
              <th class="px-4 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">CO Term</th>
            </tr></thead>
            <tbody class="divide-y divide-(--color-border-subtle)">
              <tr v-for="(row, i) in allMeasurements.slice(0, 100)" :key="i" class="hover:bg-(--color-bg-hover) transition-colors">
                <td class="px-4 py-2 text-(--color-text-muted) text-xs">{{ row.runDate }}</td>
                <td class="px-4 py-2 text-(--color-text-secondary) text-xs">{{ row.solution }}</td>
                <td class="px-4 py-2 text-(--color-text-muted) text-xs font-mono">{{ row.folder }}</td>
                <td class="px-4 py-2 text-(--color-text-primary) text-xs truncate max-w-40">{{ row.fileName }}</td>
                <td class="px-4 py-2 text-xs"><span v-if="row.plantName" class="px-1.5 py-0.5 rounded bg-(--color-accent-sky)/10 text-(--color-accent-sky)">{{ row.plantName }}</span></td>
                <td class="px-4 py-2 text-(--color-text-secondary) text-xs">{{ row.variable }}</td>
                <td class="px-4 py-2 text-right font-mono text-xs font-semibold text-(--color-accent-green)">{{ row.value }} <span class="text-(--color-text-muted) font-normal">{{ row.unit }}</span></td>
                <td class="px-4 py-2 text-(--color-text-muted) text-[10px] font-mono">{{ row.coTermId }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="px-4 py-3 border-t border-(--color-border-subtle) flex items-center justify-between">
          <span class="text-xs text-(--color-text-muted)">Показано {{ Math.min(allMeasurements.length, 100) }} из {{ allMeasurements.length }}</span>
          <button @click="downloadCsv" class="text-xs text-(--color-accent-green) hover:underline flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Скачать CSV
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ Lightbox Modal ═══ -->
    <Teleport to="body">
      <div v-if="lightboxImage" class="fixed inset-0 z-50 flex items-center justify-center" @keydown.esc="closeLightbox">
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="closeLightbox"></div>
        <div class="relative max-w-5xl max-h-[90vh] w-full mx-4 flex gap-5 z-10">
          <!-- Image -->
          <div class="flex-1 bg-(--color-bg-surface) rounded-2xl overflow-hidden shadow-2xl">
            <img v-if="lightboxImage.imageId" :src="imageUrl(lightboxImage.imageId)" class="w-full h-full object-contain max-h-[85vh]" />
            <div v-else class="h-96 flex items-center justify-center text-(--color-text-muted)">Изображение недоступно</div>
          </div>
          <!-- Side panel with measurements -->
          <div class="w-72 bg-(--color-bg-surface) rounded-2xl p-5 overflow-y-auto shadow-2xl flex-shrink-0">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold text-(--color-text-primary)">Измерения</h3>
              <button @click="closeLightbox" class="p-1 rounded-lg hover:bg-(--color-bg-hover) text-(--color-text-muted)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <p class="text-xs text-(--color-text-secondary) font-medium mb-1">{{ lightboxImage.fileName }}</p>
            <p v-if="lightboxImage.plantName" class="text-xs text-(--color-text-muted) mb-4">Растение: <span class="text-(--color-accent-sky)">{{ lightboxImage.plantName }}</span></p>

            <div class="space-y-3">
              <div v-for="m in lightboxImage.measurements || []" :key="m.variableName" class="bg-(--color-bg-base) rounded-lg p-3 border border-(--color-border-subtle)">
                <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mb-1">{{ m.variableName }}</p>
                <p class="text-xl font-mono font-bold text-(--color-accent-green)">{{ m.value }} <span class="text-sm font-normal text-(--color-text-muted)">{{ m.unit }}</span></p>
                <p v-if="m.coTermId" class="text-[10px] text-(--color-text-muted) mt-1 font-mono">{{ m.coTermId }}</p>
              </div>
            </div>

            <!-- Raw metrics if available -->
            <div v-if="lightboxImage.metrics && Object.keys(lightboxImage.metrics).length" class="mt-4 pt-4 border-t border-(--color-border-subtle)">
              <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mb-2">Сырые данные</p>
              <div class="space-y-1">
                <div v-for="(val, key) in lightboxImage.metrics" :key="key" class="flex items-center justify-between text-xs">
                  <span class="text-(--color-text-muted)">{{ key }}</span>
                  <span class="font-mono text-(--color-text-secondary)">{{ typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : val }}</span>
                </div>
              </div>
            </div>

            <p v-if="lightboxImage.solutionName" class="text-[10px] text-(--color-text-muted) mt-4">Алгоритм: {{ lightboxImage.solutionName }}</p>
            <p v-if="lightboxImage.runDate" class="text-[10px] text-(--color-text-muted)">Дата: {{ lightboxImage.runDate }}</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>

  <!-- Loading -->
  <div v-else-if="loading" class="space-y-4">
    <div v-for="i in 3" :key="i" class="h-20 bg-(--color-bg-surface) rounded-xl animate-pulse"></div>
  </div>
</template>
