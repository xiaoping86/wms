<template>
  <div class="home">
    <div v-for="g in visibleGroups" :key="g.name" class="group-row">
      <div class="group-tag">{{ g.name }}</div>
      <div class="group-body">
        <div v-for="it in g.items" :key="it.label" class="nav-item" @click="click(it)">
          <div class="nav-icon">{{ it.icon }}</div>
          <div class="nav-label">{{ it.label }}</div>
        </div>
        <div v-if="!g.items.length" style="width:100%"></div>
      </div>
    </div>

    <!-- 通用功能弹窗（资料 / 系统：与原版一致，主页面之上弹窗口） -->
    <el-dialog draggable overflow v-model="dlg.on" :title="dlg.title" :width="dlg.w" destroy-on-close append-to-body :class="['win-dlg', dlg.kind === 'master' ? 'master-dlg' : null, dlg.kind === 'bom' ? 'bom-dlg' : null]">
      <component :is="dlg.comp" v-bind="dlg.props" @close="dlg.on = false" />
    </el-dialog>

    <!-- 初始化（原版复选样式） -->
    <el-dialog draggable overflow v-model="resetVisible" title="系统初始化" width="560px" append-to-body class="win-dlg dlg-fit">
      <div class="ku-check-grid" style="padding:4px 10px">
        <label v-for="it in RESET_ITEMS" :key="it"><input type="checkbox" v-model="resetChecks[it]" /> {{ it }}</label>
      </div>
      <div class="btns">
        <button class="ku-btn" @click="resetAll(true)">全 选</button>
        <button class="ku-btn" @click="resetAll(false)">全 清</button>
        <button class="ku-btn warn" @click="doReset">初 始 化</button>
      </div>
      <div style="text-align:center;font-size:13px;color:#b26a00;padding:6px 0 0">⚠ 初始化将清空所选数据且不可恢复，请先【备份】</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, markRaw, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { loadMe, hasPerm } from '../perm'
import MasterView from './master/MasterView.vue'
import Settings from './system/Settings.vue'
import Profile from './system/Profile.vue'
import Users from './system/Users.vue'
import Backup from './system/Backup.vue'
import Help from './system/Help.vue'
import Logs from './system/Logs.vue'
import Bom from './bom/Bom.vue'

const router = useRouter()

const COMP = {
  master: MasterView, settings: Settings, profile: Profile, users: Users, backup: Backup,
  help: Help, logs: Logs, bom: Bom,
}
const dlg = reactive({ on: false, title: '', w: '920px', comp: null, props: {}, kind: '' })
function openDlg(kind, title, props = {}, w = '920px') {
  Object.assign(dlg, { on: true, title, w, props, comp: markRaw(COMP[kind]), kind })
}

const groups = [
  { name: '单据', items: [
    { icon: '📥', label: '入库单', to: '/doc/inbound', perm: 'inbound' },
    { icon: '📤', label: '出库单', to: '/doc/outbound', perm: 'outbound' },
    { icon: '🔁', label: '调拨单', to: '/doc/transfer', perm: 'transfer' },
    { icon: '✅', label: '盘点单', to: '/doc/check', perm: 'check' },
    { icon: '🔍', label: '单据查询', to: '/docquery', perm: 'docquery' },
  ]},
  { name: '报表', items: [
    { icon: '📦', label: '库存表', to: '/report/inventory', perm: 'reports' },
    { icon: '📊', label: '进销存', to: '/report/jxc', perm: 'reports' },
    { icon: '⇅', label: '进出汇总', to: '/report/inoutsum', perm: 'reports' },
    { icon: '📋', label: '进出明细', to: '/report/inout', perm: 'reports' },
    { icon: '🥧', label: '利润分析', to: '/report/profit', perm: 'reports' },
    { icon: '🧾', label: '借还统计', to: '/report/borrow', perm: 'reports' },
    { icon: '🧮', label: '产品查询', to: '/productquery', perm: 'reports' },
  ]},
  { name: '资料', items: [
    { icon: '📜', label: '货物资料', perm: 'goods', dlg: ['master', '货物资料', { entity: 'goods' }, '1080px'] },
    { icon: '🏠', label: '期初库存', perm: 'initial', dlg: ['master', '期初库存', { entity: 'initial' }, '1080px'] },
    { icon: '🏭', label: '仓库信息', perm: 'warehouses', dlg: ['master', '仓库信息', { entity: 'warehouses' }, '700px'] },
    { icon: '🏢', label: '库区库位', perm: 'locations', needLoc: true, dlg: ['master', '库区库位', { entity: 'locations' }, '820px'] },
    { icon: '🔀', label: '进出类别', perm: 'categories', dlg: ['master', '进出类别', { entity: 'categories' }, '900px'] },
    { icon: '🤝', label: '往来单位', perm: 'units', dlg: ['master', '往来单位', { entity: 'units' }, '820px'] },
    { icon: '🙂', label: '工作人员', perm: 'personnel', dlg: ['master', '工作人员', { entity: 'personnel' }, '760px'] },
    { icon: '🧩', label: 'BOM', perm: 'goods', dlg: ['bom', 'BOM 管理', {}, 'min(78vh, 92vw)'] },
  ]},
  { name: '系统', items: [
    { icon: '⚙', label: '系统设置', perm: 'settings', dlg: ['settings', '系统设置', { embedded: true }, '900px'] },
    { icon: '🔧', label: '个人设置', dlg: ['profile', '个人设置', { embedded: true }, '560px'] },
    { icon: '👥', label: '账号权限', perm: 'users', dlg: ['users', '账号权限', { embedded: true }, '760px'] },
    { icon: '💾', label: '备份', perm: 'data', dlg: ['backup', '数据备份', { mode: 'backup' }, '600px'] },
    { icon: '♻', label: '还原', perm: 'data', dlg: ['backup', '数据还原', { mode: 'restore' }, '600px'] },
    { icon: '🗑', label: '初始化', perm: 'data', act: 'reset' },
    { icon: '📄', label: '操作日志', perm: 'users', dlg: ['logs', '操作日志（服务器记录）', {}, '860px'] },
    { icon: '📖', label: '使用说明', dlg: ['help', '使用说明', {}, '880px'] },
  ]},
]

