<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const initialized = computed(() => false)
const go = (p: string) => router.push(p)
</script>

<template>
  <div style="min-height:100%;display:flex;flex-direction:column">
    <header style="border-bottom:1px solid var(--line);background:#fff">
      <div class="between" style="max-width:1100px;margin:0 auto;padding:10px 16px">
        <div style="display:flex;align-items:center;gap:10px">
          <span style="font-size:20px">🐾</span>
          <strong>SoulPet</strong>
          <span class="chip gray">本地优先</span>
        </div>
        <nav style="display:flex;gap:6px">
          <button class="ghost" @click="go('/chat')">聊天</button>
          <button class="ghost" @click="go('/memory')">记忆</button>
          <button class="ghost" @click="go('/settings')">设置</button>
          <button class="ghost" @click="go('/status')">运行状态</button>
        </nav>
      </div>
    </header>
    <main style="flex:1"><router-view /></main>
    <footer class="small muted center" style="padding:14px">
      配置、记忆、密钥全部保存在本机 · SoulPet 不会把你的数据上传到任何第三方
    </footer>
  </div>
</template>
