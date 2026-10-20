<!--
  Analysis of the two extracted traits (plant height, projected leaf area):
  group statistics, Welch's t-test against control, dynamics by capture date,
  per-plant growth rates and height/area correlation. Data: GET /studies/:id/trait-summary
-->
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import { useApi } from '@/composables/useApi'

Chart.register(...registerables)

const props = defineProps<{ studyId: string; refreshKey?: number }>()
const api = useApi()

const summary = ref<any>(null)
const loading = ref(true)
const error = ref('')
const canvases = ref<Record<string, HTMLCanvasElement | null>>({})
const charts: Chart[] = []
const colors = ['#4ADE80', '#FBBF24', '#38BDF8', '#FB7185', '#A78BFA', '#14B8A6']

function fmt(v: number | null | undefined, digits = 2) {
  return v === null || v === undefined ? '—' : v.toFixed(digits).replace('.', ',')
}
function fmtP(p: number | null | undefined) {
  if (p === null || p === undefined) return '—'
  return p < 0.0001 ? '< 0,0001' : fmt(p, 4)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    summary.value = await api.get<any>(`/studies/${props.studyId}/trait-summary`)
  } catch (e: any) {
    error.value = e.message || 'Не удалось загрузить статистику'
  }
  loading.value = false
  await nextTick()
  drawCharts()
}

function drawCharts() {
  charts.splice(0).forEach(c => c.destroy())
  if (!summary.value) return
  for (const trait of summary.value.traits) {
    const canvas = canvases.value[trait.key]
    if (!canvas || trait.dynamics.length === 0) continue
    const labels = trait.dynamics.map((d: any) => d.date)
    const groups = trait.dynamicsByTreatment.length > 1
      ? trait.dynamicsByTreatment
      : [{ treatment: 'Все растения', points: trait.dynamics }]
    const datasets = groups.map((g: any, i: number) => {
      const byDate = Object.fromEntries(g.points.map((p: any) => [p.date, p.mean]))
      return {
        label: g.treatment,
        data: labels.map((d: string) => byDate[d] ?? null),
        borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length] + '30',
        spanGaps: true,
      }
    })
    charts.push(new Chart(canvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: '#8FA399', usePointStyle: true, pointStyle: 'circle', font: { size: 11 } } },
          tooltip: { backgroundColor: '#1A2320', titleColor: '#E4EBE7', bodyColor: '#8FA399', borderColor: '#2A3A33', borderWidth: 1 },
        },
        scales: {
          x: { grid: { color: '#1E2B26' }, ticks: { color: '#5A7068', font: { size: 10 } } },
          y: { beginAtZero: true, grid: { color: '#1E2B26' }, ticks: { color: '#5A7068', font: { size: 10 } },
               title: { display: true, text: trait.unit, color: '#5A7068' } },
        },
        elements: { point: { radius: 3, hoverRadius: 6 }, line: { tension: 0.25, borderWidth: 2 } },
      },
    }))
  }
}

onMounted(load)
watch(() => props.refreshKey, load)
onBeforeUnmount(() => charts.splice(0).forEach(c => c.destroy()))
</script>

