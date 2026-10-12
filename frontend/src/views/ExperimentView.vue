<!--
  Experiment detail: overview with plants, per-plant images, folder-based upload, run phenotyping button
-->
<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useSignedImages } from '@/composables/useSignedImages'
import TraitSummaryPanel from '@/components/TraitSummaryPanel.vue'

const route = useRoute()
const api = useApi()
const { imageUrl, annotatedUrl } = useSignedImages()
const studyId = computed(() => route.params.studyId as string)

const study = ref<any>(null)
const plants = ref<any[]>([])
const studyImages = ref<any[]>([])
const loading = ref(true)
const activeTab = ref('overview')
const tabs = [
  { id: 'overview', label: 'Обзор' },
  { id: 'plants', label: 'Растения' },
  { id: 'results', label: 'Результаты' },
]

const expandedRun = ref<string | null>(null)
// ─── Results tab state ───────────────────────────────────────
const resultsSubTab = ref<'runs' | 'table' | 'stats'>('runs')
const expandedRunId = ref<string | null>(null)
const selectedFolder = ref<string | null>(null)
const lightboxImage = ref<any>(null)
const selectedVariable = ref('')
const chartCanvas = ref<HTMLCanvasElement | null>(null)
let chartInstance: any = null

function toggleRunResult(id: string) { expandedRunId.value = expandedRunId.value === id ? null : id }
function openLightbox(img: any) { lightboxImage.value = img }
function closeLightbox() { lightboxImage.value = null }

const folders = computed(() => {
  const set = new Set<string>()
  for (const run of analysisRuns.value) { if (run.folderName) set.add(run.folderName) }
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
  const stats: Record<string, { images: number; runs: number }> = {}
  for (const run of analysisRuns.value) {
    const f = run.folderName || 'default'
    if (!stats[f]) stats[f] = { images: 0, runs: 0 }
    stats[f].runs++
    stats[f].images += (run.results || []).length
  }
  return stats
})
const allObservations = computed(() => plants.value.flatMap((p: any) => (p.observations || []).map((o: any) => ({ ...o, plantName: p.name }))))
const variableNames = computed(() => [...new Set(allObservations.value.map((o: any) => o.variableName || o.variable_name))])
const allMeasurements = computed(() => {
  const rows: any[] = []
  for (const run of analysisRuns.value) {
    for (const res of run.results || []) {
      for (const m of res.measurements || []) {
        rows.push({ runDate: run.createdAt, solution: run.solutionName, folder: run.folderName, fileName: res.fileName, plantName: res.plantName, variable: m.variableName, value: m.value, unit: m.unit, coTermId: m.coTermId })
      }
    }
  }
  return rows
})
const totalImages = computed(() => analysisRuns.value.reduce((s: number, r: any) => s + (r.results || []).length, 0))
const totalMeasurements = computed(() => allMeasurements.value.length)


const exporting = ref<string | null>(null)

async function downloadExport(kind: 'xlsx' | 'pdf' | 'csv' | 'zip') {
  exporting.value = kind
  try {
    const path = kind === 'zip'
      ? `/studies/${studyId.value}/export-zip`
      : `/studies/${studyId.value}/export?format=${kind}`
    await api.download(path, `export_${studyId.value}.${kind}`)
  } catch (e: any) {
    alert('Ошибка экспорта: ' + (e.message || 'unknown'))
  }
  exporting.value = null
}
const downloadCsv = () => downloadExport('csv')

// Capture time is stored in UTC; show it in the viewer's local time zone
function formatCaptured(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Upload in chunks: keeps each request under the ingress body limit and passes
// the file modification time as a fallback capture time when the photo has no EXIF
const UPLOAD_CHUNK = 20
async function uploadInChunks(path: string, files: File[], fields: Record<string, string>) {
  const results: any[] = []
  for (let i = 0; i < files.length; i += UPLOAD_CHUNK) {
    const formData = new FormData()
    for (const f of files.slice(i, i + UPLOAD_CHUNK)) {
      formData.append('files', f)
      formData.append('capturedAt', new Date(f.lastModified).toISOString())
    }
    for (const [k, v] of Object.entries(fields)) formData.append(k, v)
    const chunk = await api.upload<any[]>(path, formData)
    results.push(...(Array.isArray(chunk) ? chunk : [chunk]))
  }
  return results
}

function addUploaded(results: any[]) {
  const known = new Set(studyImages.value.map(i => i.id))
  studyImages.value.push(...results.filter(r => r.id && !r.error && !known.has(r.id)))
}

function toggleRun(id: string) {
  expandedRun.value = expandedRun.value === id ? null : id
}

onMounted(async () => {
  try {
    const [s, p, imgs, runs] = await Promise.all([
      api.get<any>('/studies/' + studyId.value),
      api.get<any[]>('/studies/' + studyId.value + '/observation-units').catch(() => []),
      api.get<any[]>('/images/by-study/' + studyId.value).catch(() => []),
      api.get<any[]>('/studies/' + studyId.value + '/analysis-runs').catch(() => []),
    ])
    study.value = s
    plants.value = p
    studyImages.value = imgs
    analysisRuns.value = runs
  } catch {}
  loading.value = false
})

const totalObs = computed(() => plants.value.reduce((s, p) => s + (p.observations || []).length, 0))
const obsVars = computed(() => study.value?.observationVariableIds || [])

// Image folders
const imageFolders = computed(() => {
  const map: Record<string, any[]> = {}
  for (const img of studyImages.value) {
    const folder = img.folderName || 'Без папки'
    if (!map[folder]) map[folder] = []
    map[folder].push(img)
  }
  return map
})

// Upload modal
const showUploadModal = ref(false)
const uploadFolderName = ref('')
const uploadFiles = ref<File[]>([])
const uploading = ref(false)
const uploadResults = ref<any[]>([])

function openUploadModal() {
  uploadFolderName.value = ''
  uploadFiles.value = []
  uploadResults.value = []
  showUploadModal.value = true
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    uploadFiles.value = Array.from(input.files)
  }
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer?.files) {
    uploadFiles.value = Array.from(e.dataTransfer.files)
  }
}

