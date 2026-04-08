<!--
  Programs with accordion pattern + delete button + create trial
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAuth } from '@/composables/useAuth'

const api = useApi()
const { user } = useAuth()
const isAdmin = computed(() => user.value?.role === 'admin')
const programs = ref<any[]>([])
const expandedProgram = ref<string | null>(null)
const showCreateModal = ref(false)
const showTrialModal = ref(false)
const trialProgramId = ref<string | null>(null)
const loading = ref(true)
const creating = ref(false)
const creatingTrial = ref(false)
const deleting = ref<string | null>(null)

const newProgram = ref({ name: '', abbreviation: '', crop: '', objective: '', leadPerson: '' })
const newTrial = ref({ name: '', description: '', startDate: '', endDate: '' })

onMounted(async () => {
  try {
    const data = await api.get<any[]>('/programs')
    programs.value = data
    if (data.length > 0) expandedProgram.value = data[0].id
  } catch {}
  loading.value = false
})

function toggle(id: string) {
  expandedProgram.value = expandedProgram.value === id ? null : id
}

function openTrialModal(programId: string, e: Event) {
  e.stopPropagation()
  trialProgramId.value = programId
  newTrial.value = { name: '', description: '', startDate: '', endDate: '' }
  showTrialModal.value = true
}

async function createTrial() {
  if (!trialProgramId.value) return
  creatingTrial.value = true
  try {
    const trial = await api.post<any>('/trials', {
      name: newTrial.value.name,
      description: newTrial.value.description,
      programId: trialProgramId.value,
      startDate: newTrial.value.startDate,
      endDate: newTrial.value.endDate,
      active: true,
    })
    const prog = programs.value.find(p => p.id === trialProgramId.value)
    if (prog) {
      if (!prog.trials) prog.trials = []
      prog.trials.push(trial)
    }
    showTrialModal.value = false
  } catch {}
  creatingTrial.value = false
}

