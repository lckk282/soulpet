<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'

/** 小灵的 9 种姿态，对应 assets/guide 下的立绘 */
type Pose =
  | 'idle' | 'happy' | 'heart' | 'cheer'
  | 'curious' | 'thinking' | 'worried' | 'alert' | 'sad'

type Line = { text: string; pose: Pose }

const props = defineProps<{
  step: string
  deployMode: 'local' | 'cloud'
  errorToken: number
  petName?: string
}>()

// 立绘用 glob 一次性收集，打包时自动带 hash
const FILES = import.meta.glob('../assets/guide/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>

const url = (name: string) => FILES[`../assets/guide/${name}.webp`] ?? ''

// 提前解码，切表情时不闪白
if (typeof window !== 'undefined') {
  Object.values(FILES).forEach((u) => { const i = new Image(); i.src = u })
}

const POSES: Record<Pose, { file: string; label: string }> = {
  idle: { file: 'idle', label: '待命' },
  happy: { file: 'happy-wave', label: '开心' },
  heart: { file: 'happy-heart', label: '比心' },
  cheer: { file: 'cheer', label: '欢呼' },
  curious: { file: 'curious', label: '好奇' },
  thinking: { file: 'thinking', label: '思考' },
  worried: { file: 'worried', label: '担心' },
  alert: { file: 'alert', label: '慌张' },
  sad: { file: 'sad', label: '委屈' },
}

// 每一步的引导台词与姿态。云端部署单独一句，随选择实时切换。
const LINES: Record<string, Line> = {
  welcome: { pose: 'happy', text: '嗨呀！我是你的向导小灵~ 接下来一起把我捏出来吧！' },
  identity: { pose: 'curious', text: '这里给我起名字啦，想好叫什么了吗😺' },
  personality: { pose: 'thinking', text: '拖拖滑块，决定我是粘人还是高冷~ 对了，我记性可好啦！' },
  deploy_local: { pose: 'cheer', text: '本地最省心，这台电脑就是我的小窝！' },
  deploy_cloud: { pose: 'worried', text: '云服务器版本没有画面，不能开启桌宠功能哒' },
  model: { pose: 'worried', text: '这里设置调用上限，防止不小心把额度用光哦' },
  modules: { pose: 'curious', text: '要让我上 QQ，还是趴在桌面上？两个都能开，也都能不开~' },
  qq: { pose: 'thinking', text: '挑个顺手的连接方案吧，记得先看清风险提示哦' },
  pet: { pose: 'cheer', text: '挑套好看的立绘~ 九个角度齐全，我才能活蹦乱跳！' },
  confirm: { pose: 'heart', text: '就差最后一步啦！核对一下，没问题就让我出生吧' },
}
const ERROR_LINE: Line = { pose: 'alert', text: '这里参数好像不对，检查一下格式~' }

const currentLine = computed<Line>(() =>
  props.step === 'deploy'
    ? LINES[`deploy_${props.deployMode}`] || LINES.deploy_local
    : LINES[props.step] || LINES.welcome,
)

const pose = ref<Pose>('happy')
const typed = ref('')
const typing = ref(false)
const replayKey = ref(0)
const justReplayed = ref(false)

let typeTimer: ReturnType<typeof setInterval> | null = null
let errorTimer: ReturnType<typeof setTimeout> | null = null
let hintTimer: ReturnType<typeof setTimeout> | null = null

const prefersReduced = typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const poseSrc = computed(() => url(POSES[pose.value].file))
const poseLabel = computed(() => POSES[pose.value].label)

function clearType() {
  if (typeTimer) { clearInterval(typeTimer); typeTimer = null }
}

function play(line: Line) {
  clearType()
  pose.value = line.pose
  if (prefersReduced || !line.text) {
    typed.value = line.text
    typing.value = false
    return
  }
  typing.value = true
  typed.value = ''
  let i = 0
  const chars = Array.from(line.text)
  const speed = line.pose === 'alert' ? 34 : 46
  typeTimer = setInterval(() => {
    i += 1
    typed.value = chars.slice(0, i).join('')
    if (i >= chars.length) {
      clearType()
      typing.value = false
    }
  }, speed)
}

function applyCurrent() {
  if (errorTimer) { clearTimeout(errorTimer); errorTimer = null }
  play(currentLine.value)
}

function replay() {
  applyCurrent()
  replayKey.value += 1
  justReplayed.value = true
  if (hintTimer) clearTimeout(hintTimer)
  hintTimer = setTimeout(() => { justReplayed.value = false }, 900)
}

// 校验报错：切到慌张，几秒后自动恢复当前步骤的引导
function onError() {
  if (errorTimer) clearTimeout(errorTimer)
  play(ERROR_LINE)
  replayKey.value += 1
  errorTimer = setTimeout(() => applyCurrent(), 4600)
}

watch(() => props.step, applyCurrent, { immediate: true })
watch(() => props.deployMode, () => { if (props.step === 'deploy') applyCurrent() })
watch(() => props.errorToken, (v) => { if (v > 0) onError() })

onBeforeUnmount(() => {
  clearType()
  if (errorTimer) clearTimeout(errorTimer)
  if (hintTimer) clearTimeout(hintTimer)
})
</script>

<template>
  <div class="guide" :class="`guide--${pose}`">
    <div class="guide__bubble" role="status" aria-live="polite">
      <span class="guide__badge">
        <AppIcon name="sparkle" :size="11" />
        小灵 · {{ poseLabel }}
      </span>
      <p class="guide__text">{{ typed }}<span v-if="typing" class="guide__cursor" /></p>
      <span class="guide__tail" />
    </div>

    <button
      :key="replayKey"
      class="guide__pet"
      type="button"
      aria-label="点击小灵，重新播放这一步的提示"
      @click="replay"
    >
      <span class="guide__stage">
        <span class="guide__halo" aria-hidden="true" />
        <Transition name="pose">
          <img
            :key="poseSrc"
            class="guide__img"
            :src="poseSrc"
            :alt="`向导小灵，${poseLabel}`"
            draggable="false"
          />
        </Transition>
        <span class="guide__shadow" aria-hidden="true" />
      </span>
      <span class="guide__replay-tip" :class="{ 'is-on': justReplayed }">
        <AppIcon name="refresh" :size="11" /> 点我重播
      </span>
    </button>
  </div>
</template>

<style scoped>
.guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

/* ---------- 对话气泡 ---------- */
.guide__bubble {
  position: relative;
  width: 100%;
  min-height: 92px;
  background: linear-gradient(168deg, #ffffff 0%, #fffbf6 100%);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 13px 15px 15px;
  box-shadow: 0 10px 30px -14px rgba(93, 62, 37, 0.28), 0 1px 3px rgba(93, 62, 37, 0.05);
  animation: bubble-in 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}
.guide__badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  font-weight: 750;
  letter-spacing: 0.03em;
  color: var(--brand-2);
  background: var(--brand-soft);
  padding: 3px 9px;
  border-radius: 999px;
}
.guide__text {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--text);
  font-weight: 500;
  min-height: 42px;
}
.guide__cursor {
  display: inline-block;
  width: 2px;
  height: 13px;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--brand);
  border-radius: 1px;
  animation: caret 0.72s steps(1) infinite;
}
.guide__tail {
  position: absolute;
  bottom: -8px;
  left: 50%;
  width: 14px;
  height: 14px;
  transform: translateX(-50%) rotate(45deg);
  background: #fffbf6;
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  border-radius: 0 0 3px 0;
}

