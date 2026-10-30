<script setup lang="ts">
import { onMounted, ref, nextTick } from 'vue'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'
import guideAvatar from '../assets/guide/idle.webp'

type Msg = { role: string; content: string; emotion?: string }

const msgs = ref<Msg[]>([])
const input = ref('')
const convId = ref<number | null>(null)
const busy = ref(false)
const petName = ref('宠物')
const box = ref<HTMLElement | null>(null)
// 还没捏宠物：后端会返回 409，此时不该给一个能打字却发不出去的输入框
const needPet = ref(false)

const scroll = async () => { await nextTick(); if (box.value) box.value.scrollTop = box.value.scrollHeight }

const goWizard = () => { window.location.href = '/?edit=1' }

onMounted(async () => {
  try {
    const p = await api.get('/pet')
    petName.value = p.profile?.pet?.name || '宠物'
    if (!p.profile?.pet?.id) { needPet.value = true; return }
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
  <div class="chat-wrap">
    <div class="page-head">
      <span class="page-head__eyebrow">你的私人伙伴</span>
      <h1>{{ needPet ? '还没有宠物' : '和 ' + petName + ' 聊聊天' }}</h1>
      <p>{{ needPet ? '先去创造向导捏一只，两分钟就好，不填 API Key 也能用。' : '说的话会按你设定的性格回应，重要的事会慢慢记进它的小本本。' }}</p>
    </div>

    <div class="card chat-card" :class="{ 'chat-card--empty': needPet }">
      <div v-if="needPet" class="chat-empty" style="padding:34px 20px">
        <img :src="guideAvatar" alt="" class="chat-empty__pet" />
        <p class="muted" style="margin:10px 0 16px">先捏一只属于你的宠物，再来聊天吧~</p>
        <button class="primary" @click="goWizard">去创造向导</button>
      </div>

      <template v-else>
      <div class="chat-head">
        <div class="chat-head__who">
          <span class="avatar"><img :src="guideAvatar" alt="" /></span>
          <div>
            <strong>{{ petName }}</strong>
            <div class="small muted" style="line-height:1.2">陪你聊天中</div>
          </div>
          <span class="chip ok"><span class="dot" /> 在线</span>
        </div>
        <div class="row" style="gap:6px">
          <button class="ghost small" @click="$router.push('/memory')"><AppIcon name="memory" :size="14" style="vertical-align:-2px" /> 记忆</button>
          <button class="ghost small" @click="$router.push('/settings')"><AppIcon name="settings" :size="14" style="vertical-align:-2px" /> 设置</button>
        </div>
      </div>

      <div ref="box" class="chat-body">
        <div v-for="(m, i) in msgs" :key="i" class="msg" :class="m.role === 'user' ? 'msg--user' : 'msg--assistant'">
          <span v-if="m.role === 'assistant'" class="avatar avatar--sm"><img :src="guideAvatar" alt="" /></span>
          <div class="bubble">
            {{ m.content }}<span v-if="busy && i === msgs.length - 1 && m.role === 'assistant'" class="typing-caret">▌</span>
          </div>
        </div>
        <div v-if="!msgs.length" class="chat-empty">
          <img :src="guideAvatar" alt="" class="chat-empty__pet" />
          <p class="small muted">打声招呼吧，我在听~</p>
        </div>
      </div>

      <div class="chat-send">
        <textarea
          v-model="input" rows="2" placeholder="说点什么…（Enter 发送）"
          @keydown.enter.exact.prevent="send"
        />
        <button class="primary send-btn" :disabled="busy || !input.trim()" @click="send">
          <AppIcon v-if="!busy" name="send" :size="17" /> <span v-if="!busy">发送</span><span v-else>…</span>
        </button>
      </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.avatar--sm { width: 30px; height: 30px; border-radius: 10px; flex-shrink: 0; }
.chat-empty {
  margin: auto;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  animation: empty-in 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.chat-empty__pet { width: 140px; opacity: 0.95; animation: pet-float 4.4s ease-in-out infinite; }
@keyframes empty-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes pet-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
.send-btn {
  height: 46px; min-width: 92px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  white-space: nowrap;
}
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--ok); margin-right: 3px; }
.typing-caret { color: var(--brand); animation: caret 0.7s steps(1) infinite; }
@keyframes caret { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .typing-caret { animation: none; } .chat-empty__pet { animation: none; } }
</style>