function removeFile(idx: number) {
  uploadFiles.value.splice(idx, 1)
}

// Parse plant name from filename for preview
function guessPlantName(filename: string): string {
  const base = filename.replace(/\.[^.]+$/, '')
  for (const p of plants.value) {
    if (base.toLowerCase().includes(p.name.toLowerCase())) {
      return p.name
    }
  }
  return '—'
}

async function doUpload() {
  if (!uploadFiles.value.length) return
  uploading.value = true
  try {
    uploadResults.value = await uploadInChunks('/images/upload-batch', uploadFiles.value, {
      studyId: studyId.value,
      folderName: uploadFolderName.value,
    })
    addUploaded(uploadResults.value)
  } catch (e: any) {
    alert('Ошибка загрузки: ' + (e.message || 'unknown'))
  }
  uploading.value = false
}

function closeUpload() {
  showUploadModal.value = false
  uploadResults.value = []
}

// Expanded plant in plants tab
const expandedPlant = ref<string | null>(null)
function togglePlant(id: string) {
  expandedPlant.value = expandedPlant.value === id ? null : id
}

function plantImages(plantId: string) {
  return studyImages.value.filter(img => img.observationUnitId === plantId)
}

// Per-plant upload
const showPlantUploadModal = ref(false)
const plantUploadTarget = ref<any>(null)
const plantUploadFolder = ref('')
const plantUploadFiles = ref<File[]>([])
const plantUploading = ref(false)
const plantUploadResults = ref<any[]>([])

function openPlantUpload(plant: any) {
  plantUploadTarget.value = plant
  plantUploadFolder.value = ''
  plantUploadFiles.value = []
  plantUploadResults.value = []
  // Pre-select first existing folder if any
  const folderKeys = Object.keys(imageFolders.value)
  if (folderKeys.length > 0) plantUploadFolder.value = folderKeys[0]
  showPlantUploadModal.value = true
}

function handlePlantFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) plantUploadFiles.value = Array.from(input.files)
}

function handlePlantDrop(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer?.files) plantUploadFiles.value = Array.from(e.dataTransfer.files)
}

function removePlantFile(idx: number) {
  plantUploadFiles.value.splice(idx, 1)
}

async function doPlantUpload() {
  if (!plantUploadFiles.value.length || !plantUploadTarget.value) return
  plantUploading.value = true
  try {
    plantUploadResults.value = await uploadInChunks('/images/upload-plant', plantUploadFiles.value, {
      studyId: studyId.value,
      folderName: plantUploadFolder.value,
      observationUnitId: plantUploadTarget.value.id,
    })
    addUploaded(plantUploadResults.value)
  } catch (e: any) {
    alert('Ошибка загрузки: ' + (e.message || 'unknown'))
  }
  plantUploading.value = false
}

function closePlantUpload() {
  showPlantUploadModal.value = false
  plantUploadResults.value = []
}

// Run phenotyping modal
const showRunModal = ref(false)
const runStep = ref(0) // 0=select solution, 1=select folder, 2=running/done
const solutions = ref<any[]>([])
const selectedSolution = ref('')
const selectedRunFolder = ref('')
const runningPhenotyping = ref(false)
const runResult = ref<string | null>(null)
const analysisRuns = ref<any[]>([])

async function openRunModal() {
  runStep.value = 0
  selectedSolution.value = ''
  selectedRunFolder.value = ''
  runResult.value = null
  showRunModal.value = true
  // Load solutions
  try {
    solutions.value = await api.get<any[]>('/studies/' + studyId.value + '/matching-solutions')
  } catch { solutions.value = [] }
  // Load analysis runs
  try {
    analysisRuns.value = await api.get<any[]>('/studies/' + studyId.value + '/analysis-runs')
  } catch { analysisRuns.value = [] }
}

function runNextStep() {
  if (runStep.value === 0 && selectedSolution.value) runStep.value = 1
  else if (runStep.value === 1 && selectedRunFolder.value) runPhenotyping()
}

async function runPhenotyping() {
  runningPhenotyping.value = true
  runResult.value = null
  runStep.value = 2
  try {
    const result = await api.post<any>('/studies/' + studyId.value + '/run-analysis', {
      solution_id: selectedSolution.value,
      folder_name: selectedRunFolder.value,
    })
    runResult.value = result.message || 'Анализ завершён'
    // Reload analysis runs
    analysisRuns.value = await api.get<any[]>('/studies/' + studyId.value + '/analysis-runs').catch(() => [])
  } catch (e: any) {
    runResult.value = 'Ошибка: ' + (e.message || 'неизвестная ошибка')
  }
  runningPhenotyping.value = false
}

const selectedSolutionObj = computed(() => solutions.value.find(s => s.id === selectedSolution.value))

// Analysis results per folder
function folderRuns(folder: string) {
  return analysisRuns.value.filter(r => r.folderName === folder)
}

const statusMap: Record<string, string> = {
  active: 'Активен',
  completed: 'Завершен',
  draft: 'Черновик',
  archived: 'Архив',
}
</script>

