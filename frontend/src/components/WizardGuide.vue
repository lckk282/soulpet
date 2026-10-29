<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'

type Mood = 'happy' | 'curious' | 'thinking' | 'worried' | 'alert' | 'celebrate'
type Line = { text: string; mood: Mood }

const props = defineProps<{
  step: string
  deployMode: 'local' | 'cloud'
  errorToken: number
  petName?: string
}>()

// 每一步的引导台词与表情。云端部署单独给一句，随选择实时切换。
const LINES: Record<string, Line> = {
  welcome: { mood: 'happy', text: '嗨呀！我是你的向导小灵~ 接下来一起把我捏出来吧！' },
  identity: { mood: 'curious', text: '这里给我起名字啦，想好叫什么了吗😺' },
  personality: { mood: 'thinking', text: '拖拖滑块，决定我是粘人还是高冷~ 对了，我记性可好啦！' },
  deploy_local: { mood: 'happy', text: '选我住哪儿呀~ 本地最省心，这台电脑就是我的小窝！' },
  deploy_cloud: { mood: 'worried', text: '云服务器版本没有画面，不能开启桌宠功能哒' },
  model: { mood: 'worried', text: '这里设置调用上限，防止不小心把额度用光哦' },
  modules: { mood: 'curious', text: '要让我上 QQ，还是趴在桌面上？两个都能开，也都能不开~' },
  qq: { mood: 'thinking', text: '挑个顺手的连接方案吧，记得先看清风险提示哦' },
  pet: { mood: 'celebrate', text: '挑套好看的立绘~ 九个角度齐全，我才能活蹦乱跳！' },
  confirm: { mood: 'celebrate', text: '就差最后一步啦！核对一下，没问题就让我出生吧' },
}
const ERROR_LINE: Line = { mood: 'alert', text: '这里参数好像不对，检查一下格式~' }

const currentLine = computed<Line>(() => {
  if (props.step === 'deploy') return LINES[`deploy_${props.deployMode}`] || LINES.deploy_local
  return LINES[props.step] || LINES.welcome
})

const mood = ref<Mood>('happy')
const typed = ref('')
const typing = ref(false)
const replayKey = ref(0)
const justReplayed = ref(false)

let typeTimer: ReturnType<typeof setInterval> | null = null
let errorTimer: ReturnType<typeof setTimeout> | null = null
let hintTimer: ReturnType<typeof setTimeout> | null = null

const prefersReduced = typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function clearType() {
  if (typeTimer) { clearInterval(typeTimer); typeTimer = null }
}

