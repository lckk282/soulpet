<script setup lang="ts">
import { computed, ref } from 'vue'
import { useWizard } from '../../stores/wizard'
import AppIcon from '../../components/AppIcon.vue'
const w = useWizard()
const confirmRisk = ref(false)

const isCloud = computed(() => w.draft.deploy.mode === 'cloud')

const toggleQQ = () => {
  if (!w.draft.modules.qq && !confirmRisk.value) {
    confirmRisk.value = true
    return
  }
  w.draft.modules.qq = !w.draft.modules.qq
  if (w.draft.modules.qq) confirmRisk.value = true
}
const togglePet = () => {
  if (isCloud.value) return
  w.draft.modules.desktop_pet = !w.draft.modules.desktop_pet
}
</script>

<template>
  <div>
    <div class="section-head">
      <span class="ic"><AppIcon name="plug" :size="19" /></span>
      <h2>功能模块开关</h2>
    </div>
    <p class="section-sub">两个模块彼此独立，也可以都不开（只保留网页聊天）。随时能在设置里改。</p>

    <div class="row wrap" style="gap:12px;margin-top:6px">
      <div class="radio-card grow" :class="{ active: w.draft.modules.qq }" style="min-width:220px">
        <div class="between">
          <span class="mod-ic" style="background:#eef0fb;color:#5b62c4"><AppIcon name="robot" :size="22" /></span>
          <button :class="w.draft.modules.qq ? 'primary' : ''" @click="toggleQQ">
            {{ w.draft.modules.qq ? '已开启' : '开启' }}
          </button>
        </div>
        <h3 style="margin-top:12px">QQ 连接器</h3>
        <p class="small muted" style="margin:2px 0">让宠物进群 / 私聊陪你</p>
        <p class="small">难度 ★★☆ · 需要额外配置</p>
        <p class="small" style="color:var(--warn);display:flex;gap:5px;align-items:flex-start">
          <AppIcon name="alert" :size="13" style="flex-shrink:0;margin-top:2px" /> 使用第三方桥接协议，存在账号风控可能
        </p>
      </div>

      <div class="radio-card grow" :class="{ active: w.draft.modules.desktop_pet, disabled: isCloud }" style="min-width:220px">
        <div class="between">
          <span class="mod-ic" style="background:var(--brand-soft);color:var(--brand-2)"><AppIcon name="cat" :size="22" /></span>
          <button :class="w.draft.modules.desktop_pet ? 'primary' : ''" :disabled="isCloud" @click="togglePet">
            {{ w.draft.modules.desktop_pet ? '已开启' : '开启' }}
          </button>
        </div>
        <h3 style="margin-top:12px">桌面悬浮桌宠</h3>
        <p class="small muted" style="margin:2px 0">在桌面上养一只</p>
        <p class="small">难度 ★☆☆ · 需要形象素材包</p>
        <p v-if="!isCloud" class="small muted">风险：无（可选安装桌面端）</p>
        <p v-else class="small" style="color:var(--warn);display:flex;gap:5px;align-items:flex-start">
          <AppIcon name="alert" :size="13" style="flex-shrink:0;margin-top:2px" /> 云服务器没有画面，此功能不可用
        </p>
      </div>
    </div>

    <div v-if="confirmRisk && !w.draft.modules.qq" class="banner warn" style="margin-top:14px;display:flex;gap:9px;align-items:flex-start">
      <AppIcon name="alert" :size="17" style="flex-shrink:0;margin-top:1px" />
      <span>开启 QQ 连接器意味着使用第三方协议与你的 QQ 账号交互，可能触发风控、限制账号功能。仅建议私人自娱、低频使用，不要群发或批量自动操作。确认后再点一次「开启」。</span>
    </div>

    <div v-if="isCloud" class="banner info" style="margin-top:14px">
      当前为<strong>云服务器部署</strong>，桌面桌宠已自动关闭（云端无画面）。若想用桌宠，请回到部署步骤改为本地部署。
    </div>
    <div v-else class="banner info" style="margin-top:14px">
      两个都不开也可以 → 只保留网页聊天，之后随时在「设置」里打开。
    </div>
  </div>
</template>

<style scoped>
.mod-ic { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 12px; }
</style>
