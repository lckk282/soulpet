<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

const model = ref<any>({
  provider: '', model: '', base_url: '', api_key: '', has_api_key: false,
  pricing: { input_per_mtokens: 0, output_per_mtokens: 0, currency: 'CNY', source: 'unknown' },
  budget: { daily_warn_cny: 5, monthly_cap_cny: 50, auto_idle_on_cap: true },
  advanced: { temperature_delta: 0, context_turns: 20, stream: true, retries: 2, timeout_sec: 60 },
})
const pet = ref<any>({})
const usage = ref<any>(null)
const okMsg = ref('')
const errMsg = ref('')
const packs = ref<any[]>([])
const uploading = ref(false)
const backend = ref('')
const plaintext = ref(false)

const isOffline = computed(() => (model.value.provider || '') === 'mock')

// 没有钥匙串又没有主密码时，文件后端只能存明文 —— 不能骗用户说「已加密」
const backendLabel = computed(() => {
  if (backend.value === 'keyring') return '系统钥匙串'
  return plaintext.value ? '本地文件（明文，建议设置主密码）' : '加密文件'
})

onMounted(async () => {
  try { model.value = (await api.get('/model')).config } catch (_) { /* 忽略 */ }
  try { pet.value = (await api.get('/pet')).profile } catch (_) { /* 忽略 */ }
  try { usage.value = (await api.get('/status/usage')).data } catch (_) { /* 忽略 */ }
  try {
    const st = await api.get('/status')
    backend.value = st.secret_backend
    plaintext.value = !!st.secret_plaintext
  } catch (_) { /* 忽略 */ }
  try { packs.value = (await api.get('/pet/packs')).items } catch (_) { /* 忽略 */ }
})

const saveModel = async () => {
  okMsg.value = errMsg.value = ''
  try {
    await api.put('/model', {
      provider: model.value.provider, model: model.value.model, base_url: model.value.base_url,
      api_key: model.value.api_key || '', pricing: model.value.pricing, budget: model.value.budget,
      advanced: model.value.advanced,
    })
    okMsg.value = '已保存' + (model.value.api_key ? '，密钥已写入' + backendLabel.value : '')
    model.value.api_key = ''
    model.value = (await api.get('/model')).config
  } catch (e: any) { errMsg.value = e.message }
}

const testModel = async () => {
  okMsg.value = errMsg.value = ''
  try {
    const r = await api.post('/model/test', {
      base_url: model.value.base_url, model: model.value.model,
      api_key: model.value.api_key, provider: model.value.provider,
    })
    if (r.ok) okMsg.value = `连通 · ${r.latency_ms}ms · ${r.model}`
    else errMsg.value = r.hint || '连接失败'
  } catch (e: any) { errMsg.value = e.message }
}

const removeKey = async () => {
  if (!confirm('删除本机保存的 API Key？')) return
  await api.del('/model/key')
  model.value = (await api.get('/model')).config
  okMsg.value = '已删除密钥'
}

const onFile = async (e: any) => {
  const f = e.target.files?.[0]
  if (!f) return
  const fd = new FormData()
  fd.append('file', f)
  uploading.value = true
  try {
    const res = await fetch('/api/pet/packs/upload', { method: 'POST', body: fd })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '上传失败')
    okMsg.value = `已导入素材包 ${data.pack_id}${data.report?.complete ? '（完整）' : '（缺 ' + (data.report?.missing_labels || []).join('、') + '）'}`
    packs.value = (await api.get('/pet/packs')).items
  } catch (err: any) { errMsg.value = err.message }
  finally { uploading.value = false }
}

const reset = async () => {
  if (!confirm('这会删掉全部配置、记忆、聊天记录和已保存的密钥，回到第一次启动的状态。\n\n删之前会自动打一个备份包放在 data/backups/，需要时还能捞回来。\n\n确定继续？')) return
  try {
    const r = await api.post('/wizard/reset')
    // 口令 Cookie 也要清掉，否则下次打开会以为还登录着
    document.cookie = 'soulpet_token=; Max-Age=0; path=/'
    alert(r.message || '已恢复出厂，正在跳回向导…')
    location.href = '/'
  } catch (e: any) { errMsg.value = e.message }
}
const backup = async () => {
  try { const r = await api.post('/status/backup'); okMsg.value = '已备份：' + r.path }
  catch (e: any) { errMsg.value = e.message }
}
</script>

