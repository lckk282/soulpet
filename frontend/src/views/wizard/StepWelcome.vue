<script setup lang="ts">
import { useWizard } from '../../stores/wizard'
import AppIcon from '../../components/AppIcon.vue'
const w = useWizard()

const features = [
  { icon: 'lock', tint: 'var(--brand-soft)', color: 'var(--brand-2)', title: '数据在你手里', desc: '配置、记忆、密钥全部存在本机或你自己的服务器，不上传第三方。' },
  { icon: 'brain', tint: 'var(--ok-soft)', color: 'var(--ok)', title: '记忆可掌控', desc: '你说过的重要的事会被记住，可查看、可编辑、可导出、可遗忘。' },
  { icon: 'plug', tint: '#fdf1d8', color: '#a9761f', title: '模块随开关', desc: 'QQ 连接器与桌面桌宠都是可选项，随时开关，互不影响。' },
]

const acks: { key: 'privacy' | 'cost' | 'risk'; text: string }[] = [
  { key: 'privacy', text: '我理解配置与记忆保存在本机，我可以随时导出或删除' },
  { key: 'cost', text: '我理解调用大模型会产生费用，费用由模型厂商收取，本程序不代收' },
  { key: 'risk', text: '我理解若启用 QQ 连接器，将使用第三方桥接协议，存在账号风控风险' },
]
</script>

<template>
  <div>
    <div style="padding:2px 0 2px">
      <h2 style="font-size:22px;margin:0 0 6px">从零创造一只只属于你的 AI 宠物</h2>
      <p class="muted" style="margin:0;font-size:13.5px">
        它会记住你说过的话，按你设定的性格陪你聊天，安安静静地住在你自己的设备里。
      </p>
    </div>

    <div class="feature-grid">
      <div v-for="f in features" :key="f.title" class="feature">
        <div class="ic" :style="{ background: f.tint, color: f.color }"><AppIcon :name="f.icon" :size="20" /></div>
        <h3>{{ f.title }}</h3>
        <p class="muted">{{ f.desc }}</p>
      </div>
    </div>

    <div class="card" style="background:var(--bg-2);box-shadow:none">
      <h3 style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <AppIcon name="shield" :size="18" style="color:var(--brand)" /> 开始之前，请确认三件事
      </h3>
      <label
        v-for="a in acks" :key="a.key"
        class="radio-card"
        :class="{ active: w.draft.ack[a.key] }"
        style="display:flex;align-items:center;gap:10px;padding:11px 13px;margin-bottom:8px"
      >
        <input type="checkbox" v-model="w.draft.ack[a.key]" />
        <span style="font-size:13px">{{ a.text }}</span>
      </label>
    </div>

    <p class="small muted center" style="margin-top:14px">
      <AppIcon name="sparkle" :size="13" style="vertical-align:-2px;color:var(--brand)" />
      没有 API Key 也能先体验：全程可用内置的「离线体验模式」走通流程，之后在设置里补填即可。
    </p>
  </div>
</template>
