<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import { api } from '../../api'

const w = useWizard()
const providers = ref<any[]>([])
const testing = ref(false)
const result = ref<any>(null)

onMounted(async () => {
  try { providers.value = (await api.get('/model/registry')).items } catch (_) { /* 忽略 */ }
})

const applyPreset = (id: string) => {
  const p = providers.value.find((x) => x.id === id)
  if (!p) return
  w.draft.model.provider = id
  w.draft.model.base_url = p.base_url
  if (!w.draft.model.model) w.draft.model.model = p.model
}
const useMock = () => {
  w.draft.model.provider = 'mock'
  w.draft.model.model = 'mock'
  w.draft.model.base_url = 'http://127.0.0.1:1/v1'
}

const test = async () => {
  testing.value = true
  result.value = null
  try {
    result.value = await api.post('/model/test', {
      base_url: w.draft.model.base_url,
      model: w.draft.model.model,
      api_key: w.draft.model.api_key,
      provider: w.draft.model.provider,
    })
  } catch (e: any) { result.value = { ok: false, hint: e.message } }
  finally { testing.value = false }
}

const estimated = computed(() => {
  const pi = w.draft.model.pricing.input_per_mtokens || 0
  const po = w.draft.model.pricing.output_per_mtokens || 0
  if (!pi && !po) return null
  const daily = 60 * (300 / 1e6 * pi + 400 / 1e6 * po)
  return `按每天 60 条消息估算 ≈ ¥${daily.toFixed(2)} / 天`
})
</script>

<template>
  <div class="card">
    <h2>第四步 · 大模型 API 配置</h2>
    <p class="small muted">模型名与价格请以厂商官方信息为准；这里只保存连接信息，不代收任何费用。</p>

    <div class="field">
      <span style="display:block;font-size:12px;color:var(--muted);margin-bottom:6px">选择服务商</span>
      <div class="row wrap" style="gap:6px">
        <span v-for="p in providers" :key="p.id" class="chip" :class="{ gray: w.draft.model.provider !== p.id }"
              style="cursor:pointer" @click="applyPreset(p.id)">{{ p.label }}</span>
        <span class="chip" :class="{ gray: w.draft.model.provider !== 'mock' }" style="cursor:pointer" @click="useMock">先不填，离线体验</span>
      </div>
    </div>

    <div class="row">
      <label class="field grow"><span>模型名</span>
        <input v-model="w.draft.model.model" type="text" placeholder="以厂商后台显示为准" /></label>
    </div>
    <label class="field"><span>API 地址</span>
      <input v-model="w.draft.model.base_url" type="text" placeholder="https://.../v1" /></label>
    <label class="field"><span>API Key（只写入本机钥匙串，草稿与配置里不留明文）</span>
      <input v-model="w.draft.model.api_key" type="password" placeholder="sk-..." autocomplete="off" /></label>

    <div class="row" style="align-items:flex-end">
      <button :disabled="testing || !w.draft.model.api_key" @click="test">{{ testing ? '测试中…' : '测试连接' }}</button>
      <span v-if="!w.draft.model.api_key" class="small muted">不填 Key 也能继续，离线体验模式</span>
    </div>

    <div v-if="result" class="banner" :class="result.ok ? 'ok' : 'danger'" style="margin-top:10px">
      <span v-if="result.ok">✓ 连通 · 延迟 {{ result.latency_ms }}ms · 模型 {{ result.model }}</span>
      <span v-else>✗ {{ result.hint || '连接失败' }}<span v-if="result.detail" class="small"> · {{ result.detail }}</span></span>
    </div>

    <div class="row" style="margin-top:10px">
      <label class="field grow"><span>输入单价（元 / 百万 tokens，可留空）</span>
        <input v-model.number="w.draft.model.pricing.input_per_mtokens" type="number" step="0.1" /></label>
      <label class="field grow"><span>输出单价（元 / 百万 tokens，可留空）</span>
        <input v-model.number="w.draft.model.pricing.output_per_mtokens" type="number" step="0.1" /></label>
    </div>
    <p v-if="estimated" class="small muted">{{ estimated }}（价格来自你填的单价表，以厂商公告为准）</p>
    <p v-else class="small muted">未填单价时费用统计不可用，可之后在「设置 → 费用」里补充。</p>

    <div class="row" style="margin-top:8px">
      <label class="field grow"><span>日消费提醒（元）</span>
        <input v-model.number="w.draft.model.budget.daily_warn_cny" type="number" /></label>
      <label class="field grow"><span>月消费上限（元）</span>
        <input v-model.number="w.draft.model.budget.monthly_cap_cny" type="number" /></label>
    </div>
    <label style="display:flex;gap:8px">
      <input type="checkbox" v-model="w.draft.model.budget.auto_idle_on_cap" />
      <span>达到月上限时自动进入省钱待机</span>
    </label>
  </div>
</template>
