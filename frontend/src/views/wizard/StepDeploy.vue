<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
import AppIcon from '../../components/AppIcon.vue'
const w = useWizard()

const pick = (mode: 'local' | 'cloud') => {
  w.draft.deploy.mode = mode
  w.errors = []
  if (mode === 'cloud' && !w.draft.deploy.cloud) {
    w.draft.deploy.cloud = { host: '', ssh_port: 22, user: 'root', auth_type: 'key', key_path: '', remote_dir: '/opt/soulpet', public_port: 443, domain: '', https: 'none', email: '' }
  }
}
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="server" :size="19" /></span>
      <h2>部署载体选择</h2>
    </div>
    <p class="section-sub">这一步决定它住在哪。之后可以在设置里迁移。</p>

    <div class="row wrap" style="gap:12px;margin-top:6px">
      <div class="radio-card grow" :class="{ active: w.draft.deploy.mode === 'local' }" @click="pick('local')" style="min-width:220px">
        <div class="between" style="margin-bottom:8px">
          <span class="deploy-ic" style="background:var(--brand-soft);color:var(--brand-2)"><AppIcon name="home" :size="22" /></span>
          <span class="chip ok">推荐新手</span>
        </div>
        <h3>A · 本地部署</h3>
        <p class="small" style="margin:2px 0 8px"><strong>这台电脑就是它的家</strong></p>
        <ul class="small muted" style="margin:0;padding-left:18px">
          <li>零成本、零配置、数据最快</li>
          <li>代价：关机就离线</li>
        </ul>
      </div>
      <div class="radio-card grow" :class="{ active: w.draft.deploy.mode === 'cloud' }" @click="pick('cloud')" style="min-width:220px">
        <div class="between" style="margin-bottom:8px">
          <span class="deploy-ic" style="background:#eef0fb;color:#5b62c4"><AppIcon name="cloud" :size="22" /></span>
          <span class="chip gray">长期在线</span>
        </div>
        <h3>B · 云服务器部署</h3>
        <p class="small" style="margin:2px 0 8px"><strong>7×12 小时在线</strong></p>
        <ul class="small muted" style="margin:0;padding-left:18px">
          <li>关机也在，手机也能聊</li>
          <li>代价：需要一台你自己的云服务器</li>
        </ul>
      </div>
    </div>

    <div v-if="w.draft.deploy.mode === 'cloud'" class="banner warn" style="margin-top:14px;display:flex;gap:9px;align-items:flex-start">
      <AppIcon name="alert" :size="17" style="flex-shrink:0;margin-top:1px" />
      <span><b>云端版没有画面</b>：云服务器上无法使用桌面桌宠功能，选型时请留意。部署参数会先收集好，确认后由你手动执行，向导不会自动改动你的服务器。</span>
    </div>

    <div v-if="w.draft.deploy.mode === 'cloud' && w.draft.deploy.cloud" class="cloud-form">
      <div class="banner info">最低配置建议：2 核 2G / 20G SSD / Ubuntu 22.04+，并记得在云厂商控制台放行端口。</div>
      <div class="row">
        <label class="field grow"><span>主机 IP 或域名 <span style="color:var(--brand)">*</span></span>
          <input v-model="w.draft.deploy.cloud.host" type="text" placeholder="1.2.3.4" /></label>
        <label class="field" style="width:130px"><span>SSH 端口</span>
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
        <label class="field grow"><span>私钥路径（仅存路径，不存内容）</span>
          <input v-model="w.draft.deploy.cloud.key_path" type="text" placeholder="~/.ssh/id_ed25519" /></label>
      </div>
      <div class="row">
        <label class="field grow"><span>对外端口</span>
          <input v-model.number="w.draft.deploy.cloud.public_port" type="number" /></label>
        <label class="field grow"><span>域名（可选，用于 HTTPS）</span>
          <input v-model="w.draft.deploy.cloud.domain" type="text" /></label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.deploy-ic { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 12px; }
.cloud-form { margin-top: 14px; padding-top: 4px; animation: slide-in 0.3s ease; }
@keyframes slide-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .cloud-form { animation: none; } }
</style>
