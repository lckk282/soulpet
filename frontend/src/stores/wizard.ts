import { defineStore } from 'pinia'
import { api } from '../api'

export type StepId =
  | 'welcome' | 'identity' | 'personality' | 'deploy' | 'model'
  | 'modules' | 'qq' | 'pet' | 'confirm'

const KEY = 'soulpet.wizard.draft'

export const useWizard = defineStore('wizard', {
  state: () => ({
    step: 'welcome' as StepId,
    visited: [] as StepId[],
    draft: {
      version: 1,
      ack: { privacy: false, cost: false, risk: false },
      identity: {
        name: '', role_presets: [] as string[], role_custom: '',
        bio: '', asset_source: 'builtin' as string, asset_pack_id: '' as string,
      },
      personality: {
        sliders: { clinginess: 50, verbosity: 50, snark: 30, valence: 60, retention: 60 },
        tags: [] as string[],
        hard_rules: [] as string[],
        schedule: {
          timezone: 'Asia/Shanghai', active_start: '09:00', active_hours: 12,
          idle_can_reply: true,
          proactive: { enabled: true, max_per_day: 3, quiet_hours: ['23:00', '08:00'], group_enabled: false },
          auto_browse: { enabled: false, sources: [] as any[], max_per_day: 2 },
        },
      },
      deploy: { mode: 'local' as 'local' | 'cloud', cloud: null as any },
      model: {
        provider: 'custom', model: '', base_url: '', api_key: '',
        pricing: { input_per_mtokens: 0, output_per_mtokens: 0, currency: 'CNY', source: 'unknown' as const },
        budget: { daily_warn_cny: 5, monthly_cap_cny: 50, auto_idle_on_cap: true },
        advanced: { temperature_delta: 0, context_turns: 20, stream: true, retries: 2, timeout_sec: 60 },
        embedding_enabled: false, embedding_model: '',
      },
      modules: { qq: false, desktop_pet: false },
      qq: {
        scheme: 'napcat' as 'napcat' | 'official' | 'lite', ws_url: 'ws://127.0.0.1:3001',
        token: '', app_id: '', app_secret: '', groups: [] as any[],
        private_enabled: true, private_whitelist: [] as string[], risk_accepted: false,
      },
      pet: { pack_id: '', scale: 1.0, always_on_top: true, click_through: false, opacity: 100 },
    },
    errors: [] as string[],
    warnings: [] as string[],
    committing: false,
    steps: [] as string[],
  }),

  getters: {
    /** 分支动态的完整步骤序列 */
    flow(state): StepId[] {
      const base: StepId[] = ['welcome', 'identity', 'personality', 'deploy', 'model', 'modules']
      if (state.draft.modules.qq) base.push('qq')
      if (state.draft.modules.desktop_pet) base.push('pet')
      base.push('confirm')
      return base
    },
    index(state): number {
      return this.flow.indexOf(state.step)
    },
    canNext(state): boolean {
      if (state.step === 'welcome') return state.draft.ack.privacy && state.draft.ack.cost && state.draft.ack.risk
      if (state.step === 'identity') return !!state.draft.identity.name.trim()
      if (state.step === 'model') return !!state.draft.model.model && /^https?:\/\//.test(state.draft.model.base_url)
      if (state.step === 'qq') return state.draft.qq.risk_accepted &&
        (state.draft.qq.scheme === 'napcat' ? /^wss?:\/\//.test(state.draft.qq.ws_url) : !!state.draft.qq.app_id)
      if (state.step === 'deploy') return state.draft.deploy.mode === 'local' || !!state.draft.deploy.cloud?.host
      return true
    },
  },

  actions: {
    restore() {
      const raw = localStorage.getItem(KEY)
      if (raw) {
        try {
          const d = JSON.parse(raw)
          // 密钥不信任本地缓存，需要用户重新填写
          this.draft = { ...this.draft, ...d, model: { ...this.draft.model, ...(d.model || {}), api_key: '' } }
        } catch (_) { /* 坏数据忽略 */ }
      }
    },
    saveLocal() {
      const copy = JSON.parse(JSON.stringify(this.draft))
      copy.model.api_key = ''
      copy.qq.token = ''
      copy.qq.app_secret = ''
      localStorage.setItem(KEY, JSON.stringify(copy))
    },
    async saveRemote() {
      try { await api.post('/wizard/draft', { draft: this.draft }) } catch (_) { /* 草稿丢失不阻断 */ }
    },
    go(step: StepId) {
      this.step = step
      if (!this.visited.includes(step)) this.visited.push(step)
      this.saveLocal(); this.saveRemote()
    },
    next() {
      const i = this.index
      const nxt = this.flow[Math.min(i + 1, this.flow.length - 1)]
      this.go(nxt)
    },
    prev() {
      const i = this.index
      this.go(this.flow[Math.max(i - 1, 0)])
    },
    async commit() {
      this.committing = true
      this.errors = []; this.warnings = []; this.steps = []
      try {
        const r = await api.post('/wizard/commit', { draft: this.draft })
        this.steps = r.steps || []
        this.warnings = r.warnings || []
        localStorage.removeItem(KEY)
        return r
      } catch (e: any) {
        this.errors = [e.message || String(e)]
        throw e
      } finally {
        this.committing = false
      }
    },
  },
})
