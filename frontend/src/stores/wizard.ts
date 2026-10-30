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
    // 引导小宠物的「慌张」信号：任何一处校验失败都 +1，向导组件监听后切表情
    guideErrorToken: 0,
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

    /** 触发一次「慌张」表情（校验失败 / 提交失败 / 连接失败共用） */
    bumpGuideError() {
      this.guideErrorToken += 1
    },

    /**
     * 只校验「当前步骤」，返回错误文案列表。
     * 前端即时校验用于引导反馈，后端 /wizard/validate 仍是最终防线。
     */
    validateStep(): string[] {
      const d = this.draft
      const errs: string[] = []
      const hhmm = /^([01]\d|2[0-3]):[0-5]\d$/

      if (this.step === 'welcome') {
        if (!(d.ack.privacy && d.ack.cost && d.ack.risk)) {
          errs.push('先读完并勾选上面的三项知情确认，才能继续呀~')
        }
      } else if (this.step === 'identity') {
        if (!d.identity.name.trim()) errs.push('还没有名字呢，给我起一个吧~')
      } else if (this.step === 'personality') {
        const sch = d.personality.schedule
        if (!hhmm.test(sch.active_start)) errs.push('活跃开始时间要填 HH:MM 格式（如 09:00）')
        if (!(Number(sch.active_hours) >= 1 && Number(sch.active_hours) <= 24)) {
          errs.push('活跃时长要在 1~24 小时之间哦')
        }
        if (Array.isArray(sch.proactive.quiet_hours)) {
          for (const q of sch.proactive.quiet_hours) {
            if (q && !hhmm.test(q)) { errs.push('免打扰时间段格式应为 HH:MM'); break }
          }
        }
        const sliders = d.personality.sliders as Record<string, unknown>
        for (const v of Object.values(sliders)) {
          if (typeof v !== 'number' || Number.isNaN(v) || v < 0 || v > 100) {
            errs.push('性格滑块取值要在 0~100 之间'); break
          }
        }
      } else if (this.step === 'deploy') {
        if (d.deploy.mode === 'cloud') {
          const host = d.deploy.cloud?.host?.trim()
          if (!host) errs.push('云服务器要填一下主机 IP 或域名哦')
        }
      } else if (this.step === 'model') {
        // 没选服务商时只报一条：否则「请先选服务商」+「API 地址格式不对」
        // 会同时糊在用户脸上，而 API 地址他根本还没碰过。
        if (!d.model.model.trim()) {
          errs.push('先选一个服务商；没有 API Key 就点上面那块「用离线体验」')
        } else if (!/^https?:\/\//.test(d.model.base_url)) {
          errs.push('API 地址要以 http:// 或 https:// 开头')
        }
      } else if (this.step === 'qq') {
        if (!d.qq.risk_accepted) errs.push('请先确认所选方案的风险提示')
        if (d.qq.scheme === 'napcat' && !/^wss?:\/\//.test(d.qq.ws_url)) {
          errs.push('NapCat 地址要以 ws:// 或 wss:// 开头')
        }
        if (d.qq.scheme === 'official' && !d.qq.app_id.trim()) {
          errs.push('官方机器人需要填写 AppID')
        }
      }
      return errs
    },

    /** 尝试进入下一步：先校验，失败则触发慌张并返回 false */
    tryNext(): boolean {
      const errs = this.validateStep()
      if (errs.length) {
        this.errors = errs
        this.bumpGuideError()
        return false
      }
      this.errors = []
      this.next()
      return true
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
        this.bumpGuideError()
        throw e
      } finally {
        this.committing = false
      }
    },
  },
})
