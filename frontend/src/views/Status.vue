<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

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
const STATE_CLASS: Record<string, string> = { ACTIVE: 'ok', IDLE: 'gray', SAVING: 'warn' }
const MOD_LABEL: Record<string, string> = { qq: 'QQ 连接器', desktop_pet: '桌面桌宠', web_chat: '网页聊天' }
const MOD_ICON: Record<string, string> = { qq: 'robot', desktop_pet: 'cat', web_chat: 'chat' }
const STATUS_CLASS: Record<string, string> = { running: 'ok', starting: 'warn', waiting: 'warn', error: 'danger', stopped: 'gray', disabled: 'gray' }
const STATUS_LABEL: Record<string, string> = {
  running: '运行中', starting: '启动中', waiting: '等待中', error: '出错', stopped: '已停止', disabled: '未启用',
}
</script>

<template>
  <div class="page col">
    <div class="page-head" style="margin-bottom:4px">
      <span class="page-head__eyebrow">系统状态</span>
      <h1>运行状态</h1>
      <p>查看宠物的作息状态、各模块运行情况与实时日志。</p>
    </div>

    <div v-if="st" class="card">
      <div class="between" style="flex-wrap:wrap;gap:10px;margin-bottom:14px">
        <h2 style="margin:0">概览</h2>
        <div class="row wrap" style="gap:7px">
          <span class="chip" :class="STATE_CLASS[st.state] || 'gray'"><span class="dot" /> 宠物：{{ STATE_LABEL[st.state] || st.state }}</span>
          <span class="chip" :class="st.scheduler_running ? 'ok' : 'warn'">调度器 {{ st.scheduler_running ? '运行中' : '未运行' }}</span>
          <span class="chip gray">端口 {{ st.server_port }}</span>
          <span class="chip" :class="st.secret_plaintext ? 'warn' : 'gray'">
            <AppIcon name="lock" :size="11" />
            {{ st.secret_backend === 'keyring' ? '系统钥匙串' : (st.secret_plaintext ? '明文文件（建议设主密码）' : '加密文件') }}
          </span>
        </div>
      </div>

      <div class="stat-tiles" style="margin-bottom:0">
        <div v-for="(m, name) in st.modules" :key="name" class="tile">
          <div class="between" style="margin-bottom:8px">
            <span class="tile__label" style="display:inline-flex;align-items:center;gap:6px">
              <AppIcon :name="MOD_ICON[name] || 'plug'" :size="15" style="color:var(--brand)" /> {{ MOD_LABEL[name] || name }}
            </span>
            <span class="chip" :class="STATUS_CLASS[m.status]">{{ STATUS_LABEL[m.status] || m.status }}</span>
          </div>
          <p class="small muted" style="margin:2px 0 8px;min-height:32px">{{ m.detail }}</p>
          <p v-if="m.last_error" class="small" style="color:var(--danger);margin:0 0 8px">{{ m.last_error }}</p>
          <div class="row" style="gap:6px">
            <button class="small" @click="toggle(name, !m.enabled)">{{ m.enabled ? '关闭' : '开启' }}</button>
            <button class="small" @click="restart(name)"><AppIcon name="refresh" :size="13" style="vertical-align:-2px" /> 重启</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="between" style="margin-bottom:10px;flex-wrap:wrap;gap:10px">
        <h2 style="margin:0;display:flex;align-items:center;gap:8px"><AppIcon name="memory" :size="17" style="color:var(--brand)" /> 日志</h2>
        <select v-model="module" style="max-width:170px" @change="load">
          <option value="backend">backend</option>
          <option value="qq-bridge">qq-bridge</option>
        </select>
      </div>
      <pre class="log">{{ logs.join('\n') || '（暂无日志）' }}</pre>
    </div>
  </div>
</template>

<style scoped>
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: currentColor; margin-right: 3px; }
</style>
