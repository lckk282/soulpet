<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

const st = ref<any>(null)
const logs = ref<string[]>([])
const module = ref('backend')

const load = async () => {
  st.value = (await api.get('/status'))
  logs.value = (await api.get(`/status/logs?module=${module.value}&lines=80`)).lines || []
}
onMounted(load)

const toggle = async (name: string, enabled: boolean) => {
  await api.post(`/modules/${name}/toggle`, { enabled })
  await load()
}
const restart = async (name: string) => { await api.post(`/modules/${name}/restart`); await load() }

const STATE_LABEL: Record<string, string> = { ACTIVE: '活跃', IDLE: '待机', SAVING: '省钱待机' }
const MOD_LABEL: Record<string, string> = { qq: 'QQ 连接器', desktop_pet: '桌面桌宠', web_chat: '网页聊天' }
const STATUS_CLASS: Record<string, string> = { running: 'ok', starting: 'warn', waiting: 'warn', error: 'danger', stopped: 'gray', disabled: 'gray' }
</script>

<template>
  <div style="max-width:820px;margin:0 auto;padding:18px 16px" class="col">
    <div v-if="st" class="card">
      <div class="between">
        <h2>运行状态</h2>
        <div class="row">
          <span class="chip" :class="st.scheduler_running ? 'ok' : 'warn'">
            宠物状态：{{ STATE_LABEL[st.state] || st.state }}
          </span>
          <span class="chip gray">端口 {{ st.server_port }}</span>
          <span class="chip gray">密钥存放：{{ st.secret_backend === 'keyring' ? '系统钥匙串' : '加密文件' }}</span>
        </div>
      </div>

      <div class="row wrap" style="gap:10px;margin-top:12px">
        <div v-for="(m, name) in st.modules" :key="name" class="card grow" style="padding:12px">
          <div class="between">
            <strong>{{ MOD_LABEL[name] || name }}</strong>
            <span class="chip" :class="STATUS_CLASS[m.status]">{{ m.status }}</span>
          </div>
          <p class="small muted" style="margin:4px 0">{{ m.detail }}</p>
          <p v-if="m.last_error" class="small" style="color:var(--danger)">{{ m.last_error }}</p>
          <div class="row" style="margin-top:8px">
            <button class="small" @click="toggle(name, !m.enabled)">{{ m.enabled ? '关闭' : '开启' }}</button>
            <button class="small" @click="restart(name)">重启</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="between" style="margin-bottom:8px">
        <h2>日志</h2>
        <select v-model="module" style="max-width:160px" @change="load">
          <option value="backend">backend</option>
          <option value="qq-bridge">qq-bridge</option>
        </select>
      </div>
      <pre style="max-height:320px;overflow:auto;background:#fafaff;padding:10px;border-radius:10px;font-size:12px">{{ logs.join('\n') || '（暂无日志）' }}</pre>
    </div>
  </div>
</template>
