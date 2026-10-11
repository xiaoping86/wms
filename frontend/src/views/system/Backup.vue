<template>
  <div class="ku-win" style="padding: 14px 18px 10px; min-width: 560px">
    <div class="fld">
      <span class="lb">{{ mode === 'backup' ? '位置：' : '文件：' }}</span>
      <template v-if="mode === 'backup'">
        <span class="ku-input tip-text" style="flex:1">点 📁 或“备份”即保存到本机电脑</span>
        <span class="icon-btn" title="保存到本机电脑（另存为）" @click="onFolderIcon">📁</span>
      </template>
      <input v-else type="file" accept=".db" class="ku-input" style="flex:1; padding-top:3px" @change="onFile" />
    </div>

    <div class="ku-check-grid2">
      <label v-for="it in ITEMS" :key="it"><input type="checkbox" v-model="checks[it]" /> {{ it }}</label>
    </div>

    <div class="btns">
      <button class="ku-btn" @click="all(true)">全 选</button>
      <button class="ku-btn" @click="all(false)">全 清</button>
      <button v-if="mode === 'backup'" class="ku-btn warn" :disabled="saving" @click="backup">备 份</button>
      <button v-if="mode === 'restore'" class="ku-btn warn" :disabled="!file || saving" @click="restore">还 原</button>
    </div>
    <div class="tip-line">
      {{ mode === 'backup'
        ? (canPick
          ? '点“📁”或“备份”都会把备份文件保存到本机电脑'
          : '当前是普通 http 地址，浏览器规定网页不能弹出系统“另存为”窗口（只有 localhost 或 https 允许），因此点备份会直接下载到浏览器下载文件夹。想每次弹出另存为自己选文件夹：可在浏览器设置开启“下载前询问每个文件的保存位置”，或将本系统地址加入浏览器“视为安全来源”白名单（chrome://flags/#unsafely-treat-insecure-origin-as-secure），或改用 localhost / https 地址访问。')
        : '还原将用所选备份文件覆盖当前数据，请谨慎操作' }}
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const props = defineProps({ mode: { type: String, default: 'backup' } })

const ITEMS = ['货物资料', '期初库存', '仓库信息', '库区库位', '往来单位', '工作人员', '进出类别', '单据账目', '系统设置', '账号权限']
const checks = reactive(Object.fromEntries(ITEMS.map(i => [i, true])))
const file = ref(null)
const saving = ref(false)
// 浏览器是否允许网页弹出系统“另存为”窗口（仅 localhost / https），setup 时求值一次
const canPick = !!(window.isSecureContext && window.showSaveFilePicker)

function all(v) { for (const k of ITEMS) checks[k] = v }
function onFile(e) { file.value = e.target.files[0] || null }

function stampName() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  return `wms_backup_${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}.db`
}
// 取备份文件内容（Blob）
async function fetchBackupBlob() {
  const t = api.getToken()
  const resp = await api.raw.get('/backup', { responseType: 'blob', headers: { Authorization: 'Bearer ' + t } })
  return resp instanceof Blob ? resp : new Blob([resp]) // 拦截器已返回 data 本体
}
// 兜底：浏览器禁用系统“另存为”时，直接触发下载保存到本机
function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
// 把备份保存到本机：优先弹系统“另存为”（先弹窗再取数据，避免 await 消耗浏览器瞬态用户激活），不可用则直接下载
async function saveLocal() {
  if (canPick) {
    let handle = null
    try {
      handle = await window.showSaveFilePicker({
        suggestedName: stampName(),
        types: [{ description: '数据库备份文件', accept: { 'application/octet-stream': ['.db'] } }]
      })
    } catch (e) {
      if (e && e.name === 'AbortError') return // 用户取消选择
      // 其它异常不报错，转为直接下载兜底
    }
    if (handle) {
      try {
        const blob = await fetchBackupBlob()
        const w = await handle.createWritable()
        await w.write(blob)
        await w.close()
        ElMessage.success('备份成功：已保存到您选择的电脑文件夹')
        return
      } catch (e) {
        // 取数据或写入失败也不报错，转为直接下载兜底
      }
    }
  }
  const blob = await fetchBackupBlob()
  downloadBlob(blob, stampName())
  ElMessage.success('备份文件已开始下载，请在本机保存')
}
async function onFolderIcon() {
  saving.value = true
  try { await saveLocal() } catch (e) { ElMessage.error(e.message || '备份失败') }
  saving.value = false
}
async function backup() {
  saving.value = true
  try { await saveLocal() } catch (e) { ElMessage.error(e.message || '备份失败') }
  saving.value = false
}
async function restore() {
  await ElMessageBox.confirm('恢复将覆盖当前所有数据，确定继续？', '危险操作', { type: 'warning' }).catch(() => Promise.reject())
  const fd = new FormData(); fd.append('file', file.value)
  const t = api.getToken()
  try {
    await api.raw.post('/restore', fd, { headers: { Authorization: 'Bearer ' + t } })
    ElMessage.success('恢复成功，请重新登录'); api.setToken(''); location.hash = '#/login'
  } catch (e) { ElMessage.error(e.message) }
}
</script>

<style scoped>
.fld { display: flex; align-items: center; margin-bottom: 12px; gap: 6px; }
.lb { font-size: 14px; color: var(--ku-text); white-space: nowrap; }
.icon-btn { cursor: pointer; font-size: 16px; padding: 2px 4px; border: 1px solid var(--ku-border); background: var(--ku-head); }
.tip-text { height: 24px; line-height: 22px; color: var(--ku-muted); background: var(--ku-panel-soft); cursor: default; }
.btns { display: flex; justify-content: center; gap: 18px; margin-top: 10px; }
.ku-btn.warn { color: #ffe36e; }
.tip-line {
  text-align: center; font-size: 13px; line-height: 1.6;
  color: var(--ku-muted); padding: 6px 4px 0;
}
</style>
