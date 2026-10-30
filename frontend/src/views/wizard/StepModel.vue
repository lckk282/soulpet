<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import { api } from '../../api'
import AppIcon from '../../components/AppIcon.vue'

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
  // 从离线模式切到真服务商时，必须换掉 mock 那个模型名，
  // 否则会把 "mock" 当模型名发给真的接口，然后 404 / 400 一脸懵。
  const fromMock = w.draft.model.provider === 'mock' || w.draft.model.model === 'mock'
  w.draft.model.provider = id
  w.draft.model.base_url = p.base_url
  if (fromMock || !w.draft.model.model) w.draft.model.model = p.model
  w.errors = []
}
const useMock = () => {
  w.draft.model.provider = 'mock'
  w.draft.model.model = 'mock'
  w.draft.model.base_url = 'http://127.0.0.1:1/v1'
  w.errors = []
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
    if (result.value && !result.value.ok) w.bumpGuideError()
  } catch (e: any) {
    result.value = { ok: false, hint: e.message }
    w.bumpGuideError()
  } finally { testing.value = false }
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
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="bolt" :size="19" /></span>
      <h2>大模型 API 与额度</h2>
    </div>
    <p class="section-sub">模型名与价格请以厂商官方信息为准；这里只保存连接信息，不代收任何费用。</p>

    <div class="field">
      <span style="display:block;font-size:12.5px;color:var(--muted);margin-bottom:8px;font-weight:600">选择服务商</span>
      <div class="row wrap" style="gap:7px">
        <span v-for="p in providers" :key="p.id" class="chip" :class="{ gray: w.draft.model.provider !== p.id }"
              style="cursor:pointer;padding:7px 13px;font-size:13px" @click="applyPreset(p.id)">{{ p.label }}</span>
      </div>
    </div>

    <!-- 没有 Key 是最常见的起步状态，别把它藏在一排药丸里 -->
    <div class="offline-box" :class="{ on: w.draft.model.provider === 'mock' }">
      <div class="offline-box__text">
        <strong>还没有 API Key？先用离线体验模式</strong>
        <p class="small muted">内置模拟回复，不联网、不花钱，能把向导和聊天全流程跑通。之后在「设置 → 大模型」补上 Key 就换成真模型。</p>
      </div>
      <button :class="w.draft.model.provider === 'mock' ? 'primary' : 'ghost'" @click="useMock">
        <AppIcon name="sparkle" :size="14" style="vertical-align:-2px;margin-right:4px" />
        {{ w.draft.model.provider === 'mock' ? '已选离线体验' : '用离线体验' }}
      </button>
    </div>

    <div class="row">
      <label class="field grow"><span>模型名</span>
        <input v-model="w.draft.model.model" type="text" placeholder="以厂商后台显示为准" /></label>
    </div>
    <label class="field"><span>API 地址</span>
      <input v-model="w.draft.model.base_url" type="text" placeholder="https://.../v1" /></label>
    <label class="field">
      <span><AppIcon name="lock" :size="12" style="vertical-align:-1px" /> API Key（只写入本机钥匙串，草稿与配置里不留明文）</span>
      <input v-model="w.draft.model.api_key" type="password" placeholder="sk-..." autocomplete="off" />
    </label>

    <div class="row" style="align-items:center">
      <button :disabled="testing || !w.draft.model.api_key" @click="test">
        {{ testing ? '测试中…' : '测试连接' }}
      </button>
      <span v-if="!w.draft.model.api_key" class="small muted">不填 Key 也能继续，先用离线体验模式</span>
    </div>

    <div v-if="result" class="banner" :class="result.ok ? 'ok' : 'danger'" style="margin-top:10px;display:flex;gap:8px;align-items:flex-start">
      <AppIcon :name="result.ok ? 'check' : 'alert'" :size="16" style="flex-shrink:0;margin-top:2px" />
      <span v-if="result.ok">连通 · 延迟 {{ result.latency_ms }}ms · 模型 {{ result.model }}</span>
      <span v-else>{{ result.hint || '连接失败' }}<span v-if="result.detail" class="small"> · {{ result.detail }}</span></span>
    </div>

    <hr class="divider" />
    <h3 style="display:flex;align-items:center;gap:7px;margin-bottom:10px">
      <AppIcon name="wallet" :size="17" style="color:var(--warn)" /> 资源额度与上限
    </h3>
    <div class="row">
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
    <label class="check-row" style="display:flex;align-items:center;gap:9px;padding:8px 10px;cursor:pointer">
      <input type="checkbox" v-model="w.draft.model.budget.auto_idle_on_cap" />
      <span style="font-size:13.5px">达到月上限时自动进入省钱待机</span>
    </label>
  </div>
</template>

<style scoped>
.offline-box {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  margin: 4px 0 18px; padding: 13px 15px;
  border: 1.5px dashed var(--line, #efe7dc); border-radius: 14px;
  background: var(--bg-2, #fdfaf5);
  transition: border-color 0.18s, background 0.18s;
}
.offline-box.on {
  border-style: solid; border-color: var(--brand); background: var(--brand-tint);
}
.offline-box__text { flex: 1 1 260px; min-width: 200px; }
.offline-box__text strong { font-size: 14px; }
.offline-box__text p { margin: 4px 0 0; line-height: 1.55; }
@media (max-width: 560px) {
  .offline-box { flex-direction: column; align-items: stretch; }
  .offline-box button { width: 100%; }
}
</style>
