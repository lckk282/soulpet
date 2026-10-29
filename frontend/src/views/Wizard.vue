<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWizard, type StepId } from '../stores/wizard'
import WizardGuide from '../components/WizardGuide.vue'
import AppIcon from '../components/AppIcon.vue'
import StepWelcome from './wizard/StepWelcome.vue'
import StepIdentity from './wizard/StepIdentity.vue'
import StepPersonality from './wizard/StepPersonality.vue'
import StepDeploy from './wizard/StepDeploy.vue'
import StepModel from './wizard/StepModel.vue'
import StepModules from './wizard/StepModules.vue'
import StepQQ from './wizard/StepQQ.vue'
import StepPet from './wizard/StepPet.vue'
import StepConfirm from './wizard/StepConfirm.vue'

const w = useWizard()
const route = useRoute()
const router = useRouter()

const MAP: Record<StepId, any> = {
  welcome: StepWelcome, identity: StepIdentity, personality: StepPersonality,
  deploy: StepDeploy, model: StepModel, modules: StepModules,
  qq: StepQQ, pet: StepPet, confirm: StepConfirm,
}
const LABEL: Record<StepId, string> = {
  welcome: '欢迎', identity: '形象', personality: '性格', deploy: '部署',
  model: '模型', modules: '模块', qq: 'QQ 对接', pet: '桌宠形象', confirm: '确认',
}

const progress = computed(() => Math.round(((w.index + 1) / w.flow.length) * 100))

onMounted(() => {
  w.restore()
  const s = route.params.step as StepId
  if (s && w.flow.includes(s)) w.step = s
  if (w.flow.indexOf(w.step) < 0) w.step = 'welcome'
  // 云端部署没有画面，桌宠功能需关闭（防止开出无法使用的功能）
  if (w.draft.deploy.mode === 'cloud' && w.draft.modules.desktop_pet) {
    w.draft.modules.desktop_pet = false
  }
})

// 切步骤时把视口拉回顶部，否则上一步滚到一半的位置会被带过来，
// 新页面一进来就顶着标题被 sticky 顶栏压住。
watch(() => w.step, () => {
  window.scrollTo({ top: 0, behavior: 'auto' })
})

// 切到云端部署时自动关闭桌宠，回到本地不强制
watch(() => w.draft.deploy.mode, (mode) => {
  if (mode === 'cloud' && w.draft.modules.desktop_pet) {
    w.draft.modules.desktop_pet = false
  }
})

const jump = (s: StepId) => {
  if (w.visited.includes(s) || w.flow.indexOf(s) <= w.index) {
    w.errors = []
    w.go(s)
  }
}

const onNext = () => {
  w.tryNext()
  if (w.errors.length) {
    // 滚动到错误提示
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}
</script>

<template>
  <div class="wizard">
    <div class="wizard__top">
      <div class="wizard__title">
        <span class="chip"><AppIcon name="sparkle" :size="12" /> 创造向导</span>
        <h1>捏一只属于你的 AI 宠物</h1>
      </div>
      <span class="progress-pill">第 {{ w.index + 1 }} / {{ w.flow.length }} 步 · {{ progress }}%</span>
    </div>

    <div class="card steps">
      <template v-for="(s, i) in w.flow" :key="s">
        <button
          class="steps__item"
          :class="{ active: s === w.step, done: i < w.index || (w.visited.includes(s) && i !== w.index) }"
          :disabled="i > w.index && !w.visited.includes(s)"
          @click="jump(s)"
        >
          <span class="steps__num">
            <AppIcon v-if="i < w.index || (w.visited.includes(s) && i !== w.index)" name="check" :size="11" :stroke="3" />
            <template v-else>{{ i + 1 }}</template>
          </span>
          <span class="steps__label">{{ LABEL[s] }}</span>
        </button>
      </template>
    </div>

    <div v-if="w.errors.length" class="banner danger inline-error" style="margin-bottom:14px">
      <AppIcon name="alert" :size="18" />
      <div>
        <div v-for="(e, i) in w.errors" :key="i">{{ e }}</div>
      </div>
    </div>

    <div class="wizard__grid">
      <div class="wizard__main">
        <div class="card wizard__card">
          <transition name="step" mode="out-in">
            <component :is="MAP[w.step]" :key="w.step" />
          </transition>
        </div>

        <div v-if="w.step !== 'confirm'" class="wizard__actions">
          <button v-if="w.index > 0" @click="w.prev()">
            <AppIcon name="arrowLeft" :size="15" style="vertical-align:-3px;margin-right:4px" />上一步
          </button>
          <span v-else class="small muted">这一步是起点，填好就能继续</span>
          <button class="primary" @click="onNext">
            下一步<AppIcon name="arrowRight" :size="15" style="vertical-align:-3px;margin-left:5px" />
          </button>
        </div>
      </div>

      <aside class="wizard__guide">
        <WizardGuide
          :step="w.step"
          :deploy-mode="w.draft.deploy.mode"
          :error-token="w.guideErrorToken"
          :pet-name="w.draft.identity.name"
        />
      </aside>
    </div>
  </div>
</template>
