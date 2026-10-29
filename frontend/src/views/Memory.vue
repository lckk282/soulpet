<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

const items = ref<any[]>([])
const stats = ref<any>(null)
const q = ref('')
const type = ref('')
const total = ref(0)
const limit = 50

const TYPE_LABEL: Record<string, string> = { fact: '事实', emotion: '情感', preference: '偏好', event: '事件' }
const TYPE_CLASS: Record<string, string> = { fact: '', emotion: 'danger', preference: 'ok', event: 'warn' }
const SOURCE_LABEL: Record<string, string> = { user_stated: '你亲口说的', inferred: '它推断的', manual: '你手动加的' }

const load = async () => {
  const r = await api.get(`/memory/timeline?q=${encodeURIComponent(q.value)}&type=${type.value}&limit=${limit}`)
  items.value = r.items
  total.value = r.total
  stats.value = (await api.get('/memory/stats')).data
}
onMounted(load)

const editing = ref<any>(null)
const save = async () => {
  if (!editing.value) return
  await api.put(`/memory/${editing.value.id}`, {
    content: editing.value.content, type: editing.value.type,
    importance: editing.value.importance, pinned: editing.value.pinned,
  })
  editing.value = null
  load()
}
const del = async (id: number) => { await api.del(`/memory/${id}`); load() }
const pin = async (m: any) => { await api.put(`/memory/${m.id}`, { pinned: !m.pinned }); load() }
const add = async () => {
  const c = prompt('写一条你想让它记住的事')
  if (!c) return
  await api.post('/memory', { content: c, type: 'manual' as any, importance: 0.8 })
  load()
}
const forgetAll = async () => {
  if (!confirm('确定清空全部记忆？这会删除它记住的所有事（不可恢复）。')) return
  await api.del('/memory'); load()
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <span class="page-head__eyebrow">记忆时间线</span>
      <h1>它记住的事</h1>
      <p>每一条记忆你都能查看、编辑、置顶或让它遗忘，主动权始终在你手里。</p>
    </div>

    <div class="between" style="margin-bottom:14px;flex-wrap:wrap;gap:10px">
      <div v-if="stats" class="row wrap" style="gap:7px">
        <span class="chip">共 {{ stats.total }} 条</span>
        <span v-for="(n, t) in stats.by_type" :key="t" class="chip" :class="TYPE_CLASS[t]">{{ TYPE_LABEL[t] || t }} {{ n }}</span>
        <span v-if="stats.first_at" class="chip gray">始于 {{ String(stats.first_at).slice(0, 10) }}</span>
      </div>
      <div class="row" style="gap:8px">
        <button @click="add"><AppIcon name="plus" :size="15" style="vertical-align:-3px" /> 手动添加</button>
        <button class="danger" @click="forgetAll"><AppIcon name="trash" :size="14" style="vertical-align:-2px" /> 清空</button>
      </div>
    </div>

    <div class="row" style="margin-bottom:14px">
      <input v-model="q" type="text" placeholder="搜索记忆…" @keyup.enter="load" />
      <select v-model="type" style="max-width:130px" @change="load">
        <option value="">全部类型</option>
        <option value="fact">事实</option>
        <option value="emotion">情感</option>
        <option value="preference">偏好</option>
        <option value="event">事件</option>
      </select>
      <button @click="load"><AppIcon name="search" :size="16" style="vertical-align:-3px" /> 搜索</button>
    </div>

    <div v-for="m in items" :key="m.id" class="mem-item">
      <div class="between" style="align-items:flex-start;gap:10px">
        <div class="row wrap" style="gap:6px;align-items:center">
          <span class="chip" :class="TYPE_CLASS[m.type]">{{ TYPE_LABEL[m.type] || m.type }}</span>
          <span class="small muted">{{ m.created_at.slice(0, 16).replace('T', ' ') }}</span>
          <span class="small muted">· {{ SOURCE_LABEL[m.source] || m.source }}</span>
          <span v-if="m.pinned" class="chip warn"><AppIcon name="pin" :size="11" /> 置顶</span>
        </div>
        <div class="row" style="gap:4px;flex-shrink:0">
          <button class="ghost small" @click="pin(m)">{{ m.pinned ? '取消置顶' : '置顶' }}</button>
          <button class="ghost small" @click="editing = { ...m }"><AppIcon name="edit" :size="13" style="vertical-align:-2px" /> 编辑</button>
          <button class="danger small" @click="del(m.id)">遗忘</button>
        </div>
      </div>
      <div v-if="editing && editing.id === m.id" class="col" style="margin-top:10px">
        <input v-model="editing.content" type="text" />
        <div class="row">
          <label class="field grow"><span>重要度</span>
            <input v-model.number="editing.importance" type="number" step="0.1" min="0" max="1" /></label>
          <label class="field grow"><span>类型</span>
            <select v-model="editing.type">
              <option value="fact">事实</option><option value="emotion">情感</option>
              <option value="preference">偏好</option><option value="event">事件</option>
            </select></label>
        </div>
        <div class="row"><button class="primary" @click="save">保存</button><button @click="editing = null">取消</button></div>
      </div>
      <div v-else style="margin-top:8px;font-size:14px">{{ m.content }}</div>
      <div class="small muted" style="margin-top:6px">重要度 {{ Number(m.importance).toFixed(2) }} · 被想起 {{ m.reinforce_count }} 次</div>
    </div>

    <div v-if="!items.length" class="center muted" style="padding:40px 0">
      <AppIcon name="memory" :size="42" style="opacity:0.3" />
      <p class="small">还没有记忆。去和它聊几句吧，重要的事会被记住。</p>
    </div>
  </div>
</template>
