import { createRouter, createWebHistory } from 'vue-router'
import { api } from './api'
import { getCachedHasPet, setCachedHasPet } from './petCache'

const routes = [
  { path: '/', name: 'wizard', component: () => import('./views/Wizard.vue') },
  { path: '/wizard/:step', name: 'wizard-step', component: () => import('./views/Wizard.vue') },
  { path: '/chat', name: 'chat', component: () => import('./views/Chat.vue') },
  { path: '/memory', name: 'memory', component: () => import('./views/Memory.vue') },
  { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
  { path: '/status', name: 'status', component: () => import('./views/Status.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

// 已经捏好宠物就直接去聊天页，别把人丢回一个空白向导、让人以为配置丢了。
// 必须在「路由守卫」里做：放在 Wizard 组件的 onMounted 里再 router.replace()，
// 客户端跳转会出现 URL 与页面不同步（页面已是聊天页，地址栏还停在设置页）。
router.beforeEach(async (to) => {
  if (to.name !== 'wizard') return true
  // 主动来重捏的（设置页入口）放行
  if (to.query.edit === '1') return true
  // 有未完成的草稿就让他接着填
  if (localStorage.getItem('soulpet.wizard.draft')) return true

  let has = getCachedHasPet()
  if (has === null) {
    try {
      const p = await api.get('/pet')
      has = !!p?.profile?.pet?.id
    } catch {
      has = false // 后端没起来就老老实实待在向导
    }
    setCachedHasPet(has)
  }
  return has ? '/chat' : true
})

export default router
