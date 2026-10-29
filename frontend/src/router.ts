import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'wizard', component: () => import('./views/Wizard.vue') },
  { path: '/wizard/:step', name: 'wizard-step', component: () => import('./views/Wizard.vue') },
  { path: '/chat', name: 'chat', component: () => import('./views/Chat.vue') },
  { path: '/memory', name: 'memory', component: () => import('./views/Memory.vue') },
  { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
  { path: '/status', name: 'status', component: () => import('./views/Status.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({ history: createWebHistory(), routes })
