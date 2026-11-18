<template>
  <div class="login-box" :class="{ 'no-star': !starOn }">
    <!-- 系统设置里自定义的登录背景图（星空画布会覆一层深蓝纱，隐约可见） -->
    <div v-if="bg" class="bg-img" :style="{ backgroundImage: 'url(' + bg + ')' }"></div>
    <canvas ref="starCanvas" v-show="starOn"></canvas>
    <div class="canvaszz" v-show="starOn"></div>

    <div class="input-content">
      <div class="login_tit">
        <div>
          <i class="tit-bg left"></i>
          {{ site }}
          <i class="tit-bg right"></i>
        </div>
      </div>

      <p class="p user_icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="8" r="3.6"/><path d="M4.5 20c1.6-3.6 4.3-5.4 7.5-5.4s5.9 1.8 7.5 5.4"/></svg>
        <input v-model="form.username" type="text" class="login_txtbx" placeholder="账号" autocomplete="off" @keyup.enter="onLogin" />
      </p>

      <p class="p pwd_icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="5" y="10.5" width="14" height="9.5" rx="1.5"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/></svg>
        <input v-model="form.password" :type="showPwd ? 'text' : 'password'" class="login_txtbx" placeholder="密码" autocomplete="off" @keyup.enter="onLogin" />
        <a class="eye" :title="showPwd ? '隐藏密码' : '显示密码'" @click="showPwd = !showPwd">{{ showPwd ? '🙈' : '👁' }}</a>
      </p>

      <div class="opts">
        <el-checkbox v-model="remember">记住密码</el-checkbox>
      </div>

      <div class="signup">
        <button class="gv" :disabled="loading" @click="onLogin">登&thinsp;&thinsp;录</button>
        <button class="gv" @click="clearForm">清&thinsp;&thinsp;空</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { setMe } from '../perm'
import { applyTheme, currentTheme } from '../theme'

const router = useRouter()
const form = ref({ username: '', password: '' })
const remember = ref(true)
const loading = ref(false)
const showPwd = ref(false)
const bg = ref('')
const site = ref('Www.KuGuanYi.Com')
const starOn = ref(true)          // 星空特效开关（系统设置→登录界面）

/* ───────── 星空动画（移植自参考源码：2500 颗绕轨运动星） ───────── */
const starCanvas = ref(null)
let stars = []
let rafId = 0
const hue = 217

function random(min, max) {
  if (arguments.length < 2) { max = min; min = 0 }
  if (min > max) { const hold = max; max = min; min = hold }
  return Math.floor(Math.random() * (max - min + 1)) + min
}
function maxOrbit(x, y) {
  const max = Math.max(x, y)
  const diameter = Math.round(Math.sqrt(max * max + max * max))
  return diameter / 2      // 星星移动范围，值越大范围越小
}

function initStars(w, h) {
  stars = []
  const count = 2500      // 星星数量
  for (let i = 0; i < count; i++) {
    stars.push({
      orbitRadius: random(maxOrbit(w, h)),
      radius: 0,
      orbitX: w / 2,
      orbitY: h / 2,
      timePassed: random(0, count),
      speed: 0,
      alpha: random(2, 10) / 10
    })
  }
  stars.forEach(s => {
    s.radius = random(60, s.orbitRadius) / 18   // 星星大小
    s.speed = random(s.orbitRadius) / 500000    // 星星移动速度
  })
}

function makeStarSprite() {
  // 预渲染单颗星（径向渐变），避免每帧重建渐变
  const c2 = document.createElement('canvas')
  c2.width = 100; c2.height = 100
  const ctx2 = c2.getContext('2d')
  const half = 50
  const g = ctx2.createRadialGradient(half, half, 0, half, half, half)
  g.addColorStop(0.025, '#CCC')
  g.addColorStop(0.1, 'hsl(' + hue + ', 61%, 33%)')
  g.addColorStop(0.25, 'hsl(' + hue + ', 64%, 6%)')
  g.addColorStop(1, 'transparent')
  ctx2.fillStyle = g
  ctx2.beginPath()
  ctx2.arc(half, half, half, 0, Math.PI * 2)
  ctx2.fill()
  return c2
}

let sprite = null
let ctx = null
let w = 0
let h = 0

function animation() {
  ctx.globalCompositeOperation = 'source-over'
  ctx.globalAlpha = 0.5                 // 尾迹（与参考源码一致：每帧半透明覆盖，短尾迹）
  ctx.fillStyle = 'hsla(' + hue + ', 64%, 6%, 1)'
  ctx.fillRect(0, 0, w, h)
  ctx.globalCompositeOperation = 'lighter'
  for (const s of stars) {
    const x = Math.sin(s.timePassed) * s.orbitRadius + s.orbitX
    const y = Math.cos(s.timePassed) * s.orbitRadius + s.orbitY
    const twinkle = random(10)
    if (twinkle === 1 && s.alpha > 0) s.alpha -= 0.05
    else if (twinkle === 2 && s.alpha < 1) s.alpha += 0.05
    ctx.globalAlpha = s.alpha
    ctx.drawImage(sprite, x - s.radius / 2, y - s.radius / 2, s.radius, s.radius)
    s.timePassed += s.speed
  }
  rafId = window.requestAnimationFrame(animation)
}

function onResize() {
  if (!starCanvas.value) return
  w = starCanvas.value.width = window.innerWidth
  h = starCanvas.value.height = window.innerHeight
  initStars(w, h)
}