function play(line: Line) {
  clearType()
  mood.value = line.mood
  if (prefersReduced || !line.text) {
    typed.value = line.text
    typing.value = false
    return
  }
  typing.value = true
  typed.value = ''
  let i = 0
  const chars = Array.from(line.text)
  const speed = line.mood === 'alert' ? 34 : 46
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

// 校验报错：切到慌张表情，几秒后自动恢复当前步骤的引导
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

const isAlert = computed(() => mood.value === 'alert')
const isWorried = computed(() => mood.value === 'worried')
const isCelebrate = computed(() => mood.value === 'celebrate')
const isThinking = computed(() => mood.value === 'thinking')
const isCurious = computed(() => mood.value === 'curious')
const isHappy = computed(() => mood.value === 'happy')

const MOOD_LABEL: Record<Mood, string> = {
  happy: '开心', curious: '好奇', thinking: '思考', worried: '担心', alert: '慌张', celebrate: '欢呼',
}
</script>

<template>
  <div class="guide" :class="`guide--${mood}`">
    <div class="guide__bubble" role="status" aria-live="polite">
      <span class="guide__badge"><AppIcon name="sparkle" :size="12" /> 向导小灵 · {{ MOOD_LABEL[mood] }}</span>
      <p class="guide__text">{{ typed }}<span v-if="typing" class="guide__cursor">▍</span></p>
      <span class="guide__tail" />
    </div>

    <button
      :key="replayKey"
      class="guide__pet"
      type="button"
      aria-label="点击小宠物，重新播放这一步的提示"
      @click="replay"
    >
      <svg viewBox="0 0 200 200" class="pet-svg" aria-hidden="true">
        <defs>
          <radialGradient id="spBody" cx="42%" cy="34%" r="72%">
            <stop offset="0%" stop-color="#fff7ee" />
            <stop offset="58%" stop-color="#ffe6cd" />
            <stop offset="100%" stop-color="#f7cf9f" />
          </radialGradient>
          <linearGradient id="spBelly" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#fffaf3" />
            <stop offset="100%" stop-color="#ffecda" />
          </linearGradient>
          <linearGradient id="spScarf" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#e8845b" />
            <stop offset="100%" stop-color="#d9683f" />
          </linearGradient>
        </defs>

        <!-- 地面阴影 -->
        <ellipse cx="100" cy="182" rx="52" ry="8" fill="#e7d6c2" opacity="0.55" class="pet-shadow" />

        <!-- 尾巴 -->
        <path
          d="M150 150 Q182 148 176 120 Q172 104 158 110 Q170 112 168 124 Q166 138 148 138 Z"
          fill="url(#spBody)" stroke="#eab983" stroke-width="2" class="pet-tail"
        />

        <!-- 小脚 -->
        <ellipse cx="76" cy="172" rx="16" ry="9" fill="#f4c48f" stroke="#e6ad72" stroke-width="2" />
        <ellipse cx="124" cy="172" rx="16" ry="9" fill="#f4c48f" stroke="#e6ad72" stroke-width="2" />

        <!-- 身体/大头 -->
        <ellipse cx="100" cy="116" rx="66" ry="62" fill="url(#spBody)" stroke="#eab983" stroke-width="2.5" />
        <ellipse cx="100" cy="138" rx="42" ry="34" fill="url(#spBelly)" opacity="0.85" />

        <!-- 耳朵 -->
        <path d="M52 78 Q46 44 60 40 Q78 40 88 66 Z" fill="url(#spBody)" stroke="#eab983" stroke-width="2.5" class="pet-ear pet-ear--l" />
        <path d="M148 78 Q154 44 140 40 Q122 40 112 66 Z" fill="url(#spBody)" stroke="#eab983" stroke-width="2.5" class="pet-ear pet-ear--r" />
        <path d="M58 70 Q56 52 63 50 Q72 50 78 65 Z" fill="#f6b9a6" class="pet-ear pet-ear--l" />
        <path d="M142 70 Q144 52 137 50 Q128 50 122 65 Z" fill="#f6b9a6" class="pet-ear pet-ear--r" />

        <!-- 呆毛 -->
        <path d="M100 55 Q104 42 112 44 Q106 46 106 55 Z" fill="#eab983" class="pet-ahoge" />

        <!-- 围巾 -->
        <path d="M62 158 Q100 176 138 158 Q136 172 100 180 Q64 172 62 158 Z" fill="url(#spScarf)" />
        <circle cx="100" cy="172" r="6" fill="#ffd27a" stroke="#e8a94e" stroke-width="1.5" />

        <!-- 腮红 -->
        <ellipse cx="66" cy="132" rx="11" ry="7" fill="#f7a98f" opacity="0.55" />
        <ellipse cx="134" cy="132" rx="11" ry="7" fill="#f7a98f" opacity="0.55" />

        <!-- 眼睛：随表情切换 -->
        <g class="pet-eyes" :class="{ 'pet-eyes--shake': isAlert }">
          <!-- 开心 ^ ^ -->
          <template v-if="isHappy">
            <path d="M70 116 Q80 104 90 116" fill="none" stroke="#5b4636" stroke-width="4.5" stroke-linecap="round" />
            <path d="M110 116 Q120 104 130 116" fill="none" stroke="#5b4636" stroke-width="4.5" stroke-linecap="round" />
          </template>
          <!-- 好奇：大圆眼 + 高光 -->
          <template v-else-if="isCurious">
            <ellipse cx="80" cy="116" rx="10" ry="12" fill="#5b4636" />
            <ellipse cx="120" cy="116" rx="10" ry="12" fill="#5b4636" />
            <circle cx="83" cy="112" r="3.4" fill="#fff" />
            <circle cx="123" cy="112" r="3.4" fill="#fff" />
            <circle cx="77" cy="121" r="1.6" fill="#fff" opacity="0.7" />
            <circle cx="117" cy="121" r="1.6" fill="#fff" opacity="0.7" />
          </template>
          <!-- 思考：半闭、歪 -->
          <template v-else-if="isThinking">
            <path d="M68 116 Q80 122 92 114" fill="none" stroke="#5b4636" stroke-width="4.2" stroke-linecap="round" />
            <path d="M108 114 Q120 122 132 116" fill="none" stroke="#5b4636" stroke-width="4.2" stroke-linecap="round" />
          </template>
          <!-- 担心：八字下垂 -->
          <template v-else-if="isWorried">
            <path d="M70 110 Q80 120 90 114" fill="none" stroke="#5b4636" stroke-width="4" stroke-linecap="round" />
            <path d="M110 114 Q120 120 130 110" fill="none" stroke="#5b4636" stroke-width="4" stroke-linecap="round" />
          </template>
          <!-- 慌张：瞪大 + 手忙脚乱眉 -->
          <template v-else-if="isAlert">
            <ellipse cx="80" cy="116" rx="9" ry="11" fill="#fff" stroke="#5b4636" stroke-width="3" />
            <ellipse cx="120" cy="116" rx="9" ry="11" fill="#fff" stroke="#5b4636" stroke-width="3" />
            <circle cx="81" cy="118" r="4.2" fill="#5b4636" />
            <circle cx="121" cy="118" r="4.2" fill="#5b4636" />
            <path d="M66 100 L90 106" stroke="#5b4636" stroke-width="3" stroke-linecap="round" />
            <path d="M134 100 L110 106" stroke="#5b4636" stroke-width="3" stroke-linecap="round" />
          </template>
          <!-- 欢呼：星星眼 -->
          <template v-else-if="isCelebrate">
            <path d="M80 104 L83 112 L91 113 L85 119 L87 127 L80 123 L73 127 L75 119 L69 113 L77 112 Z" fill="#f4a63c" stroke="#e08a2a" stroke-width="1.5" />
            <path d="M120 104 L123 112 L131 113 L125 119 L127 127 L120 123 L113 127 L115 119 L109 113 L117 112 Z" fill="#f4a63c" stroke="#e08a2a" stroke-width="1.5" />
          </template>
        </g>

        <!-- 汗滴（担心/慌张） -->
        <g v-if="isWorried || isAlert" class="pet-sweat">
          <path d="M148 96 Q154 106 150 112 Q142 112 143 104 Q144 100 148 96 Z" fill="#8fd0e8" stroke="#5fb4d6" stroke-width="1.2" />
        </g>

        <!-- 思考气泡 -->
        <g v-if="isThinking" class="pet-think">
          <circle cx="150" cy="74" r="4" fill="#fff" stroke="#e0cdb4" stroke-width="1.5" />
          <circle cx="160" cy="64" r="6" fill="#fff" stroke="#e0cdb4" stroke-width="1.5" />
        </g>

        <!-- 欢呼星星 -->
        <g v-if="isCelebrate" class="pet-sparks">
          <path d="M40 78 L42 84 L48 86 L42 88 L40 94 L38 88 L32 86 L38 84 Z" fill="#f6c453" />
          <path d="M164 84 L165.5 88.5 L170 90 L165.5 91.5 L164 96 L162.5 91.5 L158 90 L162.5 88.5 Z" fill="#f6c453" />
        </g>

        <!-- 嘴巴 -->
        <g class="pet-mouth">
          <template v-if="isCelebrate">
            <path d="M88 138 Q100 154 112 138 Q100 144 88 138 Z" fill="#c9674e" stroke="#a94f38" stroke-width="1.5" />
          </template>
          <template v-else-if="isAlert">
            <ellipse cx="100" cy="142" rx="7" ry="9" fill="#c9674e" />
          </template>
          <template v-else-if="isWorried">
            <path d="M90 142 Q95 138 100 142 Q105 146 110 142" fill="none" stroke="#8a5a45" stroke-width="3" stroke-linecap="round" />
          </template>
          <template v-else-if="isCurious">
            <ellipse cx="100" cy="141" rx="4" ry="5" fill="#c9674e" />
          </template>
          <template v-else-if="isThinking">
            <path d="M92 142 Q100 140 108 142" fill="none" stroke="#8a5a45" stroke-width="3" stroke-linecap="round" />
          </template>
          <template v-else>
            <path d="M90 138 Q100 148 110 138" fill="none" stroke="#8a5a45" stroke-width="3" stroke-linecap="round" />
          </template>
        </g>
      </svg>
      <span class="guide__replay-tip" :class="{ 'is-on': justReplayed }">
        <AppIcon name="refresh" :size="12" /> 点我重播
      </span>
    </button>
  </div>
</template>

<style scoped>
.guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.guide__bubble {
  position: relative;
  width: 100%;
  min-height: 96px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 16px 16px;
  box-shadow: var(--shadow-md);
  animation: bubble-in 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}
.guide__badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--brand);
  background: var(--brand-soft);
  padding: 3px 9px;
  border-radius: 999px;
}
.guide__text {
  margin: 9px 0 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  font-weight: 500;
  min-height: 44px;
}
.guide__cursor {
  color: var(--brand);
  animation: caret 0.7s steps(1) infinite;
  margin-left: 1px;
}
.guide__tail {
  position: absolute;
  bottom: -9px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 16px;
  height: 16px;
  background: var(--panel);
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  border-radius: 0 0 4px 0;
}
.guide--alert .guide__bubble { border-color: #efc9c1; background: linear-gradient(180deg, #fff 0%, #fff6f3 100%); }
.guide--alert .guide__badge { color: var(--danger); background: var(--danger-soft); }
.guide--worried .guide__bubble { border-color: #f0dcb4; background: linear-gradient(180deg, #fff 0%, #fef9ee 100%); }
.guide--worried .guide__badge { color: var(--warn); background: var(--warn-soft); }
.guide--celebrate .guide__bubble { border-color: #bfe0c9; }
.guide--celebrate .guide__badge { color: var(--ok); background: var(--ok-soft); }

.guide__pet {
  position: relative;
  border: none;
  background: transparent;
  padding: 0;
  margin-top: 4px;
  width: 190px;
  max-width: 100%;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.guide__pet:focus-visible { outline: 3px solid var(--brand-soft); border-radius: 20px; }
.pet-svg { width: 100%; height: auto; display: block; overflow: visible; animation: pet-float 3.4s ease-in-out infinite; }
.guide--alert .pet-svg { animation: pet-shake 0.42s ease-in-out 2, pet-float 3.4s ease-in-out 0.9s infinite; }
.guide--celebrate .pet-svg { animation: pet-bounce 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) 1, pet-float 3.4s ease-in-out 0.7s infinite; }
.guide--worried .pet-svg { animation: pet-tilt 2.2s ease-in-out infinite; }

.pet-tail { transform-origin: 150px 145px; animation: tail-wag 2.4s ease-in-out infinite; }
.pet-ear--l { transform-origin: 78px 68px; }
.pet-ear--r { transform-origin: 122px 68px; }
.pet-ear { animation: ear-twitch 5s ease-in-out infinite; }
.pet-ear--r { animation-delay: 0.3s; }
.pet-ahoge { transform-origin: 104px 55px; animation: ahoge 2.8s ease-in-out infinite; }
.pet-eyes { animation: blink 5.2s ease-in-out infinite; transform-origin: 100px 116px; }
.pet-eyes--shake { animation: none; }
.pet-sweat { animation: sweat 1.6s ease-in-out infinite; }
.pet-shadow { animation: shadow-pulse 3.4s ease-in-out infinite; transform-origin: 100px 182px; }
.pet-think { animation: think-pop 2.2s ease-in-out infinite; }
.pet-sparks { animation: spark 1.4s ease-in-out infinite; transform-origin: center; }

.guide__replay-tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
  opacity: 0.75;
  transition: opacity 0.2s, color 0.2s, transform 0.2s;
}
.guide__replay-tip.is-on { color: var(--brand); opacity: 1; transform: scale(1.06); }
.guide__pet:hover .guide__replay-tip { opacity: 1; color: var(--brand); }

@keyframes bubble-in { from { opacity: 0; transform: translateY(10px) scale(0.97); } to { opacity: 1; transform: none; } }
@keyframes caret { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
@keyframes pet-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes pet-bounce { 0% { transform: translateY(0) scale(1); } 40% { transform: translateY(-22px) scale(1.05); } 100% { transform: translateY(0) scale(1); } }
@keyframes pet-shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-6px) rotate(-2deg); } 75% { transform: translateX(6px) rotate(2deg); } }
@keyframes pet-tilt { 0%, 100% { transform: rotate(-3deg); } 50% { transform: rotate(3deg); } }
@keyframes tail-wag { 0%, 100% { transform: rotate(0); } 50% { transform: rotate(9deg); } }
@keyframes ear-twitch { 0%, 92%, 100% { transform: rotate(0); } 96% { transform: rotate(-8deg); } }
@keyframes ahoge { 0%, 100% { transform: rotate(-4deg); } 50% { transform: rotate(6deg); } }
@keyframes blink { 0%, 92%, 100% { transform: scaleY(1); } 96% { transform: scaleY(0.12); } }
@keyframes sweat { 0%, 100% { transform: translateY(0); opacity: 0.9; } 50% { transform: translateY(4px); opacity: 0.5; } }
@keyframes shadow-pulse { 0%, 100% { transform: scaleX(1); opacity: 0.55; } 50% { transform: scaleX(0.9); opacity: 0.4; } }
@keyframes think-pop { 0%, 100% { transform: scale(1); opacity: 0.9; } 50% { transform: scale(1.12); opacity: 1; } }
@keyframes spark { 0%, 100% { transform: scale(0.9) rotate(0); opacity: 0.7; } 50% { transform: scale(1.15) rotate(12deg); opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  .guide__bubble, .pet-svg, .pet-tail, .pet-ear, .pet-ahoge, .pet-eyes,
  .pet-sweat, .pet-shadow, .pet-think, .pet-sparks, .guide__cursor { animation: none !important; }
}
</style>
