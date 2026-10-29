<script setup lang="ts">
import { onMounted, ref, nextTick } from 'vue'
import { api } from '../api'

type Msg = { role: string; content: string; emotion?: string }

const msgs = ref<Msg[]>([])
const input = ref('')
const convId = ref<number | null>(null)
const busy = ref(false)
const petName = ref('宠物')
const box = ref<HTMLElement | null>(null)

const scroll = async () => { await nextTick(); if (box.value) box.value.scrollTop = box.value.scrollHeight }

onMounted(async () => {
  try {
    const p = await api.get('/pet')
    petName.value = p.profile?.pet?.name || '宠物'
    const h = await api.get('/chat/history')
    convId.value = h.conv_id
    msgs.value = h.messages || []
    if (!msgs.value.length) {
      const g = await api.get('/chat/greeting')
      msgs.value.push({ role: 'assistant', content: g.text?.replace(/^\[(happy|shy|sad|neutral)\]\s*/, '') || '你好呀~' })
    }
  } catch (_) { /* 未初始化时提示 */ }
  scroll()
})

const send = async () => {
  const text = input.value.trim()
  if (!text || busy.value) return
  input.value = ''
  msgs.value.push({ role: 'user', content: text })
  await scroll()

  busy.value = true
  const idx = msgs.value.push({ role: 'assistant', content: '' }) - 1
  try {
    convId.value = await api.chatStream(text, convId.value, (delta) => {
      msgs.value[idx].content += delta
      scroll()
    })
    const m = msgs.value[idx].content.match(/^\[(happy|shy|sad|neutral)\]\s*/)
    if (m) { msgs.value[idx].emotion = m[1]; msgs.value[idx].content = msgs.value[idx].content.slice(m[0].length) }
  } catch (e: any) {
    msgs.value[idx].content = '（' + (e.message || '出错了') + '）'
  } finally {
    busy.value = false
    scroll()
  }
}
</script>

<template>
  <div style="max-width:820px;margin:0 auto;padding:18px 16px">
    <div class="card" style="padding:0;display:flex;flex-direction:column;height:calc(100vh - 150px)">
      <div class="between" style="padding:10px 16px;border-bottom:1px solid var(--line)">
        <div><strong>{{ petName }}</strong> <span class="chip ok">在线</span></div>
        <div class="row">
          <button class="ghost" @click="$router.push('/memory')">记忆时间线</button>
          <button class="ghost" @click="$router.push('/settings')">设置</button>
        </div>
      </div>

      <div ref="box" style="flex:1;overflow:auto;padding:16px">
        <div v-for="(m, i) in msgs" :key="i" style="margin-bottom:12px">
          <div v-if="m.role === 'user'" style="text-align:right">
            <span style="display:inline-block;background:var(--brand);color:#fff;padding:8px 12px;border-radius:12px;max-width:76%;white-space:pre-wrap">{{ m.content }}</span>
          </div>
          <div v-else class="row" style="align-items:flex-start">
            <div style="font-size:22px">🐾</div>
            <div style="background:#fff;border:1px solid var(--line);padding:8px 12px;border-radius:12px;max-width:76%;white-space:pre-wrap">
              {{ m.content }}<span v-if="busy && i === msgs.length - 1" class="muted">▌</span>
            </div>
          </div>
        </div>
      </div>

      <div class="row" style="padding:12px;border-top:1px solid var(--line)">
        <textarea
          v-model="input" rows="2" placeholder="说点什么…（Enter 发送，Shift+Enter 换行）"
          @keydown.enter.exact.prevent="send"
        />
        <button class="primary" :disabled="busy || !input.trim()" @click="send">{{ busy ? '…' : '发送' }}</button>
      </div>
    </div>
  </div>
</template>