// 按当前账号的操作权限过滤宫格（管理员拥有全部）；未启用库位管理时隐藏「库区库位」
const locMgmt = ref(true)
const visibleGroups = computed(() =>
  groups
    .map(g => ({ ...g, items: g.items.filter(it => (!it.perm || hasPerm(it.perm)) && !(it.needLoc && !locMgmt.value)) }))
    .filter(g => g.items.length)
)
onMounted(() => {
  loadMe()
  // 读取系统设置：未启用库位管理时主页隐藏「库区库位」入口
  api.get('system/settings').then(s => { locMgmt.value = !!s.location_mgmt }).catch(() => {})
})

function click(it) {
  if (it.to) router.push(it.to)
  else if (it.dlg) openDlg(...it.dlg)
  else if (it.act === 'reset') resetVisible.value = true
}

/* ---------- 初始化 ---------- */
const RESET_ITEMS = [
  '单据账目', '期初库存', '查询报表',
  '货物资料', '货物分类', '计量单位',
  '仓库信息', '仓库分类', '库区库位',
  '库位分类', '进出类别', '类别分类',
  '往来单位', '单位分类', '工作人员',
  '人员分类', '人员职务', 'BOM 资料', '系统设置',
  '用户账号', '操作权限',
]
const MASTER_ITEMS = ['货物资料', '货物分类', '计量单位', '仓库信息', '仓库分类', '库区库位', '库位分类', '进出类别', '类别分类', '往来单位', '单位分类', '工作人员', '人员分类', '人员职务', 'BOM 资料', '系统设置', '用户账号', '操作权限']
const resetVisible = ref(false)
const resetChecks = reactive(Object.fromEntries(RESET_ITEMS.map(i => [i, false])))
function resetAll(v) { for (const k of RESET_ITEMS) resetChecks[k] = v }

async function doReset() {
  const anyMaster = MASTER_ITEMS.some(k => resetChecks[k])
  const anyBiz = ['单据账目', '期初库存', '查询报表'].some(k => resetChecks[k])
  if (!anyMaster && !anyBiz) return ElMessage.warning('请先勾选要初始化的项目')
  const mode = anyMaster ? 'all' : 'business'
  await ElMessageBox.confirm(
    mode === 'all' ? '已勾选基础资料类项目，将清空【全部数据】且不可恢复！确定继续？' : '将清空所选业务数据且不可恢复，确定继续？',
    '危险操作', { type: 'warning' }
  ).catch(() => Promise.reject())
  try {
    await api.post('system/reset?mode=' + mode)
    ElMessage.success('初始化完成')
    resetVisible.value = false
  } catch (e) { ElMessage.error(e.message) }
}
</script>

<style scoped>
.home { padding: 18px; background: var(--ku-bg); min-height: calc(100vh - 60px); }
.group-row { display: flex; margin-bottom: 14px; border: 1px solid var(--ku-border-soft); background: #fff; }
.group-tag {
  flex: 0 0 76px; display: flex; align-items: center; justify-content: center;
  background: var(--ku-tag); color: #fff; font-size: 17px; letter-spacing: 4px; font-weight: 600;
}
.group-body { flex: 1; display: flex; flex-wrap: wrap; padding: 10px 8px; row-gap: 10px; }
.nav-item {
  width: 104px; text-align: center; padding: 10px 4px; margin: 0 4px; cursor: pointer;
  border: 1px solid transparent; border-radius: 6px; transition: all .15s;
}
.nav-item:hover { background: #e8f6f8; border-color: var(--ku-border-lite); }
.nav-icon {
  width: 58px; height: 58px; margin: 0 auto 6px; display: flex; align-items: center; justify-content: center;
  font-size: 36px; border-radius: 8px; background: linear-gradient(145deg, #fdfdfd, #dde5e8);
  box-shadow: 1px 2px 4px rgba(0,0,0,.18);
}
.nav-label { font-size: 14px; color: #333; }
.btns { display: flex; justify-content: center; gap: 18px; margin-top: 8px; }
.ku-btn.warn { color: #ffe36e; }
</style>

<style>
/* 弹窗内边距与高度（全局样式） */
.win-dlg .el-dialog__body { padding: 10px 16px 14px; max-height: 74vh; overflow: auto; }
/* 资料栏窗口：默认即为原版大窗口（内容区撑满，可手动调小） */
.master-dlg .el-dialog__body { height: calc(70vh - 54px); max-height: none; overflow: hidden; display: flex; }
.master-dlg .el-dialog__body > * { flex: 1; min-height: 0; }
.master-dlg .ku-win { height: 100%; }
.master-dlg .ku-win-main { max-height: none; height: 100%; }
/* BOM 管理窗口：初始为正方形（宽=高），列表区撑满 */
.bom-dlg .el-dialog__body { height: calc(min(78vh, 92vw) - 54px); max-height: none; overflow: hidden; display: flex; }
.bom-dlg .bom-page { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.bom-dlg .bom-card.grow { flex: 1; min-height: 0; overflow: auto; margin-bottom: 0; }
</style>
