<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
</script>

<template>
  <div class="min-h-screen bg-(--color-bg-root) grain-overlay">
    <AppSidebar />
    <div class="ml-64">
      <AppHeader />
      <main class="p-6">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.page-enter-active {
  transition: all 0.3s ease-out;
}
.page-leave-active {
  transition: all 0.15s ease-in;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
