<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import { api } from '../../api'
import AppIcon from '../../components/AppIcon.vue'

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
const ACTIONS = [
  { id: 'idle', label: '待机' }, { id: 'sway', label: '晃动' }, { id: 'wave', label: '挥手' },
  { id: 'tilt', label: '歪头' }, { id: 'blink', label: '眨眼' }, { id: 'jump', label: '蹦跳' },
]
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="cat" :size="19" /></span>
      <h2>桌宠形象</h2>
    </div>
    <p class="section-sub">校验素材包是否完整（九个槽位：六视角 + 三表情），缺的槽位会自动降级，不阻断流程。</p>

    <label class="field"><span>素材包</span>
      <select v-model="w.draft.pet.pack_id" @change="loadReport">
        <option v-for="p in packs" :key="p.id" :value="p.id">{{ p.id }}</option>
      </select>
    </label>

    <div v-if="report">
      <div class="row" style="gap:8px;margin-bottom:12px">
        <span class="chip" :class="report.complete ? 'ok' : 'warn'">
          <AppIcon :name="report.complete ? 'check' : 'alert'" :size="12" />
          完整性 {{ 9 - report.missing.length }}/9 {{ report.complete ? '齐全' : '· 缺 ' + report.missing_labels.join('、') }}
        </span>
        <span v-if="report.warnings.length" class="chip warn">{{ report.warnings.length }} 条提示</span>
      </div>

      <div class="slot-grid">
        <div v-for="(meta, slot) in report.slots" :key="slot" class="slot">
          <img :src="`/api/pet/packs/${w.draft.pet.pack_id}/file/${meta.file}`" width="72" height="72" alt="" />
          <div class="small">{{ LABEL[slot] || slot }}</div>
        </div>
        <div v-for="m in report.missing" :key="m" class="slot slot--missing">
          <div class="slot__q">?</div>
          <div class="small">缺 {{ LABEL[m] || m }}</div>
        </div>
      </div>

      <div v-if="report.warnings.length" class="banner warn" style="margin-top:12px">
        <div v-for="(x, i) in report.warnings" :key="i" class="small">· {{ x }}</div>
      </div>

      <div style="margin-top:16px">
        <span style="font-size:12.5px;color:var(--muted);font-weight:600">动作预览</span>
        <div class="row wrap" style="gap:6px;margin:8px 0 10px">
          <button v-for="a in ACTIONS" :key="a.id" class="small" :class="{ primary: preview === a.id }" @click="preview = a.id">{{ a.label }}</button>
        </div>
        <div class="preview-stage">
          <img
            :src="`/api/pet/packs/${w.draft.pet.pack_id}/file/${(report.slots[preview === 'jump' ? 'happy' : (preview === 'wave' || preview === 'tilt') ? 'front45' : 'front'] || report.slots.front).file}`"
            width="140" height="140"
            :class="preview === 'idle' ? 'spin' : ''"
            :style="preview === 'sway' ? 'animation: breathe 1.8s ease-in-out infinite' : ''"
            alt=""
          />
          <div class="small muted" style="margin-top:6px">当前动作：{{ ACTIONS.find((a) => a.id === preview)?.label }}</div>
        </div>
      </div>
    </div>

    <hr class="divider" />
    <div class="row">
      <label class="field grow"><span>缩放</span>
        <input v-model.number="w.draft.pet.scale" type="number" step="0.1" min="0.5" max="2" /></label>
      <label class="field grow"><span>不透明度（%）</span>
        <input v-model.number="w.draft.pet.opacity" type="number" min="30" max="100" /></label>
    </div>
    <label class="check-row" style="display:flex;align-items:center;gap:9px;padding:8px 10px;cursor:pointer"><input type="checkbox" v-model="w.draft.pet.always_on_top" /><span style="font-size:13.5px">窗口置顶</span></label>
    <label class="check-row" style="display:flex;align-items:center;gap:9px;padding:8px 10px;cursor:pointer"><input type="checkbox" v-model="w.draft.pet.click_through" /><span style="font-size:13.5px">鼠标穿透（点了不会挡住操作）</span></label>
  </div>
</template>

<style scoped>
.slot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.slot {
  border: 1px solid var(--line); border-radius: 12px; padding: 10px; text-align: center;
  background: var(--bg-2);
}
.slot--missing { opacity: 0.5; }
.slot__q { height: 72px; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 800; color: var(--muted); }
.preview-stage { text-align: center; padding: 18px; background: var(--bg-2); border-radius: 14px; border: 1px solid var(--line-2); }
@media (max-width: 480px) { .slot-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