onMounted(async () => {
  try {
    const saved = JSON.parse(localStorage.getItem('wms_remember') || 'null')
    if (saved) { form.value = saved; remember.value = true }
  } catch (e) {}
  // 登录背景图（系统设置里自定义，免登录读取）
  try {
    const d = await api.raw.get('/system/login-bg')
    bg.value = (d && d.login_bg) || ''
    if (d && d.theme && d.theme !== currentTheme()) applyTheme(d.theme)
    if (d && d.sys_title) document.title = d.sys_title
    if (d && d.company_name) site.value = d.company_name
    if (d && d.login_star === false) starOn.value = false
  } catch (e) {}

  if (!starOn.value) return   // 关闭星空：不启动画布动画，保留静态背景图
  ctx = starCanvas.value.getContext('2d')
  sprite = makeStarSprite()
  onResize()
  window.addEventListener('resize', onResize)
  rafId = window.requestAnimationFrame(animation)
})

onUnmounted(() => {
  window.cancelAnimationFrame(rafId)
  window.removeEventListener('resize', onResize)
})

async function onLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const res = await api.login(form.value.username, form.value.password)
    api.setToken(res.token)
    api._user = res.user
    setMe(res.user)
    if (remember.value) localStorage.setItem('wms_remember', JSON.stringify(form.value))
    else localStorage.removeItem('wms_remember')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function clearForm() {
  form.value.username = ''
  form.value.password = ''
}
</script>

<style scoped>
/* 全屏星空画布 */
.login-box { position: fixed; inset: 0; overflow: hidden; background: var(--ku-login-bg, #000); background-size: cover; background-position: center; font-family: 'Microsoft YaHei', sans-serif; }
.login-box canvas { position: absolute; inset: 0; z-index: 1; }
.bg-img { position: absolute; inset: 0; z-index: 0; background-size: cover; background-position: center; }
/* 关闭星空时：给自定义壁纸加暗化层，保证输入框文字可读 */
.login-box.no-star::after { content: ''; position: absolute; inset: 0; z-index: 2; pointer-events: none; background: rgba(5, 16, 28, .45); }
.canvaszz { /* 暗角纱，让星空更有层次 */
  position: absolute; inset: 0; z-index: 2; pointer-events: none; opacity: .4;
  background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 30%, rgba(0,0,10,.85) 100%);
}

/* 登录框：参考 .input-content —— 居中偏上，透明底 */
.input-content { position: absolute; z-index: 3; padding: 30px; width: 350px; left: 50%; margin-left: -205px; top: 25%; box-sizing: content-box; }

/* 标题：两侧装饰渐变线 */
.login_tit { position: absolute; top: -66px; left: -5px; width: 420px; color: #fff; text-align: center; }
.login_tit > div { position: relative; font-size: 22px; font-weight: bold; letter-spacing: 2px; text-shadow: 0 0 8px rgba(29,126,184,.8); }
.login_tit > p { font-size: 15px; font-family: arial, 'Microsoft YaHei'; margin: 10px 0; color: rgba(255,255,255,.75); letter-spacing: 4px; }
.tit-bg { position: absolute; top: 50%; display: inline-block; width: 90px; height: 1px;
  background: linear-gradient(90deg, transparent, #1d7eb8); box-shadow: 0 0 6px #1d7eb8; }
.tit-bg.left { left: 0; transform: rotate(180deg); }
.tit-bg.right { right: 0; }

/* 输入行：左侧图标 + 透明蓝框输入 */
.input-content .p { margin: 10px 0; height: 44px; position: relative; }
.input-content .p svg {
  position: absolute; top: 12px; left: 13px; width: 20px; height: 20px;
  color: #fff; z-index: 2; pointer-events: none; filter: drop-shadow(0 0 3px rgba(29,126,184,.9));
}
.login_txtbx {
  font-size: 14px; height: 42px; line-height: 42px; padding: 0 9%;
  width: 82%; box-sizing: border-box; text-indent: 1.6em;
  border: 1px solid #1d7eb8; background: rgba(0,0,0,.25); color: #fff;
  outline: none; border-radius: 2px;
}
.login_txtbx::placeholder { color: rgba(255,255,255,.9); }
.login_txtbx:focus, .login_txtbx:hover { box-shadow: 0 0 8px #1d7eb8; border-color: #4aa3e0; transition: all .4s; }

/* 密码可见切换 */
.eye { position: absolute; right: 8px; top: 0; height: 44px; line-height: 44px; width: 30px;
  text-align: center; cursor: pointer; z-index: 2; font-size: 15px; opacity: .8; user-select: none; }
.eye:hover { opacity: 1; }

/* 记住密码 */
.opts { margin: 2px 0 6px 10px; height: 26px; }
.opts :deep(.el-checkbox__label) { color: rgba(255,255,255,.85); font-size: 13px; }
.opts :deep(.el-checkbox__inner) { background: rgba(0,0,0,.25); border-color: #1d7eb8; }
.opts :deep(.el-checkbox__input.is-checked .el-checkbox__inner) { background: #1d7eb8; border-color: #1d7eb8; }

/* 按钮：蓝渐变 + 悬停发光（对应参考 nav_gv.png） */
.signup { margin-top: 30px; text-align: center; }
.signup .gv {
  background: linear-gradient(180deg, #d9ecfa 0%, #a6d2ef 48%, #c7e4f7 100%);
  border: 1px solid #1d7eb8; border-radius: 3px;
  width: 130px; height: 43px; display: inline-block; text-align: center; line-height: 41px;
  cursor: pointer; margin: 8px 16px; padding: 0;
  font: 18px/41px 'Microsoft YaHei'; color: #066197; letter-spacing: 6px; text-indent: 6px;
}
.signup .gv:hover {
  background: linear-gradient(180deg, #bfe0f7 0%, #7cbce8 48%, #a4d4f2 100%);
  color: #1d7eb8;
  box-shadow: 0 0 10px #1d7eb8;
  transition-duration: .5s;
}
.signup .gv:disabled { opacity: .55; cursor: default; box-shadow: none; }
</style>
