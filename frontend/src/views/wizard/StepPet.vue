<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import { api } from '../../api'

const w = useWizard()
const packs = ref<any[]>([])
const report = ref<any>(null)
const preview = ref('idle')

onMounted(async () => {
  try {
    packs.value = (await api.get('/pet/packs')).items
    if (!w.draft.pet.pack_id && packs.value.length) w.draft.pet.pack_id = packs.value[0].id
    loadReport()
  } catch (_) { /* 忽略 */ }
})

const loadReport = async () => {
  if (!w.draft.pet.pack_id) return
  try { report.value = (await api.get(`/pet/packs/${w.draft.pet.pack_id}`)).report } catch (_) { report.value = null }
}
const LABEL: Record<string, string> = {
  front: '正面', front45: '45°侧前', side: '侧面', back45: '背侧', back: '背面',
  side_down: '低头侧脸', happy: '开心', shy: '害羞', sad: '委屈',
}
const ACTIONS = ['idle', 'sway', 'wave', 'tilt', 'blink', 'jump']
</script>

<template>
  <div class="card">
    <h2>桌宠形象</h2>
    <p class="small muted">校验素材包是否完整（九个槽位：六视角 + 三表情），缺的槽位会自动降级，不阻断流程。</p>

    <label class="field"><span>素材包</span>
      <select v-model="w.draft.pet.pack_id" @change="loadReport">
        <option v-for="p in packs" :key="p.id" :value="p.id">{{ p.id }}</option>
      </select>
    </label>

    <div v-if="report" style="margin-top:8px">
      <div class="row" style="gap:8px;margin-bottom:8px">
        <span class="chip" :class="report.complete ? 'ok' : 'warn'">
          完整性 {{ 9 - report.missing.length }}/9 {{ report.complete ? '✔' : '· 缺 ' + report.missing_labels.join('、') }}
        </span>
        <span v-if="report.warnings.length" class="chip warn">{{ report.warnings.length }} 条提示</span>
      </div>

      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        <div v-for="(meta, slot) in report.slots" :key="slot" class="card center" style="padding:10px">
          <img :src="`/api/pet/packs/${w.draft.pet.pack_id}/file/${meta.file}`" width="72" height="72" alt="" />
          <div class="small">{{ LABEL[slot] || slot }}</div>
        </div>
        <div v-for="m in report.missing" :key="m" class="card center" style="padding:10px;opacity:.45">
          <div style="height:72px;display:flex;align-items:center;justify-content:center;font-size:24px">？</div>
          <div class="small">缺 {{ LABEL[m] || m }}</div>
        </div>
      </div>

      <div v-if="report.warnings.length" class="banner warn" style="margin-top:10px">
        <div v-for="(x, i) in report.warnings" :key="i" class="small">· {{ x }}</div>
      </div>

      <div style="margin-top:12px">
        <span style="font-size:12px;color:var(--muted)">动作预览</span>
        <div class="row wrap" style="gap:6px;margin:6px 0 10px">
          <button v-for="a in ACTIONS" :key="a" :class="{ primary: preview === a }" @click="preview = a">{{ a }}</button>
        </div>
        <div class="center" style="padding:18px;background:#fafaff;border-radius:12px">
          <img
            :src="`/api/pet/packs/${w.draft.pet.pack_id}/file/${(report.slots[preview === 'jump' ? 'happy' : (preview === 'wave' || preview === 'tilt') ? 'front45' : 'front'] || report.slots.front).file}`"
            width="140" height="140"
            :class="preview === 'idle' ? 'spin' : ''"
            :style="preview === 'sway' ? 'animation: breathe 1.8s ease-in-out infinite' : ''"
            alt=""
          />
          <div class="small muted" style="margin-top:6px">当前动作：{{ preview }}</div>
        </div>
      </div>
    </div>

    <div class="row" style="margin-top:12px">
      <label class="field grow"><span>缩放</span>
        <input v-model.number="w.draft.pet.scale" type="number" step="0.1" min="0.5" max="2" /></label>
      <label class="field grow"><span>不透明度（%）</span>
        <input v-model.number="w.draft.pet.opacity" type="number" min="30" max="100" /></label>
    </div>
    <label style="display:flex;gap:8px"><input type="checkbox" v-model="w.draft.pet.always_on_top" /><span>窗口置顶</span></label>
    <label style="display:flex;gap:8px"><input type="checkbox" v-model="w.draft.pet.click_through" /><span>鼠标穿透（点了不会挡住操作）</span></label>
  </div>
</template>
