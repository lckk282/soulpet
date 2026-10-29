<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import AppIcon from './components/AppIcon.vue'
import guideAvatar from './assets/guide/idle.webp'

const router = useRouter()
const route = useRoute()
const go = (p: string) => router.push(p)

const navs = [
  { path: '/chat', label: '聊天', icon: 'chat' },
  { path: '/memory', label: '记忆', icon: 'memory' },
  { path: '/settings', label: '设置', icon: 'settings' },
  { path: '/status', label: '运行状态', icon: 'status' },
]
const isActive = (p: string) => computed(() => route.path === p)
const activeChat = isActive('/chat')
const activeMemory = isActive('/memory')
const activeSettings = isActive('/settings')
const activeStatus = isActive('/status')
const activeMap: Record<string, any> = {
  '/chat': activeChat, '/memory': activeMemory, '/settings': activeSettings, '/status': activeStatus,
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar__inner">
        <button class="brand" @click="go('/')">
          <span class="brand__mark"><img :src="guideAvatar" alt="" /></span>
          <span>SoulPet</span>
          <span class="chip gray" style="font-weight:600">本地优先</span>
        </button>
        <nav class="nav">
          <button
            v-for="n in navs" :key="n.path"
            class="nav__item"
            :class="{ active: activeMap[n.path].value }"
            :title="n.label"
            @click="go(n.path)"
          >
            <AppIcon :name="n.icon" :size="17" /><span>{{ n.label }}</span>
          </button>
        </nav>
      </div>
    </header>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer class="app-footer">
      <AppIcon name="lock" :size="12" /> 配置、记忆、密钥全部保存在本机<span class="fdot">·</span>SoulPet 不会把你的数据上传到任何第三方
    </footer>
  </div>
</template>