async function deleteProgram(id: string, e: Event) {
  e.stopPropagation()
  if (!confirm('Удалить программу?')) return
  deleting.value = id
  try {
    await api.del('/programs/' + id)
    programs.value = programs.value.filter(p => p.id !== id)
    if (expandedProgram.value === id) expandedProgram.value = null
  } catch {}
  deleting.value = null
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
    showCreateModal.value = false
    newProgram.value = { name: '', abbreviation: '', crop: '', objective: '', leadPerson: '' }
    expandedProgram.value = p.id
  } catch {}
  creating.value = false
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <div class="flex items-end justify-between">
      <div>
        <h1 class="font-(family-name:--font-display) text-3xl text-(--color-text-primary)">Исследовательские программы</h1>
        <p class="text-sm text-(--color-text-secondary) mt-1">Управление программами и экспериментами по стандарту BrAPI</p>
      </div>
      <button @click="showCreateModal = true" class="px-4 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 active:scale-[0.98] transition-all flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Новая программа
      </button>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl p-5 animate-pulse">
        <div class="h-4 bg-(--color-bg-elevated) rounded w-1/3"></div>
        <div class="h-3 bg-(--color-bg-elevated) rounded w-1/2 mt-2"></div>
      </div>
    </div>

    <div v-else class="space-y-3">
      <div v-for="program in programs" :key="program.id"
        class="bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl overflow-hidden transition-colors"
        :class="expandedProgram === program.id ? 'border-(--color-border-default)' : ''">
        <div @click="toggle(program.id)" class="px-5 py-4 flex items-center gap-4 cursor-pointer hover:bg-(--color-bg-hover) transition-colors">
          <div class="w-10 h-10 rounded-lg bg-(--color-accent-green)/10 flex items-center justify-center flex-shrink-0">
            <span class="text-xs font-mono font-bold text-(--color-accent-green)">{{ program.abbreviation }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-sm font-medium text-(--color-text-primary)">{{ program.name }}</h3>
            <p class="text-xs text-(--color-text-muted) mt-0.5">
              {{ program.crop }} &middot; Руководитель: {{ program.lead_person || program.leadPerson }}
            </p>
          </div>
          <div class="flex items-center gap-3 flex-shrink-0">
            <span class="text-xs text-(--color-text-muted)">{{ (program.trials || []).length }} испытаний</span>
            <button @click="deleteProgram(program.id, $event)" :disabled="deleting === program.id"
              class="p-1.5 rounded-lg text-(--color-text-muted) hover:text-(--color-accent-rose) hover:bg-(--color-accent-rose)/10 transition-all disabled:opacity-30"
              title="Удалить программу">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/></svg>
            </button>
            <button v-if="isAdmin" @click="deleteProgram(program.id, $event)" :disabled="deleting === program.id"
              class="p-1.5 rounded-lg text-(--color-text-muted) hover:text-(--color-accent-rose) hover:bg-(--color-accent-rose)/10 transition-all disabled:opacity-30"
              title="Удалить программу">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/></svg>
            </button>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-muted) transition-transform duration-200" :class="expandedProgram === program.id ? 'rotate-180' : ''" stroke-linecap="round">
              <polyline points="6,9 12,15 18,9"/>
            </svg>
          </div>
        </div>

        <transition name="expand">
          <div v-if="expandedProgram === program.id">
            <div class="px-5 pb-2 border-t border-(--color-border-subtle) flex items-center justify-between">
              <p class="text-xs text-(--color-text-secondary) py-3 flex-1">{{ program.objective }}</p>
              <button @click="openTrialModal(program.id, $event)"
                class="ml-3 px-3 py-1.5 rounded-lg text-xs font-medium bg-(--color-accent-green)/10 text-(--color-accent-green) border border-(--color-accent-green)/20 hover:bg-(--color-accent-green)/20 transition-colors flex items-center gap-1.5 flex-shrink-0">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Новое испытание
              </button>
            </div>

            <div v-if="(program.trials || []).length > 0" class="px-5 pb-4">
              <p class="text-[10px] uppercase tracking-wider text-(--color-text-muted) mb-2">Испытания</p>
              <div class="space-y-2">
                <router-link v-for="trial in program.trials" :key="trial.id" :to="'/programs/' + program.id + '/trials/' + trial.id"
                  class="block bg-(--color-bg-base) border border-(--color-border-subtle) rounded-lg p-4 hover:border-(--color-border-default) hover:bg-(--color-bg-elevated) transition-all group">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <span :class="['w-2 h-2 rounded-full flex-shrink-0', trial.active ? 'bg-(--color-accent-green)' : 'bg-(--color-text-muted)']" />
                      <div>
                        <h4 class="text-sm font-medium text-(--color-text-primary) group-hover:text-(--color-accent-green) transition-colors">{{ trial.name }}</h4>
                        <p class="text-xs text-(--color-text-muted) mt-0.5">
                          {{ trial.start_date || trial.startDate }} — {{ trial.end_date || trial.endDate }} &middot; {{ (trial.studies || []).length }} экспериментов
                        </p>
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <span :class="['px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border', trial.active ? 'bg-(--color-accent-green)/10 text-(--color-accent-green) border-(--color-accent-green)/20' : 'bg-(--color-bg-elevated) text-(--color-text-muted) border-(--color-border-subtle)']"
                      >{{ trial.active ? 'Активно' : 'Завершено' }}</span>
                      <button v-if="isAdmin" @click.prevent.stop="deleteTrial(program.id, trial.id)"
                        class="p-1 rounded text-(--color-text-muted) hover:text-(--color-accent-rose) hover:bg-(--color-accent-rose)/10 transition-all"
                        title="Удалить испытание">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/></svg>
                      </button>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-(--color-text-muted) group-hover:text-(--color-accent-green) transition-all" stroke-linecap="round"><polyline points="9,6 15,12 9,18"/></svg>
                    </div>
                  </div>
                </router-link>
              </div>
            </div>

            <div v-else class="px-5 pb-5">
              <div class="text-center py-6 text-sm text-(--color-text-muted) bg-(--color-bg-base) rounded-lg border border-dashed border-(--color-border-default)">
                Нет испытаний. Создайте первое испытание для этой программы.
              </div>
            </div>
          </div>
        </transition>
      </div>

      <div v-if="programs.length === 0 && !loading" class="text-center py-16 bg-(--color-bg-surface) border border-(--color-border-subtle) rounded-xl">
        <p class="text-sm text-(--color-text-muted)">Нет программ. Создайте первую программу.</p>
      </div>
    </div>

    <!-- Create Program Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreateModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-5">Новая программа</h2>
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
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Цель исследования</label>
                <textarea v-model="newProgram.objective" rows="3" placeholder="Описание цели программы" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-none"></textarea>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Руководитель</label>
                <input v-model="newProgram.leadPerson" type="text" required placeholder="Фамилия И.О." class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
              <div class="flex gap-3 pt-2">
                <button type="button" @click="showCreateModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
                <button type="submit" :disabled="creating" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">
                  {{ creating ? 'Создание...' : 'Создать' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Create Trial Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showTrialModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showTrialModal = false"></div>
          <div class="relative w-full max-w-lg mx-4 bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-6 slide-up">
            <h2 class="font-(family-name:--font-display) text-xl text-(--color-text-primary) mb-5">Новое испытание</h2>
            <form @submit.prevent="createTrial" class="space-y-4">
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Название</label>
                <input v-model="newTrial.name" type="text" required placeholder="Название испытания" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
              </div>
              <div>
                <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Описание</label>
                <textarea v-model="newTrial.description" rows="3" placeholder="Описание испытания" class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 transition-all resize-none"></textarea>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Дата начала</label>
                  <input v-model="newTrial.startDate" type="date" required class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                </div>
                <div>
                  <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Дата окончания</label>
                  <input v-model="newTrial.endDate" type="date" required class="w-full px-4 py-2.5 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) focus:outline-none focus:border-(--color-accent-green)/50 transition-all"/>
                </div>
              </div>
              <div class="flex gap-3 pt-2">
                <button type="button" @click="showTrialModal = false" class="flex-1 py-2.5 rounded-lg text-sm text-(--color-text-secondary) border border-(--color-border-default) hover:bg-(--color-bg-hover) transition-colors">Отмена</button>
                <button type="submit" :disabled="creatingTrial" class="flex-1 py-2.5 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-50">
                  {{ creatingTrial ? 'Создание...' : 'Создать' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.expand-enter-active, .expand-leave-active { transition: all 0.25s ease; overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
