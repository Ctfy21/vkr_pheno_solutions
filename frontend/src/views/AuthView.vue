<!--
  Design approach: MINIMAL
  Auth is a focused, single-task screen. Maximum whitespace, minimum cognitive load.
  Only essential elements: logo, mode toggle, form fields, submit button.
  Decorative elements (botanical SVG, gradient blurs, dot-grid) add atmosphere without distraction.
  No sidebar, no header — full-screen immersive entry point.
-->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { login, register } = useAuth()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const name = ref('')
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    let ok: boolean
    if (mode.value === 'login') {
      ok = await login(email.value, password.value)
    } else {
      ok = await register(name.value, email.value, password.value)
    }
    if (ok) {
      router.push('/dashboard')
    } else {
      error.value = mode.value === 'login' ? 'Неверный email или пароль' : 'Ошибка регистрации'
    }
  } catch (e: any) {
    error.value = e.message || 'Ошибка соединения с сервером'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-(--color-bg-root) flex items-center justify-center relative overflow-hidden">
    <!-- Background effects -->
    <div class="absolute inset-0 hex-grid-bg"></div>
    <div class="absolute inset-0 dot-grid opacity-[0.03]"></div>

    <!-- Decorative blurs -->
    <div class="absolute top-[15%] left-[10%] w-72 h-72 rounded-full bg-(--color-accent-green)/[0.03] blur-[80px]"></div>
    <div class="absolute bottom-[20%] right-[15%] w-96 h-96 rounded-full bg-(--color-accent-sky)/[0.02] blur-[100px]"></div>

    <!-- Botanical line art -->
    <svg class="absolute top-[20%] right-[20%] opacity-[0.06] w-48 h-48 text-(--color-accent-green)" viewBox="0 0 200 200" fill="none" stroke="currentColor" stroke-width="0.5">
      <path d="M100 180 C100 120 60 80 30 40" stroke-linecap="round"/>
      <path d="M100 180 C100 130 130 90 160 50" stroke-linecap="round"/>
      <path d="M100 140 C80 120 50 110 30 100" stroke-linecap="round"/>
      <path d="M100 140 C120 120 145 115 165 105" stroke-linecap="round"/>
      <path d="M100 100 C85 85 60 80 40 75" stroke-linecap="round"/>
      <path d="M100 100 C115 85 140 82 155 78" stroke-linecap="round"/>
    </svg>

    <!-- Auth card -->
    <div class="relative w-full max-w-md mx-4 slide-up">
      <div class="glow-line mb-8"></div>

      <div class="bg-(--color-bg-surface) border border-(--color-border-default) rounded-2xl p-8 backdrop-blur-sm">
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="w-14 h-14 mx-auto mb-5 rounded-xl bg-gradient-to-br from-(--color-accent-green) to-(--color-accent-green-dim) flex items-center justify-center glow-green">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-(--color-text-inverse)">
              <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c1.8 0 3.5-.5 5-1.3" stroke-linecap="round"/>
              <path d="M12 2c3 3 4.5 6.5 4.5 10s-1.5 7-4.5 10" stroke-linecap="round"/>
              <path d="M17.5 6.5C19 8 20 10 20 12" stroke-linecap="round"/>
              <path d="M8 3.5c2 1 3.5 3 4 5.5" stroke-linecap="round"/>
            </svg>
          </div>
          <h2 class="font-(family-name:--font-display) text-2xl text-(--color-text-primary)">PhenoPlant</h2>
          <p class="text-sm text-(--color-text-muted) mt-1">Платформа цифрового фенотипирования</p>
        </div>

        <!-- Tab switcher -->
        <div class="flex mb-6 bg-(--color-bg-base) rounded-lg p-1">
          <button
            @click="mode = 'login'; error = ''"
            :class="[
              'flex-1 py-2 text-sm rounded-md transition-all duration-200',
              mode === 'login'
                ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm'
                : 'text-(--color-text-muted) hover:text-(--color-text-secondary)',
            ]"
          >Вход</button>
          <button
            @click="mode = 'register'; error = ''"
            :class="[
              'flex-1 py-2 text-sm rounded-md transition-all duration-200',
              mode === 'register'
                ? 'bg-(--color-bg-elevated) text-(--color-text-primary) shadow-sm'
                : 'text-(--color-text-muted) hover:text-(--color-text-secondary)',
            ]"
          >Регистрация</button>
        </div>

        <!-- Error -->
        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-(--color-accent-rose)/10 border border-(--color-accent-rose)/20 text-sm text-(--color-accent-rose)">
          {{ error }}
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div v-if="mode === 'register'">
            <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Имя</label>
            <input v-model="name" type="text" required placeholder="Фамилия И.О." class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 focus:ring-1 focus:ring-(--color-accent-green)/20 transition-all" />
          </div>

          <div>
            <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Email</label>
            <input v-model="email" type="email" required placeholder="user@institute.ru" class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 focus:ring-1 focus:ring-(--color-accent-green)/20 transition-all" />
          </div>

          <div>
            <label class="block text-xs text-(--color-text-muted) mb-1.5 uppercase tracking-wider">Пароль</label>
            <input v-model="password" type="password" required placeholder="Введите пароль" class="w-full px-4 py-3 bg-(--color-bg-base) border border-(--color-border-default) rounded-lg text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-accent-green)/50 focus:ring-1 focus:ring-(--color-accent-green)/20 transition-all" />
          </div>

          <button type="submit" :disabled="loading" class="w-full py-3 mt-2 bg-gradient-to-r from-(--color-accent-green) to-(--color-accent-green-dim) text-(--color-text-inverse) rounded-lg text-sm font-semibold hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-wait">
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="opacity-75"/></svg>
              Загрузка...
            </span>
            <span v-else>{{ mode === 'login' ? 'Войти в систему' : 'Создать аккаунт' }}</span>
          </button>
        </form>
      </div>

      <p class="text-center text-[11px] text-(--color-text-muted) mt-6">BrAPI v2.1 &middot; CropOntology &middot; Kubernetes</p>
    </div>
  </div>
</template>
