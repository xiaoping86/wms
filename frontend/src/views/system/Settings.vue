<template>
  <div class="settings-window" :class="{ embedded }">
    <div v-if="!embedded" class="win-titlebar"><span>系统设置</span><span class="win-x" @click="goHome">×</span></div>
    <div class="win-body">
      <!-- 左侧选项卡 -->
      <div class="tabs">
        <div v-for="t in tabs" :key="t.key" class="tab" :class="{ active: tab === t.key }" @click="tab = t.key">{{ t.label }}</div>
      </div>
      <!-- 右侧面板 -->
      <div class="panel">
        <!-- 全局配置 -->
        <template v-if="tab === 'global'">
          <div class="panel-title">全局配置</div>
          <div class="field-row"><label>公司名称：</label><el-input v-model="s.company_name" style="flex:1" /></div>
          <div class="field-row"><label>系统标题：</label><el-input v-model="s.sys_title" style="flex:1" /></div>

          <div class="group">
            <div class="group-title">界面主题</div>
            <div class="theme-row">
              <div v-for="t in THEMES" :key="t.key" class="theme-card" :class="{ sel: theme === t.key }" @click="pickTheme(t.key)">
                <span class="sw" :style="{ background: t.sw }"></span>
                <span class="lb">{{ t.label }}</span>
              </div>
              <span class="theme-tip">选择后立即生效，保存后所有窗口、表格均随主题变化</span>
            </div>
          </div>

          <div class="group">
            <div class="group-title">登录界面</div>
            <div class="bg-row">
              <div class="bg-preview" :style="bgStyle">
                <span v-if="!s.login_bg" class="bg-none">当前：默认背景</span>
              </div>
              <div class="bg-ops">
                <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="bgVisible = true">🖼 登录背景图管理</el-button>
                <div class="bg-tip">可自定义登录窗口背后的壁纸，图片从本机文件夹选择；设置后点窗口底部【保存】生效</div>
              </div>
            </div>
          </div>

          <div class="group">
            <div class="group-title">成本核算</div>
            <el-radio-group v-model="s.cost_method">
              <el-radio value="moving_avg">使用移动加权平均法</el-radio>
              <el-radio value="doc_price">单据价即进出成本</el-radio>
            </el-radio-group>
            <div class="check-grid">
              <el-checkbox v-model="s.cost_tail_adjust">成本尾差自动化调整</el-checkbox>
              <el-checkbox v-model="s.force_recalc_avg">进出库强制重算均价</el-checkbox>
              <el-checkbox v-model="s.est_cost_by_doc_price">无成本用单据价暂估</el-checkbox>
              <el-checkbox v-model="s.wh_cost">分仓库核算存货成本</el-checkbox>
            </div>
            <div class="field-row inline">
              <label>均价小数位：</label>
              <el-select v-model="s.avg_digits" style="width:90px"><el-option v-for="n in [0,1,2,3,4,5,6]" :key="n" :label="n" :value="n" /></el-select>
              <label style="margin-left:30px">成本小数位：</label>
              <el-select v-model="s.cost_digits" style="width:90px"><el-option v-for="n in [0,1,2,3,4]" :key="n" :label="n" :value="n" /></el-select>
            </div>
          </div>

          <div class="group">
            <div class="group-title">单据与期初</div>
            <div class="warn">特别提醒：此处小数位数不能由大改小，请谨慎选择</div>
            <div class="field-row inline">
              <label>数量小数位：</label>
              <el-select v-model="s.qty_digits" style="width:90px"><el-option v-for="n in [0,1,2,3]" :key="n" :label="n" :value="n" /></el-select>
              <label style="margin-left:30px">单价小数位：</label>
              <el-select v-model="s.price_digits" style="width:90px"><el-option v-for="n in [0,1,2,3,4,5,6]" :key="n" :label="n" :value="n" /></el-select>
            </div>
            <div class="field-row inline">
              <label>金额小数位：</label>
              <el-select v-model="s.amount_digits" style="width:90px"><el-option v-for="n in [0,1,2,3,4]" :key="n" :label="n" :value="n" /></el-select>
            </div>
            <div class="check-grid">
              <el-checkbox v-model="s.qty_pad_zero">数量小数不足时补零</el-checkbox>
              <el-checkbox v-model="s.price_pad_zero">价格小数不足时补零</el-checkbox>
            </div>
          </div>

          <div class="group">
            <div class="group-title">运行参数</div>
            <div class="check-grid">
              <el-checkbox v-model="s.auto_save">操作后自动保存文件</el-checkbox>
              <el-checkbox v-model="s.doc_no_immutable">查询单据不可改单号</el-checkbox>
              <el-checkbox v-model="s.no_negative_stock">出库后不允许负库存</el-checkbox>
            </div>
          </div>
        </template>

        <!-- 货物字段 -->
        <template v-else-if="tab === 'goodsfields'">
          <div class="panel-title">货物字段</div>
          <div v-for="f in s.goods_fields" :key="f.key" class="group">
            <div class="group-title">{{ f.label }}</div>
            <div class="check-grid">
              <el-checkbox v-model="f.enabled">确认启用此字段</el-checkbox>
              <span class="inline-label">自定义标题：<el-input v-model="f.custom_label" :disabled="!f.enabled" style="width:180px" placeholder="" /></span>
            </div>
            <div class="check-grid" :class="{ dim: !f.enabled }">
              <el-checkbox v-model="f.in_list" :disabled="!f.enabled">窗口列表中显示</el-checkbox>
              <el-checkbox v-model="f.required" :disabled="!f.enabled">填写资料时不能为空值</el-checkbox>
            </div>
            <div class="check-grid" :class="{ dim: !f.enabled }">
              <el-checkbox v-model="f.in_doc" :disabled="!f.enabled">单据与报表显示</el-checkbox>
            </div>
          </div>
        </template>

        <!-- 库位管理 -->
        <template v-else-if="tab === 'location'">
          <div class="panel-title">启用设置</div>
          <el-radio-group v-model="locMode">
            <el-radio :value="'off'">不启用库位管理功能</el-radio>
            <el-radio :value="'on'">启用智能化库位管理</el-radio>
          </el-radio-group>
          <div class="check-grid" style="margin-top:14px" :class="{ dim: locMode === 'off' }">
            <el-checkbox v-model="s.loc_required_in_goods" :disabled="locMode === 'off'">货物中必填默认库位</el-checkbox>
            <el-checkbox v-model="s.loc_required_in_doc" :disabled="locMode === 'off'">单据中必填进出库位</el-checkbox>
          </div>
          <div class="loc-order" :class="{ dim: locMode === 'off' }">
            <div class="loc-order-head">
              <span>库位优先顺序：</span>
              <span class="arrows">
                <el-button size="small" :disabled="locMode === 'off'" @click="movePriority(-1)">↑</el-button>
                <el-button size="small" :disabled="locMode === 'off'" @click="movePriority(1)">↓</el-button>
              </span>
            </div>
            <div v-for="(p, i) in s.loc_priority" :key="p" class="loc-item" :class="{ sel: i === priIdx }" @click="priIdx = i">{{ p }}</div>
          </div>
        </template>

        <!-- 四类单据 -->
        <template v-else>
          <div class="panel-title">基础配置</div>
          <div class="field-row"><label>单据标题：</label><el-input v-model="docCfg.title" style="flex:1" /></div>
          <div class="field-row">
            <label>默认行数：</label>
            <el-select v-model="docCfg.rows" style="width:100px"><el-option v-for="n in [4,5,6,7,8,9,10,12,15,20]" :key="n" :label="n" :value="n" /></el-select>
            <label style="margin-left:30px">单号前缀：</label>
            <el-input v-model="docCfg.prefix" style="width:120px" />
          </div>
          <div class="field-row">
            <label>单号规则：</label>
            <el-select v-model="docCfg.rule" style="width:340px">
              <el-option label="[前缀][年]-[月][日]-[四位序号]" value="[前缀][年]-[月][日]-[四位序号]" />
              <el-option label="[前缀][年][月][日][四位序号]" value="[前缀][年][月][日][四位序号]" />
              <el-option label="[前缀][年][四位序号]" value="[前缀][年][四位序号]" />
            </el-select>
          </div>
          <div v-if="tab === 'outbound'" class="check-grid" style="margin-top:8px">
            <el-checkbox v-model="docCfg.show_unit_addr">显示往来单位的送货地址、联系人、联系电话</el-checkbox>
          </div>
        </template>
      </div>
    </div>
    <div class="win-foot">
      <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" :loading="saving" @click="save">保 存</el-button>
    </div>

    <!-- 登录背景图管理 -->
    <el-dialog draggable overflow class="win-dlg bg-dlg" v-model="bgVisible" title="登录背景图管理" width="620px" append-to-body>
      <div class="bg-dlg-body">
        <div class="bg-view" :style="bgStyle">
          <span v-if="!s.login_bg" class="bg-none">未设置自定义背景（显示默认背景）</span>
        </div>
        <div class="bg-btns">
          <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="pickLocalImage">从本机文件夹选择图片</el-button>
          <el-button @click="clearBg">恢复默认背景</el-button>
        </div>
        <input ref="fileRef" type="file" accept="image/*" style="display:none" @change="onBgFile" />
        <div class="bg-tip2">
          支持 JPG / PNG 等常见图片。系统会按屏幕比例自动压缩到合适尺寸，替换后的壁纸对所有使用该系统的电脑生效。
        </div>
      </div>
      <template #footer>
        <el-button @click="bgVisible = false">关闭</el-button>
        <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="saveBg">确定并保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { THEMES, applyTheme, currentTheme } from '../../theme'

