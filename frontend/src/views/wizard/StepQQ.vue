<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
const w = useWizard()

const SCHEMES = [
  { id: 'napcat', star: '★★☆', label: 'NapCat / Lagrange（推荐）', desc: '开源圈主流桥接方案，生态成熟、教程多，支持图片/表情/群白名单', risk: '第三方协议实现，非官方支持，存在风控可能' },
  { id: 'official', star: '★★★', label: '官方开放平台机器人', desc: '腾讯官方机器人，合规、风控最低，需资质申请与审核', risk: '有频率限制与功能约束，申请流程较长' },
  { id: 'lite', star: '★☆☆', label: 'Lite 协议（轻量本地 Bot）', desc: '轻量非官方协议，配置最简单，扫码即用', risk: '风控高，可能限制账号功能；仅限私人自娱，禁止群发与批量操作' },
] as const

const addGroup = () => w.draft.qq.groups.push({ id: '', mode: 'at', keywords: [] })
const removeGroup = (i: number) => w.draft.qq.groups.splice(i, 1)
</script>

<template>
  <div class="card">
    <h2>QQ 对接</h2>
    <p class="small muted">三种方案对应三种玩法，选一个最适合你的。</p>

    <div v-for="s in SCHEMES" :key="s.id" class="radio-card"
         :class="{ active: w.draft.qq.scheme === s.id }" style="margin-bottom:10px"
         @click="w.draft.qq.scheme = s.id">
      <div class="between">
        <strong>{{ s.label }}</strong>
        <span class="chip gray">难度 {{ s.star }}</span>
      </div>
      <p class="small muted" style="margin:4px 0">{{ s.desc }}</p>
      <p class="small" style="color:var(--warn);margin:0">⚠ {{ s.risk }}</p>
    </div>

    <div v-if="w.draft.qq.scheme === 'napcat'" class="field" style="margin-top:12px">
      <label class="field"><span>NapCat WebSocket 地址</span>
        <input v-model="w.draft.qq.ws_url" type="text" placeholder="ws://127.0.0.1:3001" /></label>
      <label class="field"><span>Access Token（与 NapCat 侧一致）</span>
        <input v-model="w.draft.qq.token" type="password" autocomplete="off" /></label>
      <div class="banner info">
        请先自行启动 NapCat 并完成登录。它的 WS 端口<b>不要暴露到公网</b>，否则等于把 QQ 控制权交出去。
      </div>
    </div>

    <div v-if="w.draft.qq.scheme === 'official'" class="field" style="margin-top:12px">
      <label class="field"><span>AppID</span><input v-model="w.draft.qq.app_id" type="text" /></label>
      <label class="field"><span>AppSecret</span><input v-model="w.draft.qq.app_secret" type="password" autocomplete="off" /></label>
      <div class="banner info">官方方案需先在机器人开放平台创建机器人并通过审核；未通过前只能在沙箱/测试环境使用。</div>
    </div>

    <div v-if="w.draft.qq.scheme === 'lite'" class="banner danger" style="margin-top:12px">
      <b>Lite 为非官方逆向协议，违反 QQ 用户协议。</b>
      本项目只保留配置位，不实现、不分发任何协议代码。启用后强制低频、仅限 1 个群 + 私聊白名单、禁止主动消息。
    </div>

    <div class="field" style="margin-top:12px">
      <div class="between" style="margin-bottom:6px">
        <span style="font-size:12px;color:var(--muted)">群白名单（未列出的群一律不回）</span>
        <button @click="addGroup">+ 添加群</button>
      </div>
      <div v-for="(g, i) in w.draft.qq.groups" :key="i" class="row" style="margin-bottom:6px">
        <input v-model="g.id" type="text" placeholder="群号" style="max-width:160px" />
        <select v-model="g.mode" style="max-width:130px">
          <option value="at">@ 才回</option>
          <option value="keyword">关键词触发</option>
          <option value="all">全部回复</option>
        </select>
        <input v-model="g.keywords" type="text" placeholder="关键词，逗号分隔（keyword 模式）" />
        <button class="danger" @click="removeGroup(i)">删</button>
      </div>
    </div>

    <label style="display:flex;gap:8px;margin-top:10px">
      <input type="checkbox" v-model="w.draft.qq.risk_accepted" />
      <span>我已阅读并理解所选方案的风险，仅用于私人自娱，不做群发或批量自动操作</span>
    </label>
  </div>
</template>
