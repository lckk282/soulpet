<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useWizard } from '../../stores/wizard'

const w = useWizard()
const router = useRouter()

const ROLE_LABEL: Record<string, string> = {
  maid: '女仆', silent_npc: '沉默NPC', buddy: '活泼搭子', cold_assistant: '清冷助手',
  tsundere_cat: '毒舌猫系', senior: '温柔学长学姐',
}
const rows = computed(() => {
  const d = w.draft
  const s = d.personality.sliders
  return [
    { k: '名字', v: d.identity.name || '（未填）', step: 'identity' },
    { k: '身份', v: (d.identity.role_presets.map((r) => ROLE_LABEL[r] || r).join('、') || '无') + (d.identity.role_custom ? ` + ${d.identity.role_custom}` : ''), step: 'identity' },
    { k: '性格', v: `粘人${s.clinginess} 话痨${s.verbosity} 吐槽${s.snark} 元气${s.valence} 记性${s.retention}` + (d.personality.tags.length ? ` · ${d.personality.tags.join('/')}` : ''), step: 'personality' },
    { k: '作息', v: `${d.personality.schedule.active_start} 起活跃 ${d.personality.schedule.active_hours}h · 待机${d.personality.schedule.idle_can_reply ? '可回复' : '不回复'} · 主动最多 ${d.personality.schedule.proactive.enabled ? d.personality.schedule.proactive.max_per_day + ' 条/天' : '关闭'}`, step: 'personality' },
    { k: '部署', v: d.deploy.mode === 'local' ? '本地部署（这台电脑）' : `云服务器 ${d.deploy.cloud?.host || ''}`, step: 'deploy' },
    { k: '模型', v: `${d.model.provider} · ${d.model.model || '未填'}${d.model.api_key ? '' : '（离线体验模式）'}`, step: 'model' },
    { k: '预算', v: `日提醒 ¥${d.model.budget.daily_warn_cny} / 月上限 ¥${d.model.budget.monthly_cap_cny}`, step: 'model' },
    { k: '模块', v: `QQ：${d.modules.qq ? d.qq.scheme : '关闭'}　桌宠：${d.modules.desktop_pet ? '开启' : '关闭'}`, step: 'modules' },
  ]
})

const goStep = (s: string) => w.go(s as any)

const submit = async () => {
  try {
    const r = await w.commit()
    router.push('/chat')
  } catch (_) { /* 错误已在 store 中 */ }
}
</script>

<template>
  <div class="card">
    <h2>最后一步 · 确认</h2>
    <p class="small muted">这就是你的 {{ w.draft.identity.name || '宠物' }}，确认后我会生成配置、初始化记忆库并拉起服务。</p>

    <table style="margin-top:10px">
      <tbody>
        <tr v-for="r in rows" :key="r.k">
          <td style="width:80px" class="muted">{{ r.k }}</td>
          <td>{{ r.v }}</td>
          <td style="width:60px;text-align:right"><button class="ghost small" @click="goStep(r.step)">编辑</button></td>
        </tr>
      </tbody>
    </table>

    <div v-if="w.draft.deploy.mode === 'local'" class="banner warn" style="margin-top:12px">
      本地部署下，电脑关机宠物就离线了。想长期在线可在设置里迁移到云服务器。
    </div>

    <div v-if="w.errors.length" class="banner danger" style="margin-top:12px">
      <div v-for="(e, i) in w.errors" :key="i">{{ e }}</div>
    </div>
    <div v-if="w.warnings.length" class="banner warn" style="margin-top:12px">
      <div v-for="(x, i) in w.warnings" :key="i" class="small">· {{ x }}</div>
    </div>
    <div v-if="w.steps.length" class="banner ok" style="margin-top:12px">
      <div v-for="(x, i) in w.steps" :key="i" class="small">✓ {{ x }}</div>
    </div>

    <div class="between" style="margin-top:16px">
      <button @click="w.prev()">上一步</button>
      <button class="primary" :disabled="w.committing" @click="submit">
        {{ w.committing ? '生成中…' : '✓ 确认生成，启动我的宠物' }}
      </button>
    </div>
  </div>
</template>