const props = defineProps({ embedded: Boolean })
const emit = defineEmits(['close'])
const router = useRouter()
const tabs = [
  { key: 'global', label: '全局配置' },
  { key: 'goodsfields', label: '货物字段' },
  { key: 'location', label: '库位管理' },
  { key: 'inbound', label: '入库单' },
  { key: 'outbound', label: '出库单' },
  { key: 'transfer', label: '调拨单' },
  { key: 'check', label: '盘点单' },
]
const tab = ref('global')
const theme = ref(currentTheme())
function pickTheme(t) {
  theme.value = t
  applyTheme(t) // 立即生效
}
const s = reactive({
  company_name: '', sys_title: '', theme: 'blue', cost_method: 'moving_avg',
  login_bg: '',
  cost_tail_adjust: true, force_recalc_avg: false, est_cost_by_doc_price: true, wh_cost: false,
  avg_digits: 6, cost_digits: 2, qty_digits: 2, price_digits: 2, amount_digits: 2,
  qty_pad_zero: false, price_pad_zero: false, auto_save: true, doc_no_immutable: true,
  goods_fields: [], loc_priority: [],
  loc_required_in_goods: true, loc_required_in_doc: true,
  docs: {},
})
const saving = ref(false)
const priIdx = ref(0)
const locMode = computed({
  get: () => (s.location_mgmt ? 'on' : 'off'),
  set: (v) => { s.location_mgmt = v === 'on' },
})

