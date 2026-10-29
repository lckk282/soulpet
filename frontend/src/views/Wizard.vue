<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWizard, type StepId } from '../stores/wizard'
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

onMounted(() => {
  w.restore()
  const s = route.params.step as StepId
  if (s && w.flow.includes(s)) w.step = s
  if (w.flow.indexOf(w.step) < 0) w.step = 'welcome'
})

const jump = (s: StepId) => {
  if (w.visited.includes(s) || w.flow.indexOf(s) <= w.index) w.go(s)
}
</script>

<template>
  <div style="max-width:860px;margin:0 auto;padding:22px 16px">
    <div class="card" style="margin-bottom:14px">
      <div class="row wrap" style="gap:8px">
        <template v-for="(s, i) in w.flow" :key="s">
          <button
            class="ghost"
            :class="{ primary: s === w.step }"
            :disabled="i > w.index && !w.visited.includes(s)"
            @click="jump(s)"
          >{{ i + 1 }}. {{ LABEL[s] }}</button>
        </template>
      </div>
    </div>

    <component :is="MAP[w.step]" />

    <div v-if="w.step !== 'confirm'" class="between" style="margin-top:14px">
      <button :disabled="w.index === 0" @click="w.prev()">上一步</button>
      <button class="primary" :disabled="!w.canNext" @click="w.next()">下一步</button>
    </div>
  </div>
</template>