/* 情绪配色：只在边框与徽标上微妙变化，避免整块变色太吵 */
.guide--alert .guide__bubble { border-color: #f2cfc8; }
.guide--alert .guide__badge { color: var(--danger); background: var(--danger-soft); }
.guide--worried .guide__bubble { border-color: #f2e0c2; }
.guide--worried .guide__badge { color: var(--warn); background: var(--warn-soft); }
.guide--cheer .guide__badge,
.guide--heart .guide__badge { color: #b8602f; background: #fdeadd; }

/* ---------- 立绘 ---------- */
.guide__pet {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  border: none;
  background: transparent;
  padding: 0;
  width: 216px;
  max-width: 100%;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.guide__pet:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 6px;
  border-radius: 24px;
}
.guide__stage {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  display: block;
  animation: pet-float 4.2s ease-in-out infinite;
}
.guide--alert .guide__stage { animation: pet-shake 0.45s ease-in-out 2, pet-float 4.2s ease-in-out 1s infinite; }
.guide--cheer .guide__stage { animation: pet-hop 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 1, pet-float 4.2s ease-in-out 0.8s infinite; }

/* 立绘背后的一团柔光，让白色角色不从纸面上「飘」出来 */
.guide__halo {
  position: absolute;
  left: 50%;
  top: 52%;
  width: 78%;
  height: 78%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 214, 176, 0.5) 0%, rgba(255, 226, 198, 0.22) 45%, transparent 70%);
  filter: blur(6px);
  pointer-events: none;
}
.guide--worried .guide__halo,
.guide--sad .guide__halo { background: radial-gradient(circle, rgba(214, 226, 236, 0.45) 0%, transparent 68%); }
.guide--alert .guide__halo { background: radial-gradient(circle, rgba(255, 198, 180, 0.5) 0%, transparent 68%); }

.guide__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}
.guide__shadow {
  position: absolute;
  left: 50%;
  bottom: 3%;
  width: 46%;
  height: 7%;
  transform: translateX(-50%);
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(126, 92, 62, 0.2) 0%, transparent 72%);
  animation: shadow-pulse 4.2s ease-in-out infinite;
  pointer-events: none;
}