<template>
  <div v-if="loading" class="space-y-6 fade-in">
    <div class="h-8 bg-(--color-bg-surface) rounded w-1/3 animate-pulse"></div>
    <div class="grid grid-cols-4 gap-3">
      <div v-for="i in 4" :key="i" class="h-20 bg-(--color-bg-surface) rounded-xl animate-pulse"></div>
    </div>
  </div>

  <div v-else-if="study" class="space-y-6 fade-in">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <router-link to="/experiments" class="text-xs text-(--color-accent-green) hover:underline mb-2 inline-flex items-center gap-1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15,18 9,12 15,6"/></svg>
            Эксперименты
        </router-link>
        <h1 class="font-(family-name:--font-display) text-2xl md:text-3xl text-(--color-text-primary)">{{ study.name }}</h1>
        <p v-if="study.description" class="text-sm text-(--color-text-secondary) mt-1">{{ study.description }}</p>
      </div>
      <div class="flex gap-2 flex-shrink-0">
        <button @click="openUploadModal" class="px-4 py-2.5 rounded-lg text-sm border border-(--color-border-default) text-(--color-text-secondary) hover:bg-(--color-bg-hover) hover:text-(--color-text-primary) transition-all flex items-center gap-2">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          Загрузить фото
        </button>
        <button @click="openRunModal" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all flex items-center gap-2">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="5,3 19,12 5,21 5,3"/></svg>
          Запустить
        </button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
        <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Растения</span>
        <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ plants.length }}</p>
      </div>
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
        <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Изображения</span>
        <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ studyImages.length }}</p>
      </div>
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
        <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Папки</span>
        <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ Object.keys(imageFolders).length }}</p>
      </div>
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
        <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Наблюдения</span>
        <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ totalObs }}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-(--color-border-subtle)">
      <div class="flex gap-0">
        <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
          :class="['px-4 py-3 text-sm transition-colors relative', activeTab === tab.id ? 'text-(--color-accent-green)' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">
          {{ tab.label }}
          <span v-if="activeTab === tab.id" class="absolute bottom-0 left-0 right-0 h-px bg-(--color-accent-green)"></span>
        </button>
      </div>
    </div>

    <!-- Overview tab -->
    <div v-if="activeTab === 'overview'" class="space-y-5">
      <!-- Info -->
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5">
        <h3 class="text-sm font-medium text-(--color-text-primary) mb-3">Информация</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div><span class="text-(--color-text-muted) uppercase tracking-wider text-[10px]">Тип</span><p class="text-(--color-text-secondary) mt-0.5">{{ study.studyType || study.study_type || '—' }}</p></div>
          <div><span class="text-(--color-text-muted) uppercase tracking-wider text-[10px]">Начало</span><p class="text-(--color-text-secondary) mt-0.5">{{ study.startDate || study.start_date || '—' }}</p></div>
          <div><span class="text-(--color-text-muted) uppercase tracking-wider text-[10px]">Окончание</span><p class="text-(--color-text-secondary) mt-0.5">{{ study.endDate || study.end_date || '—' }}</p></div>
          <div><span class="text-(--color-text-muted) uppercase tracking-wider text-[10px]">Переменных</span><p class="text-(--color-text-secondary) mt-0.5">{{ obsVars.length }}</p></div>
        </div>
      </div>

      <!-- Image folders -->
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div class="px-5 py-4 border-b border-(--color-border-subtle) flex items-center justify-between">
          <h3 class="text-sm font-medium text-(--color-text-primary)">Папки изображений</h3>
          <button @click="openUploadModal" class="text-xs text-(--color-accent-green) hover:underline">Загрузить</button>
        </div>
        <div v-if="Object.keys(imageFolders).length > 0" class="divide-y divide-(--color-border-subtle)">
          <div v-for="(imgs, folder) in imageFolders" :key="folder" class="px-5 py-4">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-accent-amber)" stroke-linecap="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
                <span class="text-sm font-medium text-(--color-text-primary)">{{ folder }}</span>
              </div>
              <div class="flex items-center gap-3">
                <span v-if="folderRuns(folder).length > 0" class="px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20">{{ folderRuns(folder).length }} анализов</span>
                <span class="text-xs text-(--color-text-muted)">{{ imgs.length }} файлов</span>
              </div>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="img in imgs.slice(0, 8)" :key="img.id"
                class="px-2 py-0.5 text-[10px] bg-(--color-bg-base) border border-(--color-border-subtle) rounded text-(--color-text-muted) font-mono">
                {{ img.fileName }}
              </span>
              <span v-if="imgs.length > 8" class="px-2 py-0.5 text-[10px] text-(--color-text-muted)">+{{ imgs.length - 8 }}</span>
            </div>
          </div>
        </div>
        <div v-else class="px-5 py-8 text-center text-(--color-text-muted) text-sm">Нет загруженных изображений</div>
      </div>

      <!-- Plants preview -->
      <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div class="px-5 py-4 border-b border-(--color-border-subtle)">
          <h3 class="text-sm font-medium text-(--color-text-primary)">Растения</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-(--color-border-subtle)">
              <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Название</th>
              <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Позиция</th>
              <th class="px-5 py-3 text-left text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Обработка</th>
              <th class="px-5 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Фото</th>
              <th class="px-5 py-3 text-right text-[10px] uppercase tracking-wider text-(--color-text-muted) font-medium">Наблюд.</th>
            </tr></thead>
            <tbody class="divide-y divide-(--color-border-subtle)">
              <tr v-for="plant in plants.slice(0, 10)" :key="plant.id" class="hover:bg-(--color-bg-hover) transition-colors">
                <td class="px-5 py-3 text-(--color-text-primary) font-medium">{{ plant.name }}</td>
                <td class="px-5 py-3 text-(--color-text-secondary)">{{ plant.position || '—' }}</td>
                <td class="px-5 py-3"><span :class="['px-2 py-0.5 rounded text-[10px] uppercase', (plant.treatment || '').toLowerCase().includes('контроль') || (plant.treatment || '').toLowerCase().includes('control') ? 'bg-(--color-accent-green)/10 text-(--color-accent-green)' : 'bg-(--color-accent-amber)/10 text-(--color-accent-amber)']">{{ plant.treatment || '—' }}</span></td>
                <td class="px-5 py-3 text-right text-(--color-text-secondary)">{{ plantImages(plant.id).length }}</td>
                <td class="px-5 py-3 text-right text-(--color-text-secondary)">{{ (plant.observations || []).length }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="plants.length === 0" class="px-5 py-8 text-center text-(--color-text-muted) text-sm">Нет зарегистрированных растений</div>
      </div>
    </div>

    <!-- Plants tab with per-plant images -->
    <div v-if="activeTab === 'plants'" class="space-y-3">
      <div v-for="plant in plants" :key="plant.id"
        class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div @click="togglePlant(plant.id)" class="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-(--color-bg-hover) transition-colors">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-accent-green)" stroke-linecap="round"><path d="M12 22c4-4 8-7.5 8-12a8 8 0 10-16 0c0 4.5 4 8 8 12z"/></svg>
            </div>
            <div>
              <h4 class="text-sm font-medium text-(--color-text-primary)">{{ plant.name }}</h4>
              <p class="text-xs text-(--color-text-muted)">{{ plant.position || '' }} {{ plant.treatment ? '· ' + plant.treatment : '' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-xs text-(--color-text-muted)">{{ plantImages(plant.id).length }} фото</span>
            <span class="text-xs text-(--color-text-muted)">{{ (plant.observations || []).length }} набл.</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted) transition-transform duration-200" :class="expandedPlant === plant.id ? 'rotate-180' : ''" stroke-linecap="round">
              <polyline points="6,9 12,15 18,9"/>
            </svg>
          </div>
        </div>
        <div v-if="expandedPlant === plant.id" class="px-5 pb-4 border-t border-(--color-border-subtle) pt-3">
          <div class="flex items-center justify-between mb-2">
            <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Изображения ({{ plantImages(plant.id).length }})</p>
            <button @click.stop="openPlantUpload(plant)" class="text-xs text-(--color-accent-green) hover:underline flex items-center gap-1">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Добавить фото
            </button>
          </div>
          <div v-if="plantImages(plant.id).length > 0" class="flex flex-wrap gap-2">
            <div v-for="img in plantImages(plant.id)" :key="img.id"
              class="px-3 py-2 bg-(--color-bg-base) border border-(--color-border-subtle) rounded-lg text-xs">
              <span class="font-mono text-(--color-text-primary)">{{ img.fileName }}</span>
              <span v-if="img.folderName" class="ml-2 text-(--color-text-muted)">{{ img.folderName }}</span>
              <span v-if="img.capturedAt" class="ml-2 text-(--color-text-muted)" :title="'SHA-256: ' + (img.sha256 || '—')">{{ formatCaptured(img.capturedAt) }}</span>
            </div>
          </div>
          <p v-else class="text-xs text-(--color-text-muted)">Нет привязанных изображений</p>
        </div>
      </div>
      <div v-if="plants.length === 0" class="text-center py-8 text-sm text-(--color-text-muted) bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">Нет растений</div>
    </div>

    <!-- ═══ RESULTS TAB ═══ -->
    <div v-if="activeTab === 'results'" class="space-y-5">
      <!-- Header with CSV export -->
      <div class="flex items-center justify-between">

        <div class="flex gap-2">
          <button v-for="fmt in (['xlsx', 'pdf', 'csv'] as const)" :key="fmt" @click="downloadExport(fmt)" :disabled="exporting !== null"
            class="px-3 py-2 border border-(--color-border-default) text-(--color-text-secondary) rounded-lg text-xs font-medium hover:bg-(--color-bg-hover) transition-all flex items-center gap-1.5 disabled:opacity-50">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            {{ exporting === fmt ? '...' : fmt.toUpperCase() }}
          </button>
          <button @click="downloadExport('zip')" :disabled="exporting !== null" class="px-4 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-xs font-semibold hover:opacity-90 transition-all flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            {{ exporting === 'zip' ? 'Формирование...' : 'ZIP (данные + изобр.)' }}
          </button>
        </div>
      </div>
      <!-- Sub-tabs -->
      <div class="flex gap-0 border-b border-(--color-border-subtle)">
        <button v-for="st in ([{id:'runs',l:'Анализы'},{id:'table',l:'Таблица'},{id:'stats',l:'Статистика'}] as const)" :key="st.id" @click="resultsSubTab = st.id"
          :class="['px-4 py-2.5 text-xs transition-colors relative', resultsSubTab === st.id ? 'text-(--color-accent-green)' : 'text-(--color-text-muted) hover:text-(--color-text-secondary)']">
          {{ st.l }}<span v-if="resultsSubTab === st.id" class="absolute bottom-0 left-0 right-0 h-px bg-(--color-accent-green)"></span>
        </button>
      </div>

      <!-- Sub: Runs -->
      <div v-if="resultsSubTab === 'runs'" class="space-y-3">
        <div v-if="!analysisRuns.length" class="text-center py-12 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
          <p class="text-sm text-(--color-text-muted)">Нет результатов анализа</p>
        </div>
        <div v-for="run in analysisRuns" :key="run.id" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
          <button @click="toggleRunResult(run.id)" class="w-full px-5 py-4 flex items-center justify-between hover:bg-(--color-bg-hover) transition-colors">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-accent-green)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
              </div>
              <div class="text-left">
                <p class="text-sm font-medium text-(--color-text-primary)">{{ run.solutionName }}</p>
                <p class="text-xs text-(--color-text-muted)">{{ run.folderName }} &middot; {{ (run.results || []).length }} изобр.</p>
              </div>
            </div>
            <svg :class="['w-4 h-4 text-(--color-text-muted) transition-transform', expandedRunId === run.id ? 'rotate-180' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6,9 12,15 18,9"/></svg>
          </button>
          <div v-if="expandedRunId === run.id" class="border-t border-(--color-border-subtle)">
            <div v-if="run.outputVariables?.length" class="px-5 py-2 bg-(--color-bg-base) border-b border-(--color-border-subtle) flex flex-wrap gap-2">
              <span v-for="ov in run.outputVariables" :key="ov.coTermId" class="px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-green)/10 text-(--color-accent-green)">{{ ov.name }} ({{ ov.coTermId }})</span>
            </div>
            <div class="divide-y divide-(--color-border-subtle)">
              <div v-for="(res, idx) in run.results" :key="idx" class="px-5 py-3 hover:bg-(--color-bg-hover)">
                <div class="flex items-start gap-3">
                  <div class="w-14 h-14 rounded-lg overflow-hidden bg-(--color-bg-base) flex-shrink-0 cursor-pointer border border-(--color-border-subtle)" @click="openLightbox(res)">
                    <img v-if="res.annotatedImageId || res.imageId" :src="res.annotatedImageId ? annotatedUrl(res.annotatedImageId) : imageUrl(res.imageId)" class="w-full h-full object-cover" loading="lazy" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <p class="text-sm font-medium text-(--color-text-primary)">{{ res.fileName }}</p>
                      <span v-if="res.plantName" class="px-1.5 py-0.5 rounded text-[10px] bg-(--color-accent-sky)/10 text-(--color-accent-sky)">{{ res.plantName }}</span>
                    </div>
                    <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
                      <div v-for="m in res.measurements" :key="m.variableName" class="flex items-baseline gap-1">
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

      <!-- Sub: Table (grouped by analysis run) -->
      <TraitSummaryPanel v-if="resultsSubTab === 'stats'" :study-id="studyId" :refresh-key="analysisRuns.length" />

      <div v-if="resultsSubTab === 'table'">
        <div v-if="!analysisRuns.length" class="text-center py-12 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
          <p class="text-sm text-(--color-text-muted)">Нет данных</p>
        </div>
        <div v-else class="space-y-3">
          <div v-for="run in analysisRuns" :key="'tbl-'+run.id" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
            <button @click="toggleRun(run.id)" class="w-full px-5 py-4 flex items-center justify-between hover:bg-(--color-bg-hover) transition-colors">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-accent-green)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                </div>
                <div class="text-left">
                  <p class="text-sm font-medium text-(--color-text-primary)">{{ run.solutionName }}</p>
                  <p class="text-xs text-(--color-text-muted)">{{ run.createdAt }} &middot; {{ run.folderName }}</p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20">{{ (run.results || []).reduce((s, r) => s + (r.measurements || []).length, 0) }} измерений</span>
                <svg :class="['w-4 h-4 text-(--color-text-muted) transition-transform', expandedRun === run.id ? 'rotate-180' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6,9 12,15 18,9"/></svg>
              </div>
            </button>
            <div v-if="expandedRun === run.id" class="border-t border-(--color-border-subtle)">
              <div class="overflow-x-auto">
                <table class="w-full text-xs">
                  <thead><tr class="border-b border-(--color-border-subtle)">
                    <th class="px-3 py-2 text-left text-[10px] uppercase text-(--color-text-muted)">Файл</th>
                    <th class="px-3 py-2 text-left text-[10px] uppercase text-(--color-text-muted)">Растение</th>
                    <th class="px-3 py-2 text-left text-[10px] uppercase text-(--color-text-muted)">Переменная</th>
                    <th class="px-3 py-2 text-right text-[10px] uppercase text-(--color-text-muted)">Значение</th>
                    <th class="px-3 py-2 text-left text-[10px] uppercase text-(--color-text-muted)">CO Term</th>
                  </tr></thead>
                  <tbody class="divide-y divide-(--color-border-subtle)">
                    <template v-for="res in (run.results || [])" :key="res.imageId">
                      <tr v-for="(m, mi) in (res.measurements || [])" :key="res.imageId + '-' + mi" class="hover:bg-(--color-bg-hover)">
                        <td class="px-3 py-1.5 text-(--color-text-primary) truncate max-w-40">{{ mi === 0 ? res.fileName : '' }}</td>
                        <td class="px-3 py-1.5"><span v-if="mi === 0 && res.plantName" class="px-1 py-0.5 rounded bg-(--color-accent-sky)/10 text-(--color-accent-sky) text-[10px]">{{ res.plantName }}</span></td>
                        <td class="px-3 py-1.5 text-(--color-text-secondary)">{{ m.variableName }}</td>
                        <td class="px-3 py-1.5 text-right font-mono font-semibold text-(--color-accent-green)">{{ m.value }} <span class="text-(--color-text-muted) font-normal">{{ m.unit }}</span></td>
                        <td class="px-3 py-1.5 text-(--color-text-muted) font-mono text-[10px]">{{ m.coTermId }}</td>
                      </tr>
                    </template>
                  </tbody>
                </table>
              </div>
              <div class="px-3 py-2 border-t border-(--color-border-subtle) flex items-center justify-between">
                <span class="text-[10px] text-(--color-text-muted)">{{ (run.results || []).reduce((s, r) => s + (r.measurements || []).length, 0) }} измерений</span>
                <button @click="downloadCsv" class="text-[10px] text-(--color-accent-green) hover:underline">Скачать CSV</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Lightbox -->
    <Teleport to="body">
      <div v-if="lightboxImage" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="closeLightbox"></div>
        <div class="relative max-w-5xl max-h-[90vh] w-full mx-4 flex gap-5 z-10">
          <div class="flex-1 bg-(--color-bg-surface) rounded-2xl overflow-hidden shadow-2xl">
            <img v-if="lightboxImage.annotatedImageId || lightboxImage.imageId" :src="lightboxImage.annotatedImageId ? annotatedUrl(lightboxImage.annotatedImageId) : imageUrl(lightboxImage.imageId)" class="w-full h-full object-contain max-h-[85vh]" />
          </div>
          <div class="w-64 bg-(--color-bg-surface) rounded-2xl p-4 overflow-y-auto shadow-2xl flex-shrink-0">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-xs font-semibold text-(--color-text-primary)">Измерения</h3>
              <button @click="closeLightbox" class="text-(--color-text-muted) hover:text-(--color-text-primary) text-lg leading-none">&times;</button>
            </div>
            <p class="text-xs text-(--color-text-secondary) mb-1">{{ lightboxImage.fileName }}</p>
            <p v-if="lightboxImage.plantName" class="text-[10px] text-(--color-text-muted) mb-3">{{ lightboxImage.plantName }}</p>
            <div class="space-y-2">
              <div v-for="m in lightboxImage.measurements || []" :key="m.variableName" class="bg-(--color-bg-base) rounded-lg p-2.5 border border-(--color-border-subtle)">
                <p class="text-[9px] uppercase tracking-wider text-(--color-text-muted)">{{ m.variableName }}</p>
                <p class="text-lg font-mono font-bold text-(--color-accent-green)">{{ m.value }} <span class="text-xs font-normal text-(--color-text-muted)">{{ m.unit }}</span></p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Upload modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeUpload"></div>
          <div class="relative w-full max-w-2xl mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl slide-up max-h-[90vh] overflow-hidden flex flex-col">
            <div class="px-6 pt-5 pb-4 border-b border-(--color-border-subtle)">
              <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary)">Загрузка изображений</h2>
              <p class="text-xs text-(--color-text-muted) mt-1">Файлы автоматически привязываются к растениям по имени: если имя файла содержит название растения (например, Plant-1.jpg → Plant-1), привязка происходит автоматически</p>
            </div>
            <div class="flex-1 overflow-y-auto p-6 space-y-5">
              <!-- Folder name -->
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название папки <span class="text-(--color-accent-rose)">*</span></label>
                <input v-model="uploadFolderName" type="text" placeholder="Например: День 7 — вид сверху" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                <p class="text-[10px] text-(--color-text-muted) mt-1">Папка группирует изображения в рамках эксперимента</p>
              </div>

              <!-- Drop zone -->
              <div v-if="uploadResults.length === 0"
                @drop="handleDrop" @dragover.prevent
                class="border-2 border-dashed border-(--color-border-default) rounded-xl p-8 text-center hover:border-(--color-accent-green)/30 transition-colors">
                <label class="cursor-pointer">
                  <input type="file" multiple accept="image/*" class="hidden" @change="handleFileSelect" />
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="mx-auto text-(--color-text-muted) mb-3" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  <p class="text-sm text-(--color-text-secondary)">Перетащите файлы или нажмите для выбора</p>
                  <p class="text-xs text-(--color-text-muted) mt-1">JPG, PNG, TIFF</p>
                </label>
              </div>

              <!-- Selected files preview -->
              <div v-if="uploadFiles.length > 0 && uploadResults.length === 0" class="space-y-2">
                <p class="text-xs text-(--color-text-muted) uppercase tracking-wider">Выбрано файлов: {{ uploadFiles.length }}</p>
                <div class="max-h-60 overflow-y-auto space-y-1">
                  <div v-for="(f, idx) in uploadFiles" :key="idx"
                    class="flex items-center justify-between px-3 py-2 bg-(--color-bg-base) border border-(--color-border-subtle) rounded-lg">
                    <div class="flex items-center gap-3 min-w-0">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted) flex-shrink-0" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
                      <span class="text-xs font-mono text-(--color-text-primary) truncate">{{ f.name }}</span>
                      <span class="text-[10px] text-(--color-text-muted) flex-shrink-0">→ {{ guessPlantName(f.name) }}</span>
                    </div>
                    <button @click="removeFile(idx)" class="p-1 text-(--color-text-muted) hover:text-(--color-accent-rose) transition-colors flex-shrink-0">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Upload results -->
              <div v-if="uploadResults.length > 0" class="space-y-2">
                <div class="flex items-center gap-2 text-(--color-accent-green) mb-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                  <span class="text-sm font-medium">Загружено {{ uploadResults.filter(r => !r.error).length }} из {{ uploadResults.length }} файлов</span>
                </div>
                <div class="max-h-48 overflow-y-auto space-y-1">
                  <div v-for="(r, ri) in uploadResults" :key="r.id || 'rejected-' + ri"
                    class="flex items-center justify-between gap-3 px-3 py-2 bg-(--color-bg-base) border border-(--color-border-subtle) rounded-lg text-xs">
                    <span class="font-mono text-(--color-text-primary) truncate">{{ r.uploadedName || r.fileName }}</span>
                    <span v-if="r.error" class="text-(--color-accent-rose) text-right">{{ r.error }}</span>
                    <span v-else class="flex items-center gap-2 flex-shrink-0">
                      <span v-if="r.duplicate" class="text-(--color-accent-amber)">{{ r.uploadedName && r.uploadedName !== r.fileName ? 'уже загружен как ' + r.fileName : 'уже загружен' }}</span>
                      <span class="text-(--color-text-muted)" :title="'Источник времени: ' + r.capturedAtSource">{{ formatCaptured(r.capturedAt) }}</span>
                      <span :class="r.matchedPlantName ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)'">
                        {{ r.matchedPlantName || 'не привязано' }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-(--color-border-subtle) flex justify-between">
              <button @click="closeUpload" class="px-4 py-2 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">
                {{ uploadResults.length > 0 ? 'Закрыть' : 'Отмена' }}
              </button>
              <button v-if="uploadResults.length === 0" @click="doUpload"
                :disabled="!uploadFolderName || uploadFiles.length === 0 || uploading"
                class="px-5 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2">
                <svg v-if="uploading" class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
                {{ uploading ? 'Загрузка...' : 'Загрузить' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Run phenotyping modal (2-step: solution → folder) -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showRunModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showRunModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl slide-up max-h-[90vh] overflow-hidden flex flex-col">
            <div class="px-6 pt-5 pb-4 border-b border-(--color-border-subtle)">
              <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary)">Запуск фенотипирования</h2>
              <div class="flex gap-4 mt-3">
                <span :class="['text-xs font-medium', runStep >= 0 ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)']">1. Решение</span>
                <span :class="['text-xs font-medium', runStep >= 1 ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)']">2. Папка</span>
                <span :class="['text-xs font-medium', runStep >= 2 ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)']">3. Результат</span>
              </div>
            </div>
            <div class="flex-1 overflow-y-auto p-6">
              <!-- Step 0: Select solution -->
              <div v-if="runStep === 0" class="space-y-2">
                <p class="text-xs text-(--color-text-muted) mb-3">Выберите фенотипическое решение для анализа</p>
                <div v-if="solutions.length > 0" class="space-y-2">
                  <button v-for="sol in solutions" :key="sol.id" @click="selectedSolution = sol.id"
                    :class="['w-full p-4 rounded-xl border text-left transition-all',
                      selectedSolution === sol.id ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
                    <div class="flex items-center gap-3">
                      <div :class="['w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                        selectedSolution === sol.id ? 'bg-(--color-accent-green)/20' : 'bg-(--color-bg-elevated)']">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" :class="selectedSolution === sol.id ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)'" stroke-linecap="round">
                          <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27,6.96 12,12.01 20.73,6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>
                        </svg>
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                          <h4 class="text-sm font-medium text-(--color-text-primary)">{{ sol.name }}</h4>
                          <span class="text-[10px] font-mono text-(--color-text-muted)">v{{ sol.version }}</span>
                          <span v-if="sol.imageBuilt" class="px-1.5 py-0.5 rounded text-[9px] bg-(--color-accent-green)/10 text-(--color-accent-green)">готово</span>
                          <span v-else class="px-1.5 py-0.5 rounded text-[9px] bg-(--color-accent-amber)/10 text-(--color-accent-amber)">не собрано</span>
                        </div>
                        <p class="text-xs text-(--color-text-muted) mt-0.5 line-clamp-1">{{ sol.description }}</p>
                        <div v-if="sol.outputVariables && sol.outputVariables.length" class="flex gap-1.5 mt-1.5">
                          <span v-for="ov in sol.outputVariables" :key="ov.coTermId" class="px-1.5 py-0.5 rounded text-[9px] bg-(--color-accent-sky)/10 text-(--color-accent-sky) font-mono">{{ ov.coTermId }} ({{ ov.unit }})</span>
                        </div>
                      </div>
                    </div>
                  </button>
                </div>
                <div v-else class="text-center py-8 text-sm text-(--color-text-muted)">
                  Нет доступных решений. Создайте решение в разделе «Фенотипические решения».
                </div>
              </div>

              <!-- Step 1: Select folder -->
              <div v-if="runStep === 1" class="space-y-2">
                <p class="text-xs text-(--color-text-muted) mb-3">
                  Решение: <span class="text-(--color-accent-green) font-medium">{{ selectedSolutionObj?.name }}</span>
                  — выберите папку для анализа
                </p>
                <div v-if="Object.keys(imageFolders).length > 0" class="space-y-2">
                  <button v-for="(imgs, folder) in imageFolders" :key="folder" @click="selectedRunFolder = folder"
                    :class="['w-full p-4 rounded-xl border text-left transition-all',
                      selectedRunFolder === folder ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30' : 'bg-(--color-bg-base) border-(--color-border-subtle) hover:border-(--color-border-default)']">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-3">
                        <div :class="['w-4 h-4 rounded-full border-2 flex items-center justify-center',
                          selectedRunFolder === folder ? 'border-(--color-accent-green) bg-(--color-accent-green)' : 'border-(--color-text-muted)']">
                          <svg v-if="selectedRunFolder === folder" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" class="text-(--color-text-inverse)" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                        </div>
                        <div>
                          <p class="text-sm font-medium text-(--color-text-primary)">{{ folder }}</p>
                          <p class="text-xs text-(--color-text-muted)">{{ imgs.length }} изображений</p>
                        </div>
                      </div>
                      <span v-if="folderRuns(folder).length > 0" class="text-[10px] text-(--color-text-muted)">{{ folderRuns(folder).length }} предыдущих анализов</span>
                    </div>
                  </button>
                </div>
                <div v-else class="text-center py-8 text-sm text-(--color-text-muted)">Нет загруженных изображений.</div>
              </div>

              <!-- Step 2: Running / Done -->
              <div v-if="runStep === 2" class="space-y-4">
                <div v-if="runningPhenotyping" class="text-center py-8">
                  <svg class="animate-spin w-8 h-8 text-(--color-accent-green) mx-auto mb-3" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
                  <p class="text-sm text-(--color-text-primary)">Выполняется анализ...</p>
                  <p class="text-xs text-(--color-text-muted) mt-1">{{ selectedSolutionObj?.name }} → {{ selectedRunFolder }}</p>
                </div>
                <div v-else-if="runResult" class="space-y-3">
                  <div :class="['rounded-lg p-4 border', runResult.startsWith('Ошибка') ? 'bg-(--color-accent-rose)/5 border-(--color-accent-rose)/20' : 'bg-(--color-accent-green)/5 border-(--color-accent-green)/20']">
                    <p :class="['text-sm', runResult.startsWith('Ошибка') ? 'text-(--color-accent-rose)' : 'text-(--color-accent-green)']">{{ runResult }}</p>
                  </div>
                  <div class="bg-(--color-bg-base) rounded-lg p-4 border border-(--color-border-subtle)">
                    <p class="text-xs text-(--color-text-muted) mb-1">Решение</p>
                    <p class="text-sm text-(--color-text-primary)">{{ selectedSolutionObj?.name }}</p>
                    <p class="text-xs text-(--color-text-muted) mt-2 mb-1">Папка</p>
                    <p class="text-sm text-(--color-text-primary)">{{ selectedRunFolder }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-(--color-border-subtle) flex justify-between">
              <button v-if="runStep === 2 && runningPhenotyping" @click="showRunModal = false"
                class="px-4 py-2 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="4,14 10,14 10,20"/><polyline points="20,10 14,10 14,4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                Свернуть
              </button>
              <button v-else @click="runStep > 0 && runStep < 2 ? runStep-- : (showRunModal = false)"
                class="px-4 py-2 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">
                {{ runStep === 0 || runStep === 2 ? 'Закрыть' : 'Назад' }}
              </button>
              <button v-if="runStep < 2" @click="runNextStep"
                :disabled="(runStep === 0 && !selectedSolution) || (runStep === 1 && !selectedRunFolder)"
                class="px-5 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2">
                <svg v-if="runStep === 1" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="5,3 19,12 5,21 5,3"/></svg>
                {{ runStep === 0 ? 'Далее' : 'Запустить анализ' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Per-plant upload modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showPlantUploadModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closePlantUpload"></div>
          <div class="relative w-full max-w-xl mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl slide-up max-h-[90vh] overflow-hidden flex flex-col">
            <div class="px-6 pt-5 pb-4 border-b border-(--color-border-subtle)">
              <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary)">Фото для {{ plantUploadTarget?.name }}</h2>
              <p class="text-xs text-(--color-text-muted) mt-1">Изображения будут привязаны к этому растению</p>
            </div>
            <div class="flex-1 overflow-y-auto p-6 space-y-5">
              <!-- Folder selection -->
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Папка</label>
                <div v-if="Object.keys(imageFolders).length > 0" class="flex flex-wrap gap-2 mb-2">
                  <button v-for="(_, folder) in imageFolders" :key="folder" @click="plantUploadFolder = folder"
                    :class="['px-3 py-1.5 rounded-lg border text-xs transition-all',
                      plantUploadFolder === folder ? 'bg-(--color-accent-green)/10 border-(--color-accent-green)/30 text-(--color-accent-green)' : 'bg-(--color-bg-base) border-(--color-border-subtle) text-(--color-text-secondary) hover:border-(--color-border-default)']">
                    {{ folder }}
                  </button>
                </div>
                <input v-model="plantUploadFolder" type="text" placeholder="Или введите новое название папки" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>

              <!-- Drop zone -->
              <div v-if="plantUploadResults.length === 0"
                @drop="handlePlantDrop" @dragover.prevent
                class="border-2 border-dashed border-(--color-border-default) rounded-xl p-6 text-center hover:border-(--color-accent-green)/30 transition-colors">
                <label class="cursor-pointer">
                  <input type="file" multiple accept="image/*" class="hidden" @change="handlePlantFileSelect" />
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="mx-auto text-(--color-text-muted) mb-2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  <p class="text-sm text-(--color-text-secondary)">Перетащите или выберите файлы</p>
                </label>
              </div>

              <!-- Selected files -->
              <div v-if="plantUploadFiles.length > 0 && plantUploadResults.length === 0" class="space-y-1">
                <p class="text-xs text-(--color-text-muted)">{{ plantUploadFiles.length }} файлов</p>
                <div class="max-h-40 overflow-y-auto space-y-1">
                  <div v-for="(f, idx) in plantUploadFiles" :key="idx"
                    class="flex items-center justify-between px-3 py-2 bg-(--color-bg-base) border border-(--color-border-subtle) rounded-lg text-xs">
                    <span class="font-mono text-(--color-text-primary) truncate">{{ f.name }}</span>
                    <button @click="removePlantFile(idx)" class="p-1 text-(--color-text-muted) hover:text-(--color-accent-rose) transition-colors flex-shrink-0">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Results -->
              <div v-if="plantUploadResults.length > 0" class="flex items-center gap-2 text-(--color-accent-green)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20,6 9,17 4,12"/></svg>
                <span class="text-sm font-medium">Загружено {{ plantUploadResults.length }} файлов</span>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-(--color-border-subtle) flex justify-between">
              <button @click="closePlantUpload" class="px-4 py-2 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">
                {{ plantUploadResults.length > 0 ? 'Закрыть' : 'Отмена' }}
              </button>
              <button v-if="plantUploadResults.length === 0" @click="doPlantUpload"
                :disabled="!plantUploadFolder || plantUploadFiles.length === 0 || plantUploading"
                class="px-5 py-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2">
                <svg v-if="plantUploading" class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
                {{ plantUploading ? 'Загрузка...' : 'Загрузить' }}
              </button>
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
