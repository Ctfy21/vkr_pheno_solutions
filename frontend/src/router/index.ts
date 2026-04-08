import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/auth',
      name: 'auth',
      component: () => import('@/views/AuthView.vue'),
      
    },
    {
      path: '/programs/select',
      name: 'program-select',
      component: () => import('@/views/ProgramSelectView.vue'),
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'programs',
          name: 'programs',
          component: () => import('@/views/ProgramsView.vue'),
        },
        {
          path: 'programs/:programId/trials/:trialId',
          name: 'trial',
          component: () => import('@/views/TrialView.vue'),
        },
        {
          path: 'experiments',
          name: 'experiments',
          component: () => import('@/views/ExperimentsListView.vue'),
        },
        {
          path: 'experiments/create',
          name: 'experiment-create',
          component: () => import('@/views/ExperimentCreateView.vue'),
        },
        {
          path: 'experiments/:studyId',
          name: 'experiment',
          component: () => import('@/views/ExperimentView.vue'),
        },
        {
          path: 'experiments/:studyId/plants',
          name: 'plants',
          component: () => import('@/views/PlantsView.vue'),
        },
        {
          path: 'experiments/:studyId/collect',
          name: 'data-collection',
          component: () => import('@/views/DataCollectionView.vue'),
        },
        {
          path: 'experiments/:studyId/results',
          name: 'results',
          component: () => import('@/views/ResultsView.vue'),
        },
        {
          path: 'variables',
          name: 'variables',
          component: () => import('@/views/VariablesView.vue'),
        },
        {
          path: 'containers',
          name: 'containers',
          component: () => import('@/views/ContainersView.vue'),
        },
        {
          path: 'experiments/:studyId/export',
          name: 'export',
          component: () => import('@/views/ExportView.vue'),
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('@/views/AdminView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const publicPages = ['/auth']
  const authRequired = !publicPages.includes(to.path)

  if (authRequired && !token) {
    return '/auth'
  }
  // If logged in and going to auth, redirect to dashboard
  if (to.path === '/auth' && token) {
    return '/dashboard'
  }
})

export default router
