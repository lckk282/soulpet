<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
const w = useWizard()
</script>

<template>
  <div class="card center" style="padding:34px 22px">
    <div class="spin" style="font-size:52px">🥚</div>
    <h1 style="margin-top:12px">从零创造一只只属于你的 AI 宠物</h1>
    <p class="muted">它会记住你说过的话，按你设定的性格陪你聊天，住在你的电脑里。</p>

    <div class="row" style="margin:20px 0;gap:10px">
      <div class="card" style="flex:1;text-align:left">
        <strong>🔒 数据在你手里</strong>
        <p class="small muted">配置、记忆、密钥全部存在本机或你自己的服务器，不上传第三方。</p>
      </div>
      <div class="card" style="flex:1;text-align:left">
        <strong>🧠 记忆只增不减</strong>
        <p class="small muted">你说过的重要的事会被记住，可查看、可编辑、可导出、可遗忘。</p>
      </div>
      <div class="card" style="flex:1;text-align:left">
        <strong>🔌 模块随开关</strong>
        <p class="small muted">QQ 连接器与桌面桌宠都是可选项，随时开关，互不影响。</p>
      </div>
    </div>

    <div class="card" style="text-align:left;background:var(--warn-soft);border-color:#f0dcb4">
      <strong>开始之前，请确认三件事</strong>
      <label style="display:flex;gap:8px;margin-top:8px"><input type="checkbox" v-model="w.draft.ack.privacy" /><span>我理解配置与记忆保存在本机，我可以随时导出或删除</span></label>
      <label style="display:flex;gap:8px"><input type="checkbox" v-model="w.draft.ack.cost" /><span>我理解调用大模型会产生费用，费用由模型厂商收取，本程序不代收</span></label>
      <label style="display:flex;gap:8px"><input type="checkbox" v-model="w.draft.ack.risk" /><span>我理解若启用 QQ 连接器，将使用第三方桥接协议，存在账号风控风险</span></label>
    </div>

    <p class="small muted" style="margin-top:14px">
      没有 API Key 也能先体验：全程可用内置的「离线体验模式」走通流程，之后在设置里补填即可。
    </p>
  </div>
</template>
