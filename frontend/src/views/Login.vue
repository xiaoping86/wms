<template>
  <div class="login-page" :style="bgStyle">
    <div v-if="bg" class="login-scrim"></div>
    <div class="login-window">
      <div class="win-titlebar">
        <span>账号登录</span>
        <span class="win-x">×</span>
      </div>
      <div class="win-head">
        <div class="site">{{ site }}</div>
      </div>
      <div class="win-body">
        <el-form :model="form" @submit.prevent="onLogin" label-position="left">
          <div class="form-row">
            <label>账号：</label>
            <el-input v-model="form.username" size="large" style="flex:1" @keyup.enter="onLogin" />
          </div>
          <div class="form-row">
            <label>密码：</label>
            <el-input v-model="form.password" type="password" size="large" style="flex:1" show-password @keyup.enter="onLogin" />
          </div>
          <div class="form-row opts">
            <el-checkbox v-model="remember">记住密码</el-checkbox>
            <span class="motto">不颓废，不消极</span>
          </div>
          <button class="login-btn" :disabled="loading" @click="onLogin">登 录</button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { setMe } from '../perm'
import { applyTheme, currentTheme } from '../theme'

const router = useRouter()
const form = ref({ username: '', password: '' })
const remember = ref(true)
const loading = ref(false)
const bg = ref('')
const site = ref('Www.KuGuanYi.Com')
const bgStyle = computed(() => bg.value ? { backgroundImage: `url(${bg.value})` } : {})

onMounted(async () => {
  try {
    const saved = JSON.parse(localStorage.getItem('wms_remember') || 'null')
    if (saved) { form.value = saved; remember.value = true }
  } catch (e) {}
  // 登录背景图（系统设置里自定义，免登录读取）
  try {
    const d = await api.raw.get('/system/login-bg') // 拦截器已返回 data 本体
    bg.value = (d && d.login_bg) || ''
    if (d && d.theme && d.theme !== currentTheme()) applyTheme(d.theme)
    if (d && d.sys_title) document.title = d.sys_title
    // 底部网址跟随系统设置里的公司名称（留空则显示默认）
    if (d && d.company_name) site.value = d.company_name
  } catch (e) {}
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
</script>

<style scoped>
.login-page {
  height: 100vh; display: flex; align-items: center; justify-content: center; position: relative;
  background: var(--ku-login-bg); background-size: cover; background-position: center;
  font-family: "Microsoft YaHei", sans-serif;
}
.login-scrim { position: absolute; inset: 0; background: rgba(15,35,55,.18); backdrop-filter: saturate(120%); }
.login-window { position: relative; z-index: 1; }
.login-window {
  width: 520px; background: var(--ku-panel-soft); border: 1px solid var(--ku-border);
  box-shadow: 0 6px 24px rgba(0,0,0,.25);
}
.win-titlebar {
  height: 34px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 12px; background: var(--ku-panel-2); border-bottom: 1px solid var(--ku-border-soft);
  font-size: 14px; color: var(--ku-text-soft);
}
.win-x { font-size: 20px; color: #666; line-height: 1; }
.win-head {
  text-align: center; padding: 34px 0 24px;
  background: linear-gradient(180deg, var(--ku-sel), #a8d8e8);
}
.brand { font-size: 26px; font-weight: 700; color: var(--ku-accent); letter-spacing: 1px; }
.site { margin-top: 8px; font-size: 15px; color: var(--ku-muted); letter-spacing: 2px; }
.win-body { padding: 36px 56px 28px; }
.form-row { display: flex; align-items: center; margin-bottom: 20px; }
.form-row label { width: 64px; font-size: 15px; color: #333; }
.form-row :deep(.el-input__wrapper) { background: #fff; }
.opts { justify-content: space-between; margin: 4px 0 22px; }
.opts :deep(.el-checkbox__label) { color: #333; font-size: 14px; }
.motto { color: var(--ku-muted); font-size: 14px; letter-spacing: 1px; }
.login-btn {
  width: 100%; height: 44px; border: none; cursor: pointer;
  background: linear-gradient(180deg, var(--ku-accent), var(--ku-accent-dark));
  color: #fff; font-size: 17px; letter-spacing: 10px; border-radius: 3px;
}
.login-btn:hover { background: linear-gradient(180deg, var(--ku-accent), var(--ku-accent-dark)); }
.login-btn:disabled { opacity: .6; cursor: default; }
.win-foot {
  padding: 8px 12px; font-size: 12px; color: var(--ku-muted);
  background: var(--ku-panel-2); border-top: 1px solid var(--ku-border-soft);
}
</style>