<template>
  <div class="page col">
    <div class="page-head" style="margin-bottom:4px">
      <span class="page-head__eyebrow">偏好设置</span>
      <h1>设置</h1>
      <p>模型、密钥、费用上限、形象素材与数据备份，都在这里管理。</p>
    </div>

    <div v-if="okMsg" class="banner ok"><AppIcon name="check" :size="15" style="vertical-align:-3px" /> {{ okMsg }}</div>
    <div v-if="errMsg" class="banner danger"><AppIcon name="alert" :size="15" style="vertical-align:-3px" /> {{ errMsg }}</div>

    <div class="card">
      <h2 style="display:flex;align-items:center;gap:8px"><AppIcon name="bolt" :size="18" style="color:var(--brand)" /> 大模型</h2>

      <!-- mock 是内部代号，别直接把 "mock / mock / http://127.0.0.1:1/v1" 甩给用户 -->
      <div v-if="isOffline" class="banner info" style="margin-bottom:12px;align-items:flex-start">
        <AppIcon name="sparkle" :size="15" style="vertical-align:-3px" />
        <div>
          当前是<strong>离线体验模式</strong>：用内置模拟回复，不联网、不花钱。
          想换成真模型，把下面几项改成厂商信息、填上 API Key，点「保存」即可。
        </div>
      </div>

      <div class="row">
        <label class="field grow"><span>服务商</span><input v-model="model.provider" type="text" /></label>
        <label class="field grow"><span>模型名</span><input v-model="model.model" type="text" /></label>
      </div>
      <label class="field"><span>API 地址{{ isOffline ? '（离线模式占位，可忽略）' : '' }}</span><input v-model="model.base_url" type="text" /></label>
      <label class="field">
        <span>API Key（当前{{ model.has_api_key ? '已保存' : '未设置' }} · 存放：{{ backendLabel }}）</span>
        <input v-model="model.api_key" type="password" placeholder="留空表示不修改" autocomplete="off" />
      </label>
      <div class="row wrap" style="gap:8px">
        <button @click="testModel"><AppIcon name="bolt" :size="14" style="vertical-align:-2px" /> 测试连接</button>
        <button class="primary" @click="saveModel">保存</button>
        <button class="danger" @click="removeKey"><AppIcon name="trash" :size="14" style="vertical-align:-2px" /> 删除密钥</button>
      </div>
      <hr class="divider" />
      <div class="row">
        <label class="field grow"><span>输入单价（元/百万 tokens）</span>
          <input v-model.number="model.pricing.input_per_mtokens" type="number" step="0.1" /></label>
        <label class="field grow"><span>输出单价</span>
          <input v-model.number="model.pricing.output_per_mtokens" type="number" step="0.1" /></label>
      </div>
      <div class="row">
        <label class="field grow"><span>日提醒（元）</span>
          <input v-model.number="model.budget.daily_warn_cny" type="number" /></label>
        <label class="field grow"><span>月上限（元）</span>
          <input v-model.number="model.budget.monthly_cap_cny" type="number" /></label>
      </div>
      <button class="primary" @click="saveModel">保存预算与价格</button>
    </div>

    <div v-if="usage" class="card">
      <h2 style="display:flex;align-items:center;gap:8px"><AppIcon name="wallet" :size="18" style="color:var(--warn)" /> 费用</h2>
      <div class="row wrap" style="gap:8px">
        <span class="chip">今日 ¥{{ usage.today.cost.toFixed(4) }}</span>
        <span class="chip">本月 ¥{{ usage.month.cost.toFixed(4) }}</span>
        <span class="chip gray">累计 ¥{{ usage.total.cost.toFixed(4) }}</span>
        <span v-if="!usage.pricing_known" class="chip warn">未配置单价，费用统计不可用</span>
        <span v-if="usage.budget.capped" class="chip danger">已达月上限，进入省钱待机</span>
      </div>
    </div>

    <div class="card">
      <h2 style="display:flex;align-items:center;gap:8px"><AppIcon name="image" :size="18" style="color:var(--brand)" /> 形象素材</h2>
      <p class="small muted">上传一个 zip 素材包（内含 manifest.json 与九个槽位图片）。</p>
      <input type="file" accept=".zip" @change="onFile" />
      <p v-if="uploading" class="small muted">上传中…</p>
      <ul class="small" style="margin-top:8px">
        <li v-for="p in packs" :key="p.id">{{ p.id }} · {{ p.complete ? '完整' : '缺 ' + p.missing.join('、') }}</li>
      </ul>
    </div>

    <div class="card">
      <h2 style="display:flex;align-items:center;gap:8px"><AppIcon name="shield" :size="18" style="color:var(--ok)" /> 备份与重置</h2>
      <div class="row wrap" style="gap:8px">
        <button @click="backup"><AppIcon name="refresh" :size="14" style="vertical-align:-2px" /> 立即备份</button>
        <button class="ghost" @click="$router.push('/?edit=1')">
          <AppIcon name="sparkle" :size="14" style="vertical-align:-2px" /> 重新运行创造向导
        </button>
        <button class="danger" @click="reset">恢复出厂（清空配置、记忆与密钥）</button>
      </div>
      <p class="small muted" style="margin-top:8px">
        备份包含 config/、数据库与记忆，保存在 data/backups/。恢复出厂前会自动先备份一份。
        「重新运行向导」只覆盖宠物配置，聊天记录和记忆都保留。
      </p>
    </div>
  </div>
</template>
