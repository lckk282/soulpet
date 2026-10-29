<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useWizard } from '../../stores/wizard'
import AppIcon from '../../components/AppIcon.vue'

const w = useWizard()
const router = useRouter()

const ROLE_LABEL: Record<string, string> = {
  maid: '女仆', silent_npc: '沉默NPC', buddy: '活泼搭子', cold_assistant: '清冷助手',
  tsundere_cat: '毒舌猫系', senior: '温柔学长学姐',
}
const PROVIDER_LABEL: Record<string, string> = {
  zhipu: '智谱 GLM', qwen: '通义千问', deepseek: 'DeepSeek', openai: 'OpenAI',
  ollama: '本地 Ollama', custom: '自定义', mock: '离线体验',
}
const identityText = computed(() => {
  const d = w.draft
  const roles = d.identity.role_presets.map((r) => ROLE_LABEL[r] || r).join('、')
  const parts = [roles, d.identity.role_custom].filter(Boolean)
  if (parts.length) return parts.join(' + ')
  // 只写了简介也算有身份，别显示成「无」
  return d.identity.bio ? `「${d.identity.bio}」` : '未设定（默认性格）'
})
const rows = computed(() => {
  const d = w.draft
  const s = d.personality.sliders
  return [
    { k: '名字', icon: 'cat', v: d.identity.name || '（未填）', step: 'identity' },
    { k: '身份', icon: 'sparkle', v: identityText.value, step: 'identity' },
    { k: '性格', icon: 'heart', v: `粘人${s.clinginess} 话痨${s.verbosity} 吐槽${s.snark} 元气${s.valence} 记性${s.retention}` + (d.personality.tags.length ? ` · ${d.personality.tags.join('/')}` : ''), step: 'personality' },
    { k: '作息', icon: 'clock', v: `${d.personality.schedule.active_start} 起活跃 ${d.personality.schedule.active_hours}h · 待机${d.personality.schedule.idle_can_reply ? '可回复' : '不回复'}`, step: 'personality' },
    { k: '部署', icon: 'server', v: d.deploy.mode === 'local' ? '本地部署（这台电脑）' : `云服务器 ${d.deploy.cloud?.host || ''}`, step: 'deploy' },
    { k: '模型', icon: 'bolt', v: `${PROVIDER_LABEL[d.model.provider] || d.model.provider} · ${d.model.model || '未填'}${d.model.api_key ? '' : '（离线体验模式）'}`, step: 'model' },
    { k: '预算', icon: 'wallet', v: `日提醒 ¥${d.model.budget.daily_warn_cny} / 月上限 ¥${d.model.budget.monthly_cap_cny}`, step: 'model' },
    { k: '模块', icon: 'plug', v: `QQ：${d.modules.qq ? d.qq.scheme : '关闭'}　桌宠：${d.modules.desktop_pet ? '开启' : '关闭'}`, step: 'modules' },
  ]
})

const goStep = (s: string) => w.go(s as any)

const submit = async () => {
  try {
    await w.commit()
    router.push('/chat')
  } catch (_) { /* 错误已在 store 中 */ }
}
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="check" :size="19" :stroke="2.4" /></span>
      <h2>最后一步 · 确认</h2>
    </div>
    <p class="section-sub">这就是你即将拥有的 {{ w.draft.identity.name || '宠物' }}，确认后我会生成配置、初始化记忆库并拉起服务。</p>

    <div class="confirm-table">
      <div v-for="r in rows" :key="r.k" class="confirm-row">
        <span class="confirm-row__k"><AppIcon :name="r.icon" :size="15" /> {{ r.k }}</span>
        <span class="confirm-row__v">{{ r.v }}</span>
        <button class="ghost small" @click="goStep(r.step)"><AppIcon name="edit" :size="13" style="vertical-align:-2px" /> 编辑</button>
      </div>
    </div>

    <div v-if="w.draft.deploy.mode === 'local'" class="banner warn" style="margin-top:14px">
      本地部署下，电脑关机宠物就离线了。想长期在线可在设置里迁移到云服务器。
    </div>

    <div v-if="w.errors.length" class="banner danger" style="margin-top:14px">
      <div v-for="(e, i) in w.errors" :key="i">{{ e }}</div>
    </div>
    <div v-if="w.warnings.length" class="banner warn" style="margin-top:14px">
      <div v-for="(x, i) in w.warnings" :key="i" class="small">· {{ x }}</div>
    </div>
    <div v-if="w.steps.length" class="banner ok" style="margin-top:14px">
      <div v-for="(x, i) in w.steps" :key="i" class="small">✓ {{ x }}</div>
    </div>

    <div class="between" style="margin-top:18px">
      <button @click="w.prev()"><AppIcon name="arrowLeft" :size="15" style="vertical-align:-3px;margin-right:4px" />上一步</button>
      <button class="primary" :disabled="w.committing" @click="submit">
        <AppIcon name="sparkle" :size="16" style="vertical-align:-3px;margin-right:5px" />
        {{ w.committing ? '生成中…' : '确认生成，启动我的宠物' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.confirm-table { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.confirm-row {
  display: grid; grid-template-columns: 92px 1fr auto; align-items: center; gap: 10px;
  padding: 11px 13px; border-bottom: 1px solid var(--line-2); font-size: 13px;
}
.confirm-row:last-child { border-bottom: none; }
.confirm-row:nth-child(odd) { background: var(--bg-2); }
.confirm-row__k { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-weight: 600; }
.confirm-row__k svg { color: var(--brand); }
.confirm-row__v { word-break: break-word; }
@media (max-width: 480px) {
  .confirm-row { grid-template-columns: 76px 1fr auto; padding: 10px; font-size: 12px; }
}
</style>