/* 表情切换：交叉淡入 + 轻微位移，不做硬切 */
.pose-enter-active, .pose-leave-active {
  transition: opacity 0.36s ease, transform 0.36s cubic-bezier(0.16, 1, 0.3, 1);
}
.pose-enter-from { opacity: 0; transform: translateY(10px) scale(0.93); }
.pose-leave-to { opacity: 0; transform: translateY(-8px) scale(0.97); }

.guide__replay-tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
  opacity: 0.7;
  transition: opacity 0.2s, color 0.2s, transform 0.2s;
}
.guide__replay-tip.is-on { color: var(--brand); opacity: 1; transform: scale(1.05); }
.guide__pet:hover .guide__replay-tip { opacity: 1; color: var(--brand); }

@keyframes bubble-in {
  from { opacity: 0; transform: translateY(9px) scale(0.97); }
  to { opacity: 1; transform: none; }
}
@keyframes caret { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
@keyframes pet-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@keyframes pet-hop {
  0% { transform: translateY(0) scale(1); }
  42% { transform: translateY(-18px) scale(1.04); }
  100% { transform: translateY(0) scale(1); }
}
@keyframes pet-shake {
  0%, 100% { transform: translateX(0) rotate(0); }
  22% { transform: translateX(-6px) rotate(-2.5deg); }
  60% { transform: translateX(5px) rotate(2deg); }
}
@keyframes shadow-pulse {
  0%, 100% { transform: translateX(-50%) scaleX(1); opacity: 0.85; }
  50% { transform: translateX(-50%) scaleX(0.86); opacity: 0.6; }
}

@media (prefers-reduced-motion: reduce) {
  .guide__bubble, .guide__stage, .guide__cursor, .guide__shadow { animation: none !important; }
  .pose-enter-active, .pose-leave-active { transition: opacity 0.15s linear; }
  .pose-enter-from, .pose-leave-to { transform: none; }
}
</style>
