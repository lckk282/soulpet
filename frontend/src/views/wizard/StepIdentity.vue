<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import { api } from '../../api'

const w = useWizard()
const roles = ref<{ id: string; label: string }[]>([])
const tags = ref<string[]>([])
const packs = ref<any[]>([])

onMounted(async () => {
  try {
    const r = await api.get('/pet')
    roles.value = r.roles
    tags.value = r.tags
  } catch (_) { /* 后端未就绪时用内置兜底 */ roles.value = [
    { id: 'maid', label: '女仆' }, { id: 'silent_npc', label: '沉默NPC' },
    { id: 'buddy', label: '活泼搭子' }, { id: 'cold_assistant', label: '清冷助手' },
    { id: 'tsundere_cat', label: '毒舌猫系' }, { id: 'senior', label: '温柔学长学姐' },
  ] }
  try {
    packs.value = (await api.get('/pet/packs')).items
    if (!w.draft.identity.asset_pack_id && packs.value.length) {
      w.draft.identity.asset_pack_id = packs.value[0].id
    }
  } catch (_) { /* 忽略 */ }
})

const toggleRole = (id: string) => {
  const list = w.draft.identity.role_presets
  const i = list.indexOf(id)
  if (i >= 0) list.splice(i, 1); else list.push(id)
}
const NAMES = ['小绫', '阿茶', '团子', '木木', '柚柚', '十七', '奶油', '咕咕']
const randomName = () => { w.draft.identity.name = NAMES[Math.floor(Math.random() * NAMES.length)] }
</script>

<template>
  <div class="card">
    <h2>第一步 · 基础形象设定</h2>
    <p class="small muted">先给它一个名字和身份，形象素材可以之后随时换。</p>

    <label class="field">
      <span>宠物名字</span>
      <div class="row">
        <input v-model="w.draft.identity.name" type="text" placeholder="例如：小绫" maxlength="16" />
        <button @click="randomName">随机</button>
      </div>
    </label>

    <div class="field">
      <span style="display:block;font-size:12px;color:var(--muted);margin-bottom:6px">身份定位（可多选）</span>
      <div class="row wrap" style="gap:8px">
        <div
          v-for="r in roles" :key="r.id"
          class="radio-card"
          :class="{ active: w.draft.identity.role_presets.includes(r.id) }"
          style="padding:8px 12px"
          @click="toggleRole(r.id)"
        >{{ r.label }}</div>
      </div>
    </div>

    <label class="field">
      <span>补充说明（可选，会写进人设）</span>
      <textarea v-model="w.draft.identity.role_custom" placeholder="例如：说话带点口癖「主人~」" />
    </label>

    <label class="field">
      <span>一句话简介（可选）</span>
      <input v-model="w.draft.identity.bio" type="text" placeholder="例如：有点笨手笨脚但很努力" />
    </label>

    <div class="field">
      <span style="display:block;font-size:12px;color:var(--muted);margin-bottom:6px">形象素材</span>
      <div class="row wrap" style="gap:8px">
        <div class="radio-card" :class="{ active: w.draft.identity.asset_source === 'builtin' }"
             @click="w.draft.identity.asset_source = 'builtin'">🎲 用内置默认形象</div>
        <div class="radio-card" :class="{ active: w.draft.identity.asset_source === 'upload' }"
             @click="w.draft.identity.asset_source = 'upload'">📁 上传素材包（zip）</div>
        <div class="radio-card disabled" style="cursor:not-allowed">🎨 图集生成器（规划中）</div>
      </div>
      <div v-if="w.draft.identity.asset_source === 'upload'" style="margin-top:8px">
        <select v-model="w.draft.identity.asset_pack_id">
          <option v-for="p in packs" :key="p.id" :value="p.id">{{ p.id }} · {{ p.complete ? '完整' : '缺 ' + p.missing.join('/') }}</option>
        </select>
        <p class="small muted" style="margin-top:6px">上传入口在「设置 → 形象素材」，也可用内置包先跑通。</p>
      </div>
    </div>
  </div>
</template>
