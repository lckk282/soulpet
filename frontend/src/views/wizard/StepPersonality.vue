<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
const w = useWizard()

const META: Record<string, { label: string; low: string; high: string }> = {
  clinginess: { label: '粘人程度', low: '高冷疏离', high: '寸步不离' },
  verbosity: { label: '说话风格', low: '惜字如金', high: '话痨小作文' },
  snark: { label: '吐槽频率', low: '温柔体贴', high: '句句带刺' },
  valence: { label: '情绪倾向', low: '阴郁低沉', high: '元气满满' },
  retention: { label: '记忆偏好', low: '金鱼记忆', high: '过目不忘' },
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
  <div class="card">
    <h2>第二步 · 性格与行为规则</h2>

    <div v-for="(m, key) in META" :key="key" class="field">
      <div class="between">
        <span style="font-size:12px">{{ m.label }}</span>
        <span class="small muted">{{ w.draft.personality.sliders[key as keyof typeof META] }}</span>
      </div>
      <input type="range" min="0" max="100" v-model.number="w.draft.personality.sliders[key as any]" />
      <div class="between small muted"><span>{{ m.low }}</span><span>{{ m.high }}</span></div>
    </div>

    <div class="field">
      <span style="display:block;font-size:12px;color:var(--muted);margin-bottom:6px">性格标签（可多选）</span>
      <div class="row wrap" style="gap:6px">
        <span v-for="t in TAGS" :key="t" class="chip" :class="{ gray: !w.draft.personality.tags.includes(t) }"
              style="cursor:pointer" @click="toggleTag(t)">{{ t }}</span>
      </div>
    </div>

    <div class="banner info">作息：默认 12 小时活跃 + 12 小时待机，可自行调整。安静时段（23:00–08:00）不会主动打扰你。</div>

    <div class="row">
      <label class="field grow"><span>活跃开始时间</span>
        <input v-model="w.draft.personality.schedule.active_start" type="text" placeholder="09:00" />
      </label>
      <label class="field grow"><span>活跃时长（小时）</span>
        <input v-model.number="w.draft.personality.schedule.active_hours" type="number" min="1" max="24" />
      </label>
    </div>

    <label style="display:flex;gap:8px;margin-bottom:8px">
      <input type="checkbox" v-model="w.draft.personality.schedule.idle_can_reply" />
      <span>待机时仍可回复消息（只是不主动找你）</span>
    </label>
    <label style="display:flex;gap:8px;margin-bottom:8px">
      <input type="checkbox" v-model="w.draft.personality.schedule.proactive.enabled" />
      <span>允许主动发消息</span>
    </label>
    <label v-if="w.draft.personality.schedule.proactive.enabled" class="field" style="margin-left:24px">
      <span>每天最多主动发几条</span>
      <input v-model.number="w.draft.personality.schedule.proactive.max_per_day" type="number" min="1" max="20" />
    </label>
    <label style="display:flex;gap:8px;margin-bottom:8px">
      <input type="checkbox" v-model="w.draft.personality.schedule.auto_browse.enabled" />
      <span>允许待机时自动浏览订阅源（RSS / 网页）</span>
    </label>
    <label style="display:flex;gap:8px;margin-bottom:12px">
      <input type="checkbox" v-model="w.draft.personality.schedule.proactive.group_enabled" />
      <span class="muted">允许在群里主动发言（不推荐，风控考虑）</span>
    </label>

    <div class="field">
      <div class="between" style="margin-bottom:6px">
        <span style="font-size:12px;color:var(--muted)">红线规则（它必须遵守）</span>
        <button @click="addRule">+ 添加</button>
      </div>
      <div v-for="(_, i) in w.draft.personality.hard_rules" :key="i" class="row" style="margin-bottom:6px">
        <input v-model="w.draft.personality.hard_rules[i]" type="text" placeholder="例如：不许主动提工作压力" />
        <button class="danger" @click="removeRule(i)">删除</button>
      </div>
    </div>
  </div>
</template>
