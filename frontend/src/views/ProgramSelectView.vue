<!--
  Full-screen program selector — separate page for switching programs
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useProgram } from '@/composables/useProgram'

const router = useRouter()
const api = useApi()
const { currentProgram, setProgram } = useProgram()

const programs = ref<any[]>([])
const loading = ref(true)
const showCreate = ref(false)
const creating = ref(false)
const newProgram = ref({ name: '', abbreviation: '', crop: '', objective: '', leadPerson: '' })

onMounted(async () => {
  try {
    programs.value = await api.get<any[]>('/programs')
  } catch {}
  loading.value = false
})

function selectAndGo(p: any) {
  setProgram({ id: p.id, name: p.name, abbreviation: p.abbreviation || '' })
  router.push('/dashboard')
}

async function createProgram() {
  creating.value = true
  try {
    const p = await api.post<any>('/programs', {
      name: newProgram.value.name,
      abbreviation: newProgram.value.abbreviation,
      crop: newProgram.value.crop,
      objective: newProgram.value.objective,
      lead_person: newProgram.value.leadPerson,
    })
    programs.value.push(p)
    showCreate.value = false
    newProgram.value = { name: '', abbreviation: '', crop: '', objective: '', leadPerson: '' }
    // Auto-select new program
    selectAndGo(p)
  } catch {}
  creating.value = false
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 fade-in">
    <div class="w-full max-w-2xl">
      <div class="text-center mb-8">
        <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-(--color-accent-green) to-(--color-accent-green-dim) flex items-center justify-center mx-auto mb-4">
          <span class="material-symbols-outlined text-(--color-text-inverse)" style="font-size: 28px">eco</span>
        </div>
        <h1 class="font-(family-name:--font-display) text-2xl text-(--color-text-primary)">Выберите программу</h1>
        <p class="text-sm text-(--color-text-muted) mt-1">Исследовательская программа определяет контекст работы</p>
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-20 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl animate-pulse"></div>
      </div>

      <div v-else class="space-y-3">
        <button v-for="p in programs" :key="p.id" @click="selectAndGo(p)"
          :class="['w-full p-5 rounded-xl border text-left transition-all group',
            currentProgram?.id === p.id
              ? 'bg-(--color-accent-green)/5 border-(--color-accent-green)/30'
              : 'bg-(--color-bg-surface) border-(--color-border-subtle) hover:border-(--color-border-default) hover:bg-(--color-bg-hover)']">
          <div class="flex items-center gap-4">
            <div :class="['w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
              currentProgram?.id === p.id ? 'bg-(--color-accent-green)/20' : 'bg-(--color-bg-elevated)']">
              <span :class="['text-sm font-mono font-bold',
                currentProgram?.id === p.id ? 'text-(--color-accent-green)' : 'text-(--color-text-muted)']">{{ p.abbreviation }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-medium text-(--color-text-primary)">{{ p.name }}</h3>
                <span v-if="currentProgram?.id === p.id" class="px-2 py-0.5 rounded-full text-[10px] bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20">Текущая</span>
              </div>
              <p class="text-xs text-(--color-text-muted) mt-0.5">{{ p.crop }} · {{ p.lead_person || p.leadPerson }}</p>
              <p v-if="p.objective" class="text-xs text-(--color-text-secondary) mt-1 line-clamp-1">{{ p.objective }}</p>
            </div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted) group-hover:text-(--color-accent-green) transition-colors flex-shrink-0" stroke-linecap="round"><polyline points="9,6 15,12 9,18"/></svg>
          </div>
        </button>

        <!-- Create new -->
        <button v-if="!showCreate" @click="showCreate = true"
          class="w-full p-5 rounded-xl border-2 border-dashed border-(--color-border-default) text-center hover:border-(--color-accent-green)/30 hover:bg-(--color-bg-surface) transition-all group">
          <div class="flex items-center justify-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted) group-hover:text-(--color-accent-green) transition-colors" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            <span class="text-sm text-(--color-text-muted) group-hover:text-(--color-text-primary) transition-colors">Создать программу</span>
          </div>
        </button>

        <!-- Create form -->
        <div v-if="showCreate" class="bg-(--color-bg-surface) border border-(--color-border-default) rounded-xl p-6">
          <h3 class="text-sm font-medium text-(--color-text-primary) mb-4">Новая программа</h3>
          <form @submit.prevent="createProgram" class="space-y-4">
            <div>
              <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название</label>
              <input v-model="newProgram.name" type="text" required placeholder="Полное название программы" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Аббревиатура</label>
                <input v-model="newProgram.abbreviation" type="text" required placeholder="ABC" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Культура</label>
                <input v-model="newProgram.crop" type="text" required placeholder="Triticum aestivum" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
            </div>
            <div>
              <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Цель</label>
              <textarea v-model="newProgram.objective" rows="2" placeholder="Описание цели программы" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-none"></textarea>
            </div>
            <div>
              <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Руководитель</label>
              <input v-model="newProgram.leadPerson" type="text" required placeholder="Фамилия И.О." class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
            </div>
            <div class="flex gap-3 pt-1">
              <button type="button" @click="showCreate = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
              <button type="submit" :disabled="creating" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">
                {{ creating ? 'Создание...' : 'Создать' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
