<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

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

onMounted(async () => {
  try { model.value = (await api.get('/model')).config } catch (_) { /* 忽略 */ }
  try { pet.value = (await api.get('/pet')).profile } catch (_) { /* 忽略 */ }
  try { usage.value = (await api.get('/status/usage')).data } catch (_) { /* 忽略 */ }
  try { backend.value = (await api.get('/status')).secret_backend } catch (_) { /* 忽略 */ }
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
    okMsg.value = '已保存' + (model.value.api_key ? '，密钥已写入' + (backend.value === 'keyring' ? '系统钥匙串' : '加密文件') : '')
    model.value.api_key = ''
    model.value = (await api.get('/model')).config
  } catch (e: any) { errMsg.value = e.message }
}

const testModel = async () => {
  okMsg.value = errMsg.value = ''
  const r = await api.post('/model/test', {
    base_url: model.value.base_url, model: model.value.model,
    api_key: model.value.api_key, provider: model.value.provider,
  })
  if (r.ok) okMsg.value = `连通 · ${r.latency_ms}ms · ${r.model}`
  else errMsg.value = r.hint || '连接失败'
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
  if (!confirm('重置会清空全部配置与记忆，回到首次启动状态。确定？')) return
  await api.post('/wizard/reset')
  location.href = '/'
}
</script>

<template>
  <div style="max-width:820px;margin:0 auto;padding:18px 16px" class="col">
    <div v-if="okMsg" class="banner ok">{{ okMsg }}</div>
    <div v-if="errMsg" class="banner danger">{{ errMsg }}</div>

    <div class="card">
      <h2>大模型</h2>
      <div class="row">
        <label class="field grow"><span>服务商</span><input v-model="model.provider" type="text" /></label>
        <label class="field grow"><span>模型名</span><input v-model="model.model" type="text" /></label>
      </div>
      <label class="field"><span>API 地址</span><input v-model="model.base_url" type="text" /></label>
      <label class="field">
        <span>API Key（当前{{ model.has_api_key ? '已保存' : '未设置' }}，密钥存放：{{ backend === 'keyring' ? '系统钥匙串' : '加密文件' }}）</span>
        <input v-model="model.api_key" type="password" placeholder="留空表示不修改" autocomplete="off" />
      </label>
      <div class="row">
        <button @click="testModel">测试连接</button>
        <button class="primary" @click="saveModel">保存</button>
        <button class="danger" @click="removeKey">删除密钥</button>
      </div>
      <div class="row" style="margin-top:10px">
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
      <h2>费用</h2>
      <div class="row wrap" style="gap:8px">
        <span class="chip">今日 ¥{{ usage.today.cost.toFixed(4) }}</span>
        <span class="chip">本月 ¥{{ usage.month.cost.toFixed(4) }}</span>
        <span class="chip gray">累计 ¥{{ usage.total.cost.toFixed(4) }}</span>
        <span v-if="!usage.pricing_known" class="chip warn">未配置单价，费用统计不可用</span>
        <span v-if="usage.budget.capped" class="chip danger">已达月上限，进入省钱待机</span>
      </div>
    </div>

    <div class="card">
      <h2>形象素材</h2>
      <p class="small muted">上传一个 zip 素材包（内含 manifest.json 与九个槽位图片）。</p>
      <input type="file" accept=".zip" @change="onFile" />
      <p v-if="uploading" class="small muted">上传中…</p>
      <ul class="small" style="margin-top:8px">
        <li v-for="p in packs" :key="p.id">{{ p.id }} · {{ p.complete ? '完整' : '缺 ' + p.missing.join('、') }}</li>
      </ul>
    </div>

    <div class="card">
      <h2>备份与重置</h2>
      <div class="row">
        <button @click="api.post('/status/backup').then(r => okMsg = '已备份：' + r.path)">立即备份</button>
        <button class="danger" @click="reset">恢复出厂（清空配置与记忆）</button>
      </div>
      <p class="small muted" style="margin-top:8px">备份包含 config/、数据库与记忆，保存在 data/backups/。</p>
    </div>
  </div>
</template>