<template>
  <div class="space-y-5">
    <div v-if="loading" class="h-40 bg-(--color-bg-surface) rounded-xl animate-pulse"></div>
    <div v-else-if="error" class="p-4 rounded-xl border border-(--color-accent-rose)/20 bg-(--color-accent-rose)/5 text-sm text-(--color-accent-rose)">{{ error }}</div>
    <div v-else-if="!summary || summary.records === 0" class="text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
      <p class="text-sm text-(--color-text-muted)">Нет измерений высоты и площади листьев</p>
      <p class="text-xs text-(--color-text-muted) mt-1">Запустите фенотипирование, чтобы получить статистику</p>
    </div>
    <template v-else>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
          <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Изображений</span>
          <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ summary.images }}</p>
        </div>
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
          <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Растений</span>
          <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ summary.plants }}</p>
        </div>
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4">
          <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Дат съёмки</span>
          <p class="text-xl font-semibold text-(--color-text-primary) mt-1">{{ summary.dates.length }}</p>
        </div>
        <div class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-4" title="Корреляция Пирсона между высотой и площадью на одном изображении">
          <span class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">r (высота ~ площадь)</span>
          <p class="text-xl font-semibold text-(--color-text-primary) mt-1">
            {{ summary.correlation ? fmt(summary.correlation.r, 3) : '—' }}
            <span v-if="summary.correlation" class="text-xs font-normal text-(--color-text-muted)">p {{ fmtP(summary.correlation.pValue).startsWith('<') ? '' : '=' }} {{ fmtP(summary.correlation.pValue) }}</span>
          </p>
        </div>
      </div>

      <div v-for="trait in summary.traits" :key="trait.key" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden">
        <div class="px-5 py-4 border-b border-(--color-border-subtle) flex items-center justify-between">
          <h3 class="text-sm font-medium text-(--color-text-primary)">{{ trait.name }}, {{ trait.unit }}</h3>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-(--color-accent-sky)/10 text-(--color-accent-sky)">{{ trait.coTermId }}</span>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-0">
          <div class="p-5 space-y-4 lg:border-r border-(--color-border-subtle)">
            <table class="w-full text-xs">
              <thead><tr class="border-b border-(--color-border-subtle) text-[10px] uppercase text-(--color-text-muted)">
                <th class="py-2 text-left">Группа</th><th class="py-2 text-right">n</th><th class="py-2 text-right">Среднее ± SD</th>
                <th class="py-2 text-right">Мин–макс</th><th class="py-2 text-right">CV, %</th><th class="py-2 text-right">95% ДИ</th>
              </tr></thead>
              <tbody class="divide-y divide-(--color-border-subtle)">
                <tr v-for="g in [{ treatment: 'Все растения', ...trait.overall }, ...trait.byTreatment]" :key="g.treatment">
                  <td class="py-1.5 text-(--color-text-secondary)">{{ g.treatment }}</td>
                  <td class="py-1.5 text-right font-mono">{{ g.n }}</td>
                  <td class="py-1.5 text-right font-mono text-(--color-accent-green)">{{ fmt(g.mean) }} ± {{ fmt(g.sd) }}</td>
                  <td class="py-1.5 text-right font-mono text-(--color-text-muted)">{{ fmt(g.min, 1) }}–{{ fmt(g.max, 1) }}</td>
                  <td class="py-1.5 text-right font-mono text-(--color-text-muted)">{{ fmt(g.cv, 1) }}</td>
                  <td class="py-1.5 text-right font-mono text-(--color-text-muted)">{{ g.ci95Low === null ? '—' : fmt(g.ci95Low) + '…' + fmt(g.ci95High) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="trait.comparisons.length" class="text-[10px] uppercase tracking-wider text-(--color-text-muted)">Сравнение с контролем, все даты</p>
            <div v-for="c in trait.comparisons" :key="c.group"
              :class="['px-3 py-2 rounded-lg text-xs border', c.significant ? 'border-(--color-accent-green)/20 bg-(--color-accent-green)/5' : 'border-(--color-border-subtle) bg-(--color-bg-base)']">
              <span class="text-(--color-text-primary)">{{ c.group }}</span>
              <span class="text-(--color-text-muted)"> vs {{ c.reference }}: Δ = {{ fmt(c.meanDiff) }} {{ trait.unit }}, t = {{ fmt(c.t) }}, df = {{ fmt(c.df, 1) }}, p {{ fmtP(c.pValue).startsWith('<') ? '' : '=' }} {{ fmtP(c.pValue) }}</span>
              <span :class="c.significant ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)'"> — {{ c.significant ? 'различие значимо' : 'различие не значимо' }}</span>
            </div>
            <div v-if="trait.comparisonsByDate?.length" class="text-xs">
              <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mb-1">По датам съёмки</p>
              <table class="w-full">
                <thead><tr class="text-[10px] uppercase text-(--color-text-muted)">
                  <th class="py-1 text-left">Дата</th><th class="py-1 text-left">Группа</th>
                  <th class="py-1 text-right">Δ, {{ trait.unit }}</th><th class="py-1 text-right">p</th>
                </tr></thead>
                <tbody class="divide-y divide-(--color-border-subtle)">
                  <tr v-for="c in trait.comparisonsByDate" :key="c.date + c.group">
                    <td class="py-1 font-mono text-(--color-text-secondary)">{{ c.date }}</td>
                    <td class="py-1 text-(--color-text-muted)">{{ c.group }}</td>
                    <td class="py-1 text-right font-mono">{{ fmt(c.meanDiff) }}</td>
                    <td :class="['py-1 text-right font-mono', c.significant ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)']">{{ fmtP(c.pValue) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <details v-if="trait.growth.length" class="text-xs">
              <summary class="cursor-pointer text-(--color-accent-green)">Скорость роста по растениям ({{ trait.growth.length }})</summary>
              <table class="w-full mt-2">
                <thead><tr class="text-[10px] uppercase text-(--color-text-muted)">
                  <th class="py-1 text-left">Растение</th><th class="py-1 text-left">Обработка</th><th class="py-1 text-right">Дней</th>
                  <th class="py-1 text-right">{{ trait.unit }}/сут</th><th class="py-1 text-right">RGR, 1/сут</th>
                </tr></thead>
                <tbody class="divide-y divide-(--color-border-subtle)">
                  <tr v-for="g in trait.growth" :key="g.plant">
                    <td class="py-1 text-(--color-text-secondary)">{{ g.plant }}</td>
                    <td class="py-1 text-(--color-text-muted)">{{ g.treatment }}</td>
                    <td class="py-1 text-right font-mono">{{ g.days }}</td>
                    <td class="py-1 text-right font-mono text-(--color-accent-green)">{{ fmt(g.agr, 3) }}</td>
                    <td class="py-1 text-right font-mono">{{ fmt(g.rgr, 4) }}</td>
                  </tr>
                </tbody>
              </table>
            </details>
          </div>
          <div class="p-5">
            <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mb-2">Динамика: среднее по дате съёмки</p>
            <div class="h-64"><canvas :ref="el => (canvases[trait.key] = el as HTMLCanvasElement | null)"></canvas></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