const docCfg = computed(() => s.docs[tab.value] || (s.docs[tab.value] = {}))

function movePriority(dir) {
  const arr = s.loc_priority
  const i = priIdx.value, j = i + dir
  if (j < 0 || j >= arr.length) return
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
  priIdx.value = j
}

onMounted(async () => {
  try {
    const d = await api.get('system/settings')
    Object.assign(s, d)
    // 服务器设置里有主题时以服务器为准
    if (d.theme && d.theme !== theme.value) { theme.value = d.theme; applyTheme(d.theme) }
    s.goods_fields = d.goods_fields || []
    s.docs = d.docs || {}
  } catch (e) { ElMessage.error(e.message) }
})

async function save() {
  saving.value = true
  s.theme = theme.value
  try {
    await api.raw.put('/system/settings', s)
    if (s.sys_title) document.title = s.sys_title  // 浏览器标签页同步
    ElMessage.success('设置已保存')
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}

// ---------- 登录背景图管理 ----------
const bgVisible = ref(false)
const fileRef = ref(null)
const bgStyle = computed(() => s.login_bg
  ? { backgroundImage: `url(${s.login_bg})` }
  : {})
function pickLocalImage() { fileRef.value && fileRef.value.click() }
function clearBg() {
  s.login_bg = ''
  ElMessage.success('已恢复默认背景，点【保存】后生效')
}
function onBgFile(e) {
  const f = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!f) return
  if (!/^image\//.test(f.type)) return ElMessage.warning('请选择图片文件')
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      // 压缩到最大宽度 1600，保证设置不至于过大
      const MAX = 1600
      const scale = Math.min(1, MAX / img.width)
      const cv = document.createElement('canvas')
      cv.width = Math.round(img.width * scale)
      cv.height = Math.round(img.height * scale)
      cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height)
      s.login_bg = cv.toDataURL('image/jpeg', 0.82)
      ElMessage.success('背景已选择，点【确定并保存】生效')
    }
    img.onerror = () => ElMessage.error('图片读取失败')
    img.src = reader.result
  }
  reader.onerror = () => ElMessage.error('文件读取失败')
  reader.readAsDataURL(f)
}
async function saveBg() {
  await save()
  bgVisible.value = false
}

function goHome() {
  if (props.embedded) emit('close')
  else router.push('/home')
}
</script>

