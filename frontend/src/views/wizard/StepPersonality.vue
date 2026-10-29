<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
import AppIcon from '../../components/AppIcon.vue'
const w = useWizard()

const META: Record<string, { label: string; low: string; high: string; icon: string }> = {
  clinginess: { label: '粘人程度', low: '高冷疏离', high: '寸步不离', icon: 'heart' },
  verbosity: { label: '说话风格', low: '惜字如金', high: '话痨小作文', icon: 'chat' },
  snark: { label: '吐槽频率', low: '温柔体贴', high: '句句带刺', icon: 'bolt' },
  valence: { label: '情绪倾向', low: '阴郁低沉', high: '元气满满', icon: 'sparkle' },
  retention: { label: '记忆偏好', low: '金鱼记忆', high: '过目不忘', icon: 'brain' },
}
const TAGS = ['傲娇', '天然呆', '姐系', '弟系', '中二', '毒舌', '温柔', '好奇宝宝', '社恐', '话痨']
const toggleTag = (t: string) => {
  const l = w.draft.personality.tags
  const i = l.indexOf(t)
  if (i >= 0) l.splice(i, 1); else l.push(t)
}
const addRule = () => w.draft.personality.hard_rules.push('')
const removeRule = (i: number) => w.draft.personality.hard_rules.splice(i, 1)
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="sparkle" :size="19" /></span>
      <h2>性格与行为规则</h2>
    </div>
    <p class="section-sub">拖动滑块，塑造它的说话方式与脾气。</p>

    <div v-for="(m, key) in META" :key="key" class="slider-row">
      <div class="slider-row__head">
        <span class="slider-row__label"><AppIcon :name="m.icon" :size="15" /> {{ m.label }}</span>
        <span class="slider-row__val">{{ w.draft.personality.sliders[key as keyof typeof META] }}</span>
      </div>
      <input type="range" min="0" max="100" v-model.number="w.draft.personality.sliders[key as any]" />
      <div class="between small muted"><span>{{ m.low }}</span><span>{{ m.high }}</span></div>
    </div>

    <hr class="divider" />
    <div class="field">
      <span style="display:block;font-size:12.5px;color:var(--muted);margin-bottom:8px;font-weight:600">性格标签（可多选）</span>
      <div class="row wrap" style="gap:7px">
        <span v-for="t in TAGS" :key="t" class="chip" :class="{ gray: !w.draft.personality.tags.includes(t) }"
              style="cursor:pointer;user-select:none" @click="toggleTag(t)">
          <AppIcon v-if="w.draft.personality.tags.includes(t)" name="check" :size="12" :stroke="3" />{{ t }}
        </span>
      </div>
    </div>

    <div class="banner info" style="display:flex;gap:9px;align-items:flex-start">
      <AppIcon name="clock" :size="17" style="flex-shrink:0;margin-top:1px" />
      <span>作息：默认 12 小时活跃 + 12 小时待机，可自行调整。安静时段（23:00–08:00）不会主动打扰你。</span>
    </div>

    <div class="row">
      <label class="field grow"><span>活跃开始时间（HH:MM）</span>
        <input v-model="w.draft.personality.schedule.active_start" type="text" placeholder="09:00" /></label>
      <label class="field grow"><span>活跃时长（1~24 小时）</span>
        <input v-model.number="w.draft.personality.schedule.active_hours" type="number" min="1" max="24" /></label>
    </div>

    <div class="check-list">
      <label class="check-row">
        <input type="checkbox" v-model="w.draft.personality.schedule.idle_can_reply" />
        <span>待机时仍可回复消息<small class="muted">（只是不主动找你）</small></span>
      </label>
      <label class="check-row">
        <input type="checkbox" v-model="w.draft.personality.schedule.proactive.enabled" />
        <span>允许主动发消息</span>
      </label>
      <label v-if="w.draft.personality.schedule.proactive.enabled" class="field" style="margin:2px 0 8px 26px;max-width:220px">
        <span>每天最多主动发几条</span>
        <input v-model.number="w.draft.personality.schedule.proactive.max_per_day" type="number" min="1" max="20" />
      </label>
      <label class="check-row">
        <input type="checkbox" v-model="w.draft.personality.schedule.auto_browse.enabled" />
        <span>允许待机时自动浏览订阅源<small class="muted">（RSS / 网页）</small></span>
      </label>
      <label class="check-row">
        <input type="checkbox" v-model="w.draft.personality.schedule.proactive.group_enabled" />
        <span class="muted">允许在群里主动发言<small>（不推荐，风控考虑）</small></span>
      </label>
    </div>

    <hr class="divider" />
    <div class="field" style="margin-bottom:0">
      <div class="between" style="margin-bottom:8px">
        <span style="font-size:12.5px;color:var(--muted);font-weight:600">红线规则（它必须遵守）</span>
        <button class="small" @click="addRule"><AppIcon name="plus" :size="14" style="vertical-align:-2px" /> 添加</button>
      </div>
      <div v-for="(_, i) in w.draft.personality.hard_rules" :key="i" class="row" style="margin-bottom:7px">
        <input v-model="w.draft.personality.hard_rules[i]" type="text" placeholder="例如：不许主动提工作压力" />
        <button class="danger" @click="removeRule(i)" title="删除"><AppIcon name="trash" :size="15" /></button>
      </div>
      <p v-if="!w.draft.personality.hard_rules.length" class="small muted" style="margin:0">还没有红线规则，可留空。</p>
    </div>
  </div>
</template>

<style scoped>
.slider-row { margin-bottom: 16px; }
.slider-row__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.slider-row__label { display: inline-flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600; }
.slider-row__label svg { color: var(--brand); }
.slider-row__val {
  min-width: 40px; text-align: center; font-weight: 800; font-size: 13px;
  color: var(--brand-2); background: var(--brand-soft); border-radius: 8px; padding: 2px 8px;
}
.check-list { display: flex; flex-direction: column; gap: 4px; }
.check-row {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 10px; cursor: pointer;
  transition: background 0.15s;
}
.check-row:hover { background: var(--bg-2); }
.check-row span { font-size: 13.5px; }
.check-row small { font-size: 12px; margin-left: 4px; }
</style>
