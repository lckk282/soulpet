<script setup lang="ts">
import { ref } from 'vue'
import { useWizard } from '../../stores/wizard'
const w = useWizard()
const confirmRisk = ref(false)

const toggleQQ = () => {
  if (!w.draft.modules.qq && !confirmRisk.value) {
    confirmRisk.value = true
    return
  }
  w.draft.modules.qq = !w.draft.modules.qq
  if (w.draft.modules.qq) confirmRisk.value = true
}
</script>

<template>
  <div class="card">
    <h2>第五步 · 功能模块开关</h2>
    <p class="small muted">两个模块彼此独立，也可以都不开（只保留网页聊天）。随时能在设置里改。</p>

    <div class="row wrap" style="gap:12px;margin-top:12px">
      <div class="radio-card grow" :class="{ active: w.draft.modules.qq }">
        <div class="between">
          <h3>🤖 QQ 连接器</h3>
          <button :class="w.draft.modules.qq ? 'primary' : ''" @click="toggleQQ">
            {{ w.draft.modules.qq ? '已开启' : '开启' }}
          </button>
        </div>
        <p class="small muted">让宠物进群 / 私聊陪你</p>
        <p class="small">难度 ★★☆ · 需要额外配置</p>
        <p class="small" style="color:var(--warn)">风险：使用第三方桥接协议，存在账号风控可能</p>
      </div>

      <div class="radio-card grow" :class="{ active: w.draft.modules.desktop_pet }">
        <div class="between">
          <h3>🐱 桌面悬浮桌宠</h3>
          <button :class="w.draft.modules.desktop_pet ? 'primary' : ''"
                  @click="w.draft.modules.desktop_pet = !w.draft.modules.desktop_pet">
            {{ w.draft.modules.desktop_pet ? '已开启' : '开启' }}
          </button>
        </div>
        <p class="small muted">在桌面上养一只</p>
        <p class="small">难度 ★☆☆ · 需要形象素材包</p>
        <p class="small muted">风险：无（可选安装桌面端）</p>
      </div>
    </div>

    <div v-if="confirmRisk && !w.draft.modules.qq" class="banner warn" style="margin-top:12px">
      开启 QQ 连接器意味着使用第三方协议与你的 QQ 账号交互，可能触发风控、限制账号功能。
      仅建议私人自娱、低频使用，不要群发或批量自动操作。确认后再点一次「开启」。
    </div>

    <div class="banner info" style="margin-top:12px">
      两个都不开也可以 → 只保留网页聊天，之后随时在「设置」里打开。
    </div>
  </div>
</template>