<style scoped>
.settings-window {
  max-width: 960px; margin: 10px auto; background: var(--ku-panel); border: 1px solid var(--ku-border);
  box-shadow: 0 4px 18px rgba(0,0,0,.18); display: flex; flex-direction: column; min-height: calc(100vh - 100px);
  font-family: "Microsoft YaHei", sans-serif;
}
.settings-window.embedded { max-width: none; margin: 0; min-height: auto; box-shadow: none; border: none; background: transparent; }
.settings-window.embedded .panel { max-height: 56vh; }
.settings-window.embedded .win-body { padding: 8px; }
.settings-window.embedded .win-foot { background: transparent; border-top: none; padding: 8px 4px 0; }
.win-titlebar {
  height: 32px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 12px; background: var(--ku-panel-2); border-bottom: 1px solid var(--ku-border-soft); font-size: 14px; color: var(--ku-text-soft);
}
.win-x { font-size: 20px; color: #666; cursor: pointer; line-height: 1; }
.win-body { flex: 1; display: flex; padding: 12px; gap: 0; }
.tabs { width: 110px; flex-shrink: 0; }
.tab {
  padding: 9px 12px; font-size: 14px; color: var(--ku-text-soft); cursor: pointer;
  border-left: 4px solid transparent;
}
.tab:hover { background: var(--ku-hover); }
.tab.active { background: var(--ku-accent); color: #fff; border-left-color: #ffd04b; }
.panel { flex: 1; background: var(--ku-panel-soft); border: 1px solid var(--ku-border-soft); padding: 16px 20px; overflow: auto; max-height: calc(100vh - 200px); }
.panel-title { font-size: 15px; color: var(--ku-text-soft); font-weight: 600; margin-bottom: 12px; }
.field-row { display: flex; align-items: center; margin: 10px 0; }
.field-row label { font-size: 14px; color: #333; white-space: nowrap; }
.group { border-top: 1px dashed var(--ku-border-soft); margin-top: 18px; padding-top: 12px; }
.group-title { color: var(--ku-text-soft); font-weight: 600; font-size: 14px; margin-bottom: 8px; }
.warn { color: #b26a00; font-size: 13px; margin-bottom: 8px; }
.check-grid { display: grid; grid-template-columns: 1fr 1fr; row-gap: 8px; margin: 8px 0; }
.inline-label { display: flex; align-items: center; gap: 6px; font-size: 14px; }
.dim { opacity: .45; }
.theme-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.theme-card {
  display: flex; align-items: center; gap: 8px; padding: 8px 16px; cursor: pointer;
  border: 2px solid var(--ku-border-soft); background: #fff; border-radius: 6px; transition: all .15s;
}
.theme-card:hover { border-color: var(--ku-accent); }
.theme-card.sel { border-color: var(--ku-accent); box-shadow: 0 0 0 2px rgba(46,139,160,.15); }
.theme-card .sw { width: 34px; height: 22px; border-radius: 4px; border: 1px solid #ccc; display: inline-block; }
.theme-card .lb { font-size: 14px; color: #333; }
.theme-tip { font-size: 12px; color: var(--ku-muted); margin-left: 6px; }
/* 登录背景图管理 */
.bg-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.bg-preview {
  width: 240px; height: 120px; border: 1px solid var(--ku-border-soft); border-radius: 6px;
  background-color: var(--ku-login-bg); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center; box-shadow: inset 0 0 0 1px rgba(255,255,255,.4);
}
.bg-none { font-size: 12px; color: var(--ku-muted); background: rgba(255,255,255,.65); padding: 2px 8px; border-radius: 10px; }
.bg-ops { display: flex; flex-direction: column; gap: 6px; }
.bg-tip { font-size: 12px; color: var(--ku-muted); max-width: 320px; }
.bg-dlg-body { display: flex; flex-direction: column; gap: 12px; align-items: center; }
.bg-view {
  width: 100%; height: 240px; border: 1px solid var(--ku-border-soft); border-radius: 8px;
  background-color: var(--ku-login-bg); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
}
.bg-btns { display: flex; gap: 12px; }
.bg-tip2 { font-size: 12px; color: var(--ku-muted); text-align: center; line-height: 1.7; }
.loc-order { margin-top: 20px; max-width: 340px; background: #fff; border: 1px solid var(--ku-border-soft); }
.loc-order-head { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; font-size: 14px; color: #333; }
.arrows { display: flex; gap: 4px; }
.loc-item { padding: 8px 12px; border-top: 1px solid var(--ku-border-soft); font-size: 14px; color: #333; cursor: pointer; }
.loc-item.sel { background: var(--ku-accent); color: #fff; }
.win-foot {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: var(--ku-panel-2); border-top: 1px solid var(--ku-border-soft);
  font-size: 12px; color: var(--ku-muted);
}
</style>
