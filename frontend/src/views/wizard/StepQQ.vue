<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
import AppIcon from '../../components/AppIcon.vue'
const w = useWizard()

const SCHEMES = [
  { id: 'napcat', star: '★★☆', label: 'NapCat / Lagrange', tag: '推荐', desc: '开源圈主流桥接方案，生态成熟、教程多，支持图片/表情/群白名单', risk: '第三方协议实现，非官方支持，存在风控可能' },
  { id: 'official', star: '★★★', label: '官方开放平台机器人', tag: '合规', desc: '腾讯官方机器人，合规、风控最低，需资质申请与审核', risk: '有频率限制与功能约束，申请流程较长' },
  { id: 'lite', star: '★☆☆', label: 'Lite 协议（轻量本地 Bot）', tag: '高风险', desc: '轻量非官方协议，配置最简单，扫码即用', risk: '风控高，可能限制账号功能；仅限私人自娱，禁止群发与批量操作' },
] as const

const addGroup = () => w.draft.qq.groups.push({ id: '', mode: 'at', keywords: [] })
const removeGroup = (i: number) => w.draft.qq.groups.splice(i, 1)
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="robot" :size="19" /></span>
      <h2>QQ 对接方案</h2>
    </div>
    <p class="section-sub">三种方案对应三种玩法，选一个最适合你的。</p>

    <div v-for="s in SCHEMES" :key="s.id" class="radio-card"
         :class="{ active: w.draft.qq.scheme === s.id }" style="margin-bottom:10px"
         @click="w.draft.qq.scheme = s.id; w.errors = []">
      <div class="between">
        <strong>{{ s.label }}</strong>
        <span class="chip gray">难度 {{ s.star }} · {{ s.tag }}</span>
      </div>
      <p class="small muted" style="margin:5px 0">{{ s.desc }}</p>
      <p class="small" style="color:var(--warn);margin:0;display:flex;gap:5px;align-items:flex-start">
        <AppIcon name="alert" :size="13" style="flex-shrink:0;margin-top:2px" /> {{ s.risk }}
      </p>
    </div>

    <div v-if="w.draft.qq.scheme === 'napcat'" class="field" style="margin-top:14px">
      <label class="field"><span>NapCat WebSocket 地址</span>
        <input v-model="w.draft.qq.ws_url" type="text" placeholder="ws://127.0.0.1:3001" /></label>
      <label class="field"><span>Access Token（与 NapCat 侧一致）</span>
        <input v-model="w.draft.qq.token" type="password" autocomplete="off" /></label>
      <div class="banner info" style="display:flex;gap:8px;align-items:flex-start">
        <AppIcon name="shield" :size="16" style="flex-shrink:0;margin-top:2px" />
        <span>请先自行启动 NapCat 并完成登录。它的 WS 端口<b>不要暴露到公网</b>，否则等于把 QQ 控制权交出去。</span>
      </div>
    </div>

    <div v-if="w.draft.qq.scheme === 'official'" class="field" style="margin-top:14px">
      <label class="field"><span>AppID</span><input v-model="w.draft.qq.app_id" type="text" /></label>
      <label class="field"><span>AppSecret</span><input v-model="w.draft.qq.app_secret" type="password" autocomplete="off" /></label>
      <div class="banner info">官方方案需先在机器人开放平台创建机器人并通过审核；未通过前只能在沙箱/测试环境使用。</div>
    </div>

    <div v-if="w.draft.qq.scheme === 'lite'" class="banner danger" style="margin-top:14px">
      <b>Lite 为非官方逆向协议，违反 QQ 用户协议。</b>
      本项目只保留配置位，不实现、不分发任何协议代码。启用后强制低频、仅限 1 个群 + 私聊白名单、禁止主动消息。
    </div>

    <div class="field" style="margin-top:16px">
      <div class="between" style="margin-bottom:8px">
        <span style="font-size:12.5px;color:var(--muted);font-weight:600">群白名单（未列出的群一律不回）</span>
        <button class="small" @click="addGroup"><AppIcon name="plus" :size="14" style="vertical-align:-2px" /> 添加群</button>
      </div>
      <div v-for="(g, i) in w.draft.qq.groups" :key="i" class="row" style="margin-bottom:7px">
        <input v-model="g.id" type="text" placeholder="群号" style="max-width:150px" />
        <select v-model="g.mode" style="max-width:130px">
          <option value="at">@ 才回</option>
          <option value="keyword">关键词触发</option>
          <option value="all">全部回复</option>
        </select>
        <input v-model="g.keywords" type="text" placeholder="关键词，逗号分隔（keyword 模式）" />
        <button class="danger" @click="removeGroup(i)" title="删除"><AppIcon name="trash" :size="15" /></button>
      </div>
      <p v-if="!w.draft.qq.groups.length" class="small muted" style="margin:0">未添加群则不会在任何群回复。</p>
    </div>

    <label class="check-row" style="display:flex;gap:9px;align-items:flex-start;margin-top:12px;padding:10px;border-radius:10px;cursor:pointer">
      <input type="checkbox" v-model="w.draft.qq.risk_accepted" style="margin-top:3px" />
      <span style="font-size:13px">我已阅读并理解所选方案的风险，仅用于私人自娱，不做群发或批量自动操作</span>
    </label>
  </div>
</template>
