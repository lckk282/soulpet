<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import { api } from '../../api'
import AppIcon from '../../components/AppIcon.vue'

const w = useWizard()
const roles = ref<{ id: string; label: string }[]>([])
const packs = ref<any[]>([])

onMounted(async () => {
  try {
    const r = await api.get('/pet')
    roles.value = r.roles
  } catch (_) {
    roles.value = [
      { id: 'maid', label: '女仆' }, { id: 'silent_npc', label: '沉默NPC' },
      { id: 'buddy', label: '活泼搭子' }, { id: 'cold_assistant', label: '清冷助手' },
      { id: 'tsundere_cat', label: '毒舌猫系' }, { id: 'senior', label: '温柔学长学姐' },
    ]
  }
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

const sources = [
  { id: 'builtin', icon: 'sparkle', title: '内置默认形象', desc: '先跑通流程' },
  { id: 'upload', icon: 'image', title: '上传素材包', desc: 'zip 格式' },
] as const
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="cat" :size="19" /></span>
      <h2>基础形象设定</h2>
    </div>
    <p class="section-sub">先给它一个名字和身份，形象素材之后随时都能换。</p>

    <label class="field">
      <span>宠物名字 <span style="color:var(--brand)">*</span></span>
      <div class="row">
        <input v-model="w.draft.identity.name" type="text" placeholder="例如：小绫" maxlength="16" />
        <button @click="randomName" title="随机一个名字"><AppIcon name="refresh" :size="15" /> 随机</button>
      </div>
    </label>

    <div class="field">
      <span style="display:block;font-size:12.5px;color:var(--muted);margin-bottom:8px;font-weight:600">身份定位（可多选）</span>
      <div class="row wrap" style="gap:8px">
        <div
          v-for="r in roles" :key="r.id"
          class="radio-card"
          :class="{ active: w.draft.identity.role_presets.includes(r.id) }"
          style="padding:9px 14px;font-size:13px;font-weight:600"
          @click="toggleRole(r.id)"
        >
          <AppIcon
            v-if="w.draft.identity.role_presets.includes(r.id)" name="check" :size="14" :stroke="3"
            style="vertical-align:-2px;margin-right:5px;color:var(--brand)"
          />{{ r.label }}
        </div>
      </div>
    </div>

    <div class="row">
      <label class="field grow"><span>补充说明（可选，会写进人设）</span>
        <textarea v-model="w.draft.identity.role_custom" placeholder="例如：说话带点口癖「主人~」" /></label>
    </div>
    <div class="row">
      <label class="field grow"><span>一句话简介（可选）</span>
        <input v-model="w.draft.identity.bio" type="text" placeholder="例如：有点笨手笨脚但很努力" /></label>
    </div>

    <hr class="divider" />
    <div class="field" style="margin-bottom:0">
      <span style="display:block;font-size:12.5px;color:var(--muted);margin-bottom:8px;font-weight:600">形象素材</span>
      <div class="row wrap" style="gap:10px">
        <div
          v-for="s in sources" :key="s.id"
          class="radio-card grow"
          :class="{ active: w.draft.identity.asset_source === s.id }"
          style="display:flex;align-items:center;gap:10px;min-width:180px"
          @click="w.draft.identity.asset_source = s.id"
        >
          <AppIcon :name="s.icon" :size="20" style="color:var(--brand)" />
          <div><div style="font-size:13px;font-weight:700">{{ s.title }}</div><div class="small muted">{{ s.desc }}</div></div>
        </div>
        <div class="radio-card disabled" style="display:flex;align-items:center;gap:10px;min-width:180px">
          <AppIcon name="image" :size="20" />
          <div><div style="font-size:13px;font-weight:700">图集生成器</div><div class="small muted">规划中</div></div>
        </div>
      </div>
      <div v-if="w.draft.identity.asset_source === 'upload'" style="margin-top:10px">
        <select v-model="w.draft.identity.asset_pack_id">
          <option v-for="p in packs" :key="p.id" :value="p.id">{{ p.id }} · {{ p.complete ? '完整' : '缺 ' + p.missing.join('/') }}</option>
        </select>
        <p class="small muted" style="margin-top:6px">上传入口在「设置 → 形象素材」，也可用内置包先跑通。</p>
      </div>
    </div>
  </div>
</template>
