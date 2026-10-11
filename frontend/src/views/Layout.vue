<template>
  <el-container style="height:100%">
    <el-header class="topbar" height="60px">
      <!-- 连接状态指示灯（最左上角） -->
      <div class="leds" :title="netTitle">
        <span class="led g" :class="{ on: net === 'ok' }"></span>
        <span class="led y" :class="{ on: net === 'busy' }"></span>
        <span class="led r" :class="{ on: net === 'down' }"></span>
      </div>
      <!-- 子页：返回 + 标题 -->
      <div v-if="!isHome" class="left">
        <el-button class="back-btn" text @click="goHome">
          <span style="font-size:18px;margin-right:4px">←</span> 返回主页
        </el-button>
        <span class="title">{{ pageTitle }}</span>
      </div>
      <!-- 主页：居中标题 -->
      <div v-else class="center-title">{{ sysTitle }}</div>

      <div class="right">
        <div class="acct">
          登录账号： <b>{{ userName }}</b>
          <el-button size="small" text style="color:#fff;margin-left:8px" @click="logout">退出登录</el-button>
        </div>
        <div class="ver">系统版本： V2026-10-03　<el-button size="small" text style="color:#fff" @click="router.push('/system/settings')">设置</el-button></div>
      </div>
    </el-header>

    <el-main class="main">
      <router-view />
    </el-main>

    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="pwdVisible" title="修改密码" width="360px">
      <el-form :model="pwd" label-width="80px">
        <el-form-item label="原密码"><el-input v-model="pwd.old" type="password" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="pwd.new" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible=false">取消</el-button>
        <el-button type="primary" @click="submitPwd">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { logout as clearPerms } from '../perm'

const route = useRoute()
const router = useRouter()

const isHome = computed(() => route.name === 'home')

const ENTITY_TITLES = {
  goods: '货物资料', units: '往来单位', 'goods-categories': '货物分类', categories: '进出类别',
  warehouses: '仓库信息', locations: '库区库位', personnel: '工作人员',
}
const DOC_TITLES = { inbound: '入库单', outbound: '出库单', transfer: '调拨单', check: '盘点单', initial: '期初库存' }
const REPORT_TITLES = { inventory: '库存表', jxc: '进销存', inoutsum: '进出汇总', inout: '进出明细', profit: '利润分析', borrow: '借还统计' }

const pageTitle = computed(() => {
  const p = route.params
  if (route.name === 'master') return ENTITY_TITLES[p.entity] || '基础资料'
  if (route.name === 'doc') return DOC_TITLES[p.type] || '业务单据'
  if (route.name === 'report') return REPORT_TITLES[p.type] || '报表中心'
  return route.meta.title || ''
})

const userName = ref('admin')
/* 系统标题：跟随"系统设置-系统标题"，浏览器标签页同步 */
const sysTitle = ref('仓库管理系统')
watch(sysTitle, v => { document.title = v })
onMounted(async () => {
  try { const me = await api.me(); userName.value = me.name || me.username } catch (e) {}
  try {
    const s = await api.list('system/settings')
    if (s.sys_title) { sysTitle.value = s.sys_title; document.title = s.sys_title }
  } catch (e) {}
})

const pwdVisible = ref(false)
const pwd = ref({ old: '', new: '' })
function goHome() { router.push('/home') }
function logout() {
  api.setToken('')
  clearPerms()
  router.push('/login')
}

// ---------- 连接状态指示灯 ----------
// 绿灯闪烁=与服务器连接正常；黄灯闪烁=正在通讯；红灯闪烁=连接断开
const net = ref('ok') // ok | busy | down
const netTitle = computed(() => ({
  ok: '与服务器连接正常', busy: '正在通讯', down: '与服务器连接断开',
}[net.value]))
let pingTimer = null
let lastPingOk = true

function onNetEvent(e) {
  if (e.detail && e.detail.busy) {
    net.value = 'busy'
  } else {
    net.value = lastPingOk ? 'ok' : 'down'
  }
}
async function ping() {
  try {
    await api.get('auth/me')
    lastPingOk = true
    if (net.value !== 'busy') net.value = 'ok'
  } catch (e) {
    // 401 会跳登录页，这里只处理真正的网络故障
    if (e.message && !/401|无效|过期/.test(e.message)) {
      lastPingOk = false
      net.value = 'down'
    }
  }
}
onMounted(() => {
  window.addEventListener('wms-net', onNetEvent)
  ping()
  pingTimer = setInterval(ping, 5000)
})
onBeforeUnmount(() => {
  window.removeEventListener('wms-net', onNetEvent)
  if (pingTimer) clearInterval(pingTimer)
})
async function submitPwd() {
  try {
    await api.post('auth/change-password', { old_password: pwd.value.old, new_password: pwd.value.new })
    ElMessage.success('密码已修改，请重新登录')
    pwdVisible.value = false
    api.setToken('')
    router.push('/login')
  } catch (e) { ElMessage.error(e.message) }
}
</script>

<style scoped>
.topbar {
  background: linear-gradient(180deg, var(--ku-top1), var(--ku-top2));
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; position: relative;
}
/* 连接状态指示灯 */
.leds { display: flex; align-items: center; gap: 6px; margin-right: 14px; flex-shrink: 0; }
.led { width: 11px; height: 11px; border-radius: 50%; background: rgba(0,0,0,.35); opacity: .3; }
.led.on { opacity: 1; animation: led-blink 1s ease-in-out infinite; }
.led.g.on { background: #3ad07a; box-shadow: 0 0 6px #3ad07a; }
.led.y.on { background: #ffd04b; box-shadow: 0 0 6px #ffd04b; }
.led.r.on { background: #ff5252; box-shadow: 0 0 6px #ff5252; }
@keyframes led-blink { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
.center-title {
  position: absolute; left: 50%; transform: translateX(-50%);
  color: #fff; font-size: 24px; font-weight: 700; letter-spacing: 6px;
  text-shadow: 1px 1px 2px rgba(0,0,0,.3);
}
.left { display: flex; align-items: center; gap: 14px; }
.back-btn { color: #fff; font-size: 14px; }
.back-btn:hover { color: #ffe9a8; }
.title { color: #fff; font-size: 17px; font-weight: 600; letter-spacing: 2px; }
.right { text-align: right; color: #fff; font-size: 12px; line-height: 1.7; }
.acct b { color: #ffe9a8; }
.main { background: #f0f4f5; padding: 14px; overflow: auto; }
</style>
