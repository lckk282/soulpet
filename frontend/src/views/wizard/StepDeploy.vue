<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
const w = useWizard()

const pick = (mode: 'local' | 'cloud') => {
  w.draft.deploy.mode = mode
  if (mode === 'cloud' && !w.draft.deploy.cloud) {
    w.draft.deploy.cloud = { host: '', ssh_port: 22, user: 'root', auth_type: 'key', key_path: '', remote_dir: '/opt/soulpet', public_port: 443, domain: '', https: 'none', email: '' }
  }
}
</script>

<template>
  <div class="card">
    <h2>第三步 · 部署载体选择</h2>
    <p class="small muted">这一步决定它住在哪。之后可以在设置里迁移。</p>

    <div class="row wrap" style="gap:12px;margin-top:10px">
      <div class="radio-card grow" :class="{ active: w.draft.deploy.mode === 'local' }" @click="pick('local')">
        <h3>💻 A · 本地部署</h3>
        <p class="small"><strong>这台电脑就是它的家</strong></p>
        <ul class="small muted" style="margin:6px 0 0 16px;padding:0">
          <li>零成本、零配置、数据最快</li>
          <li class="muted">代价：关机就离线</li>
        </ul>
      </div>
      <div class="radio-card grow" :class="{ active: w.draft.deploy.mode === 'cloud' }" @click="pick('cloud')">
        <h3>☁️ B · 云服务器部署</h3>
        <p class="small"><strong>7×12 小时在线</strong></p>
        <ul class="small muted" style="margin:6px 0 0 16px;padding:0">
          <li>关机也在，手机也能聊</li>
          <li class="muted">代价：需要一台你自己的云服务器</li>
        </ul>
      </div>
    </div>

    <div v-if="w.draft.deploy.mode === 'cloud' && w.draft.deploy.cloud" style="margin-top:14px">
      <div class="banner info">最低配置建议：2 核 2G / 20G SSD / Ubuntu 22.04+，并记得在云厂商控制台放行端口。</div>
      <div class="row">
        <label class="field grow"><span>主机 IP 或域名</span>
          <input v-model="w.draft.deploy.cloud.host" type="text" placeholder="1.2.3.4" /></label>
        <label class="field" style="width:120px"><span>SSH 端口</span>
          <input v-model.number="w.draft.deploy.cloud.ssh_port" type="number" /></label>
      </div>
      <div class="row">
        <label class="field grow"><span>登录用户</span>
          <input v-model="w.draft.deploy.cloud.user" type="text" /></label>
        <label class="field grow"><span>部署目录</span>
          <input v-model="w.draft.deploy.cloud.remote_dir" type="text" /></label>
      </div>
      <div class="row">
        <label class="field grow"><span>认证方式</span>
          <select v-model="w.draft.deploy.cloud.auth_type">
            <option value="key">SSH 私钥</option>
            <option value="password">密码</option>
          </select></label>
        <label class="field grow"><span>私钥路径（仅保存路径，不保存内容）</span>
          <input v-model="w.draft.deploy.cloud.key_path" type="text" placeholder="~/.ssh/id_ed25519" /></label>
      </div>
      <div class="row">
        <label class="field grow"><span>对外端口</span>
          <input v-model.number="w.draft.deploy.cloud.public_port" type="number" /></label>
        <label class="field grow"><span>域名（可选，用于 HTTPS）</span>
          <input v-model="w.draft.deploy.cloud.domain" type="text" /></label>
      </div>
      <p class="small muted">云服部署会在「确认生成」后引导你执行，本向导不会自动改动你的服务器。</p>
    </div>
  </div>
</template>
