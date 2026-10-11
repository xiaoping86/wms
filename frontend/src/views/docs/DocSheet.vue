<template>
  <div class="sheet-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar no-print">
      <button class="tb home" @click="goHome">&lt;主页</button>
      <button class="tb key" @click="doNew">新建</button>
      <button class="tb" @click="insertRow">插行</button>
      <button class="tb" @click="deleteRow">删行</button>
      <button class="tb key" :disabled="loading" @click="save(true)">保存新建</button>
      <button class="tb key" :disabled="loading" @click="save(false)">保存</button>
      <button class="tb" @click="doPrint">预览</button>
      <button class="tb" @click="doPrint">打印</button>
      <button class="tb" @click="quickVisible = true">快捷查询</button>
      <button class="tb" @click="router.push('/docquery')">单据查询</button>
      <button class="tb del" @click="removeDoc">删除</button>
    </div>

    <!-- 单据主体（打印区域） -->
    <div class="sheet print-area">
      <div class="company">{{ companyName }}</div>
      <div class="doc-title">{{ sh.title }}</div>

      <!-- 表头字段（与原版一致：行1 往来单位/类别/单号，行2 备注说明/仓库/时间；调拨单三行） -->
      <div class="head-grid">
        <template v-if="type !== 'transfer'">
          <div class="hrow">
            <template v-if="sh.party">
              <span class="hl">{{ sh.party }}：</span>
              <input class="hi w-party hi-pick" :value="unitName" readonly placeholder="" @click="openHeadPick('unit_id')" />
            </template>
            <template v-if="sh.cat"><span class="hl">{{ sh.cat }}：</span>
              <input class="hi w-cat hi-pick" :value="head.category" readonly placeholder="" @click="openHeadPick('category')" />
            </template>
            <span class="hl">{{ sh.no }}：</span><input class="hi w-no" :value="head.doc_no" readonly />
          </div>
          <div class="hrow">
            <span class="hl">备注说明：</span><input class="hi w-remark" v-model="head.remark" />
            <template v-if="sh.wh"><span class="hl">{{ sh.wh }}：</span>
              <input class="hi w-ware hi-pick" :value="whName(head.warehouse_id)" readonly placeholder="" @click="openHeadPick('warehouse_id')" />
            </template>
            <span class="hl">单据时间：</span><input class="hi w-no" :value="head.time" readonly />
          </div>
        </template>
        <template v-else>
          <div class="hrow">
            <span class="hl">{{ sh.party }}：</span>
            <input class="hi w-party hi-pick" :value="unitName" readonly placeholder="" @click="openHeadPick('unit_id')" />
            <span class="hl">{{ sh.no }}：</span><input class="hi w-no" :value="head.doc_no" readonly />
          </div>
          <div class="hrow">
            <template v-if="sh.cat"><span class="hl">{{ sh.cat }}：</span>
              <input class="hi w-cat hi-pick" :value="head.category" readonly placeholder="" @click="openHeadPick('category')" />
            </template>
            <span class="hl">单据时间：</span><input class="hi w-no" :value="head.time" readonly />
          </div>
          <div class="hrow">
            <span class="hl">备注说明：</span><input class="hi w-remark" v-model="head.remark" />
            <span class="hl">出货仓库：</span>
            <input class="hi w-ware hi-pick" :value="whName(head.from_warehouse_id)" readonly placeholder="" @click="openHeadPick('from_warehouse_id')" />
            <span class="hl">收货仓库：</span>
            <input class="hi w-ware hi-pick" :value="whName(head.to_warehouse_id)" readonly placeholder="" @click="openHeadPick('to_warehouse_id')" />
          </div>
        </template>
      </div>

      <!-- 行项目表格 -->
      <!-- grid key 按单据类型区分：各类型列数不同（入库/出库11、调拨/期初12、盘点13），布局互不干扰 -->
      <table class="grid" :data-grid-key="'doc-' + type">
        <thead>
          <tr>
            <th class="c-idx">序号</th>
            <th v-for="c in colDefs" :key="c.key" :class="{ req: c.req }">
              <el-tooltip v-if="COL_TIPS[c.key]" :content="COL_TIPS[c.key]" placement="bottom-start"
                :show-after="250" popper-class="ku-yellow-tip" effect="light">
                <span class="th-tip">{{ c.label }}</span>
              </el-tooltip>
              <template v-else>{{ c.label }}</template>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i" :class="{ cur: i === activeIdx }" @click="activeIdx = i">
            <td class="c-idx fill">{{ i + 1 }}</td>
            <template v-for="c in colDefs" :key="c.key">
              <!-- 编码：输入 + 回车带出；双击弹货物资料窗口（原版） -->
              <td v-if="c.key === 'code'" :class="{ fill: c.fill }">
                <input class="cell" v-model="r.code" @focus="activeIdx = i"
                  @keydown.enter.prevent="pickGoods(r)" @blur="onCodeBlur(r)" @dblclick="openRowPick(c, i)" />
              </td>
              <td v-else-if="['qty','price','book_qty','actual_qty'].includes(c.key)" :class="{ fill: c.fill }">
                <input class="cell num" type="number" v-model.number="r[c.key]" @focus="activeIdx = i" />
              </td>
              <td v-else-if="c.key === 'amount'" class="num fill">{{ fmtAmt(rowAmount(r)) }}</td>
              <td v-else-if="c.key === 'diff'" class="num fill">{{ fmtAmt((r.actual_qty || 0) - (r.book_qty || 0)) }}</td>
              <td v-else-if="c.key === 'diff_amt'" class="num fill">{{ fmtAmt(rowAmount(r)) }}</td>
              <!-- 库位/仓库：可直接输入名称（回车/失焦匹配），双击弹对应资料窗口（原版） -->
              <td v-else-if="c.ref" :class="{ fill: c.fill }">
                <input class="cell sel" :value="refName(c, r)" placeholder="" @focus="activeIdx = i"
                  @change="onRefInput(c, r, $event)" @keydown.enter.prevent="$event.target.blur()" @dblclick="openRowPick(c, i)" />
              </td>
              <td v-else :class="{ fill: c.fill }"><input class="cell" v-model="r[c.key]" @focus="activeIdx = i" /></td>
            </template>
          </tr>
        </tbody>
      </table>

      <!-- 合计 -->
      <div class="totals">
        <span>{{ sh.totalLabel || '数量合计' }}：<b>{{ fmtAmt(type === 'check' ? totalAmt : totalQty) }}</b></span>
        <span>金额合计：<b>{{ fmtAmt(totalAmt) }}</b></span>
        <span>大写金额：<b>{{ cnAmount(totalAmt) }}</b></span>
      </div>

      <!-- 签字行（点击弹「工作人员」窗口选取，与原版一致） -->
      <div class="sigs">
        <span v-for="(s, i) in sh.sig" :key="s" class="sig">
          {{ s }}：<input class="hi w-sig hi-pick" :value="head.sigs[i]" readonly placeholder="" @click="openSigPick(i)" />
        </span>
      </div>
    </div>

    <!-- 快捷查询（原版 xllList「单据查询」选单窗口：列表+每页20行分页+单位过滤+关键字+删除/选取） -->
    <el-dialog draggable overflow class="win-dlg kj-dlg" v-model="quickVisible" title="单据查询" width="920px"
      append-to-body :close-on-click-modal="false" @open="qQuery">
      <div class="kj-inner">
        <div class="kj-body">
          <div class="scroll kj-scroll">
            <table class="ku-grid" :data-grid-key="'doc-' + type + '.quick'">
              <thead>
                <tr><th v-for="c in qCols" :key="c.key">{{ c.label }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="r in qRows" :key="r.id" :class="{ sel: qSel === r }" @click="qSel = r" @dblclick="qOpen">
                  <td v-for="c in qCols" :key="c.key">{{ r[c.key] }}</td>
                </tr>
                <tr v-if="!qRows.length" class="ku-empty-row"><td :colspan="qCols.length"></td></tr>
              </tbody>
            </table>
          </div>
          <div class="kj-pager">
            <span>每页20行</span>
            <span class="kj-pginfo">第{{ qPageClamped }}页 / 共{{ qPages }}页</span>
            <button class="kj-pgbtn" :disabled="qPage <= 1" @click="qPage = 1">首页</button>
            <button class="kj-pgbtn" :disabled="qPage <= 1" @click="qPage--">上页</button>
            <button class="kj-pgbtn" :disabled="qPage >= qPages" @click="qPage++">下页</button>
            <button class="kj-pgbtn" :disabled="qPage >= qPages" @click="qPage = qPages">尾页</button>
          </div>
        </div>
        <div class="kj-bar">
          <div class="kj-field kj-w240">
            <input class="kj-in" readonly placeholder="所有单位" :value="qUnit" @click="qPickUnit" />
            <button class="kj-sq" title="选择" @click="qPickUnit">▼</button>
            <button class="kj-sq kj-x" title="清空" @click="qUnit = ''; qPage = 1">✕</button>
          </div>
          <div class="kj-field kj-w240">
            <input class="kj-in" v-model="qKw" @keydown.enter="qQuery" />
            <button class="kj-sq" title="查询" @click="qQuery">🔍</button>
            <button class="kj-sq kj-x" title="清空" @click="qKw = ''; qPage = 1">✕</button>
          </div>
          <span class="kj-sp"></span>
          <button class="kj-act kj-del" @click="qDelete">删除</button>
          <button class="kj-act kj-pick" @click="qOpen">选取</button>
        </div>
      </div>
    </el-dialog>

    <!-- 快捷查询单位选择（原版单位列表窗口） -->
    <el-dialog draggable overflow v-model="qUnitOn" title="往来单位" width="1000px" append-to-body class="win-dlg">
      <div style="min-height:420px">
        <MasterView v-if="qUnitOn" entity="units" pick-mode @pick="qOnUnit" />
      </div>
    </el-dialog>

    <!-- 资料选取窗口（原版：点击表头 来往单位/类别/仓库 弹对应资料窗；双击行内编码/库位/仓库同弹） -->
    <el-dialog draggable overflow v-model="pickOn" :title="PICK_TITLES[pickEntity] || '选择数据'" width="1000px" append-to-body class="win-dlg unit-pick-dlg">
      <div class="unit-pick-body">
        <MasterView :entity="pickEntity" pick-mode @pick="onRowPicked" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import MasterView from '../master/MasterView.vue'

const PICK_TITLES = { goods: '货物资料', locations: '库区库位', warehouses: '仓库信息', units: '往来单位', categories: '进出类别', personnel: '工作人员' }

const route = useRoute()
const router = useRouter()
const type = route.params.type
const SHEETS = {
  inbound: { title: '入 库 单', party: '往来单位', cat: '入库类别', no: '入库单号', wh: '收货仓库',
    sig: ['供货人', '经办人', '审核人'], priceOf: 'purchase_price',
    cols: ['code', 'name', 'spec', 'model', 'unit', 'location_id', 'qty', 'price', 'amount', 'remark'] },
  outbound: { title: '出 库 单', party: '往来单位', cat: '出库类别', no: '出库单号', wh: '出货仓库',
    sig: ['领货人', '经办人', '审核人'], priceOf: 'sale_price',
    cols: ['code', 'name', 'spec', 'model', 'unit', 'location_id', 'qty', 'price', 'amount', 'remark'] },
  transfer: { title: '调 拨 单', party: '调拨单位', cat: '调拨类别', no: '调拨单号', wh2: true,
    sig: ['调拨人', '经办人', '审核人'], priceOf: 'purchase_price',
    cols: ['code', 'name', 'spec', 'model', 'unit', 'from_location_id', 'to_location_id', 'qty', 'price', 'amount', 'remark'] },
  check: { title: '盘 点 单', party: '盘点单位', cat: '盘点类别', no: '盘点单号', wh: '盘点仓库',
    sig: ['盘点人', '经办人', '审核人'], priceOf: 'purchase_price',
    cols: ['code', 'name', 'spec', 'model', 'unit', 'location_id', 'book_qty', 'actual_qty', 'diff', 'price', 'diff_amt', 'remark'],
    labels: { book_qty: '账存数', actual_qty: '盘点数', diff: '盈亏数', price: '盘点价', diff_amt: '盈亏额' },
    totalLabel: '盈亏合计' },
  initial: { title: '期 初 库 存', no: '期初单号',
    sig: ['经办人', '审核人'], priceOf: 'purchase_price',
    cols: ['code', 'name', 'spec', 'model', 'unit', 'warehouse_id', 'location_id', 'qty', 'price', 'amount', 'remark'] },
}
const COL_LABELS = {
  code: '编码', name: '名称', spec: '规格', model: '型号', unit: '单位',
  location_id: '库位', warehouse_id: '仓库', from_location_id: '出库位', to_location_id: '收库位',
  qty: '数量', price: '单价', amount: '金额', book_qty: '账存数', actual_qty: '盘点数',
  diff: '盈亏数', diff_amt: '盈亏额', remark: '备注',
}
const REQ_COLS = new Set(['code', 'name', 'location_id', 'from_location_id', 'to_location_id', 'qty', 'price', 'amount', 'book_qty', 'actual_qty'])
// 蓝底列（原版仅 名称/规格/型号/单位 蓝底；编码/库位/数量/单价 白底）
const FILL_COLS = new Set(['name', 'spec', 'model', 'unit'])
// 表头黄色提示（与原版一致）
const COL_TIPS = {
  code: '下方各行，双击弹出选择窗口。\n也可以直接输入货物编码。',
  location_id: '下方各行，双击弹出选择窗口。\n也可以直接输入库位名称。',
  from_location_id: '下方各行，双击弹出选择窗口。\n也可以直接输入库位名称。',
  to_location_id: '下方各行，双击弹出选择窗口。\n也可以直接输入库位名称。',
  price: '下方各行，默认调用货物资料里的参考单价。\n可以修改单价；每张单据的单价都可以不同。',
}

const sh = reactive(SHEETS[type] || SHEETS.inbound)
const colDefs = sh.cols.map(k => ({
  key: k,
  label: (sh.labels && sh.labels[k]) || COL_LABELS[k] || k,
  ref: ['location_id', 'from_location_id', 'to_location_id', 'warehouse_id'].includes(k),
  fill: FILL_COLS.has(k),
}))

const companyName = ref('')
const cfgRows = ref(6)
const head = reactive({ unit_id: null, warehouse_id: null, from_warehouse_id: null, to_warehouse_id: null, category: '', doc_no: '', time: '', remark: '', sigs: [] })
const rows = ref([])
const activeIdx = ref(0)
const currentId = ref(null)
const loading = ref(false)

const goods = ref([])
const units = ref([])
const warehouses = ref([])
const locations = ref([])
const categories = ref([])

const quickVisible = ref(false)

// ---- 快捷查询（原版 xllList(35)「单据查询」选单窗口，1:1） ----
// 列标题按原装入库单窗口：入库单号/供货单位/入库类别/收货仓库/单据时间/供货人/经办人/审核人/备注说明，其余单据类型按原装单据用词对称
const QCOLS = {
  inbound: [
    { key: 'doc_no', label: '入库单号' }, { key: 'unit', label: '供货单位' }, { key: 'category', label: '入库类别' },
    { key: 'wh1', label: '收货仓库' }, { key: 'date', label: '单据时间' }, { key: 'sign_a', label: '供货人' },
    { key: 'operator', label: '经办人' }, { key: 'sign_b', label: '审核人' }, { key: 'remark', label: '备注说明' },
  ],
  outbound: [
    { key: 'doc_no', label: '出库单号' }, { key: 'unit', label: '领货单位' }, { key: 'category', label: '出库类别' },
    { key: 'wh1', label: '出货仓库' }, { key: 'date', label: '单据时间' }, { key: 'sign_a', label: '领货人' },
    { key: 'operator', label: '经办人' }, { key: 'sign_b', label: '审核人' }, { key: 'remark', label: '备注说明' },
  ],
  transfer: [
    { key: 'doc_no', label: '调拨单号' }, { key: 'unit', label: '调拨单位' }, { key: 'category', label: '调拨类别' },
    { key: 'wh1', label: '出货仓库' }, { key: 'wh2', label: '收货仓库' }, { key: 'date', label: '单据时间' },
    { key: 'sign_a', label: '调拨人' }, { key: 'operator', label: '经办人' }, { key: 'sign_b', label: '审核人' },
    { key: 'remark', label: '备注说明' },
  ],
  check: [
    { key: 'doc_no', label: '盘点单号' }, { key: 'category', label: '盘点类别' }, { key: 'wh1', label: '盘点仓库' },
    { key: 'date', label: '单据时间' }, { key: 'sign_a', label: '盘点人' }, { key: 'operator', label: '经办人' },
    { key: 'sign_b', label: '审核人' }, { key: 'remark', label: '备注说明' },
  ],
  initial: [
    { key: 'doc_no', label: '期初单号' }, { key: 'date', label: '单据时间' },
    { key: 'operator', label: '经办人' }, { key: 'sign_b', label: '审核人' }, { key: 'remark', label: '备注说明' },
  ],
}
const qCols = QCOLS[type] || QCOLS.inbound
const qAll = ref([])
const qPage = ref(1)
const qUnit = ref('')
const qKw = ref('')
const qSel = ref(null)
const qUnitOn = ref(false)

const qFiltered = computed(() => {
  const kw = (qKw.value || '').trim().toLowerCase()
  return qAll.value.filter(r => {
    if (qUnit.value && (r.unit || '') !== qUnit.value) return false
    if (!kw) return true
    return qCols.some(c => String(r[c.key] ?? '').toLowerCase().includes(kw))
  })
})
const qPages = computed(() => Math.max(1, Math.ceil(qFiltered.value.length / 20)))
const qPageClamped = computed(() => Math.min(qPage.value, qPages.value))
const qRows = computed(() => qFiltered.value.slice((qPageClamped.value - 1) * 20, qPageClamped.value * 20))
watch([qKw, qUnit], () => { qPage.value = 1; qSel.value = null })

async function qQuery() {
  try {
    qAll.value = await api.list('docs-query', { doc_type: type })
    qSel.value = null
    qPage.value = 1
  } catch (e) { ElMessage.error(e.message) }
}
function qPickUnit() { qUnitOn.value = true }
function qOnUnit(id, name) { qUnit.value = name || ''; qUnitOn.value = false }
function qOpen() {
  if (!qSel.value) return ElMessage.info('没有选定单据！')
  const r = qSel.value
  quickVisible.value = false
  loadDoc({ id: r.id })
}
async function qDelete() {
  if (!qSel.value) return ElMessage.info('没有选定单据！')
  const r = qSel.value
  await ElMessageBox.confirm('确认删除单据 ' + r.doc_no + ' ？删除后库存将同步回退。', '删除单据', { type: 'warning' }).catch(() => Promise.reject())
  try {
    await api.remove(type, r.id)
    ElMessage.success('已删除')
    if (currentId.value === r.id) doNew()
    qQuery()
  } catch (e) { ElMessage.error(e.message) }
}

const totalQty = computed(() => rows.value.reduce((s, r) => s + (Number(r.qty) || 0), 0))
const totalAmt = computed(() => rows.value.reduce((s, r) => s + (rowAmount(r) || 0), 0))

function rowAmount(r) {
  if (type === 'check') return Math.round(((r.actual_qty || 0) - (r.book_qty || 0)) * (r.price || 0) * 100) / 100
  return Math.round((Number(r.qty) || 0) * (Number(r.price) || 0) * 100) / 100
}
function fmtAmt(v) { return (Math.round((v || 0) * 100) / 100).toString() }

// 大写金额
function cnAmount(n) {
  n = Math.round((n || 0) * 100) / 100
  if (!n) return ''
  const digit = '零壹贰叁肆伍陆柒捌玖', unit = ['', '拾', '佰', '仟']
  const big = ['元', '万', '亿', '万亿']
  let neg = n < 0; n = Math.abs(n)
  let integer = Math.floor(n), dec = Math.round((n - integer) * 100)
  let s = ''
  let grp = 0
  while (integer > 0) {
    const part = integer % 10000
    if (part) {
      let ps = ''
      let zero = false
      let p = part
      let ui = 0
      while (p > 0) {
        const d = p % 10
        if (d === 0) { if (!zero && ps) { ps = '零' + ps; zero = true } }
        else { ps = digit[d] + unit[ui] + ps; zero = false }
        p = Math.floor(p / 10); ui++
      }
      s = ps + big[grp] + s
    } else if (s && !s.startsWith('零')) {
      s = '零' + s
    }
    integer = Math.floor(integer / 10000); grp++
  }
  s = s || '零元'
  if (dec === 0) s += '整'
  else {
    const j = Math.floor(dec / 10), f = dec % 10
    s += (j ? digit[j] + '角' : (s ? '零' : ''))
    if (f) s += digit[f] + '分'
    else if (j) s += '整'
  }
  return (neg ? '负' : '') + s
}

function blankRow() {
  const r = { code: '', name: '', spec: '', model: '', unit: '', remark: '', qty: null, price: null, book_qty: null, actual_qty: null, location_id: null, warehouse_id: null, from_location_id: null, to_location_id: null }
  return r
}function ensureRows() {
  while (rows.value.length < cfgRows.value) rows.value.push(blankRow())
}

function nowStr() {
  const d = new Date()
  const p = x => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function refreshNo() {
  try { head.doc_no = (await api.get(type + '/next-no')).doc_no } catch (e) { head.doc_no = '' }
}

function doNew() {
  currentId.value = null
  head.unit_id = null; head.warehouse_id = null; head.from_warehouse_id = null; head.to_warehouse_id = null
  head.category = ''; head.remark = ''; head.time = nowStr()
  head.sigs = sh.sig.map(() => '')
  rows.value = []; ensureRows(); activeIdx.value = 0
  refreshNo()
}

function pickGoods(r) {
  const code = (r.code || '').trim()
  const g = goods.value.find(x => (x.code || '').toLowerCase() === code.toLowerCase())
  if (g) fillFromGoods(r, g)
  else if (code) { ElMessage.info('未找到编码 ' + code + '，可双击编码格弹出选择窗口') }
}
function onCodeBlur(r) { if ((r.code || '').trim()) pickGoods(r) }

function fillFromGoods(r, g) {
  r.code = g.code || ''
  r.name = g.name || ''
  r.spec = g.spec || ''
  r.model = g.model || ''
  r.unit = g.unit || ''
  r.price = type === 'outbound' ? (g.sale_price ?? null) : (g.purchase_price ?? null)
  if (type === 'inbound' || type === 'outbound' || type === 'check') {
    if (g.default_location_id) r.location_id = g.default_location_id
  }
}

function refName(c, r) {
  if (c.key === 'warehouse_id') { const w = warehouses.value.find(x => x.id === r.warehouse_id); return w ? w.name : '' }
  let id = null
  if (c.key === 'location_id') id = r.location_id
  if (c.key === 'from_location_id') id = r.from_location_id
  if (c.key === 'to_location_id') id = r.to_location_id
  const l = locations.value.find(x => x.id === id)
  return l ? l.name : ''
}

// 库位/仓库可直接输入名称（原版）：回车或失焦时按名称匹配；匹配不到则还原并提示
function onRefInput(c, r, ev) {
  const input = ev.target
  const txt = (input.value || '').trim()
  if (!txt) { r[c.key] = null; return }
  const pool = c.key === 'warehouse_id' ? warehouses.value : locations.value
  const hit = pool.find(x => (x.name || '').toLowerCase() === txt.toLowerCase())
  if (hit) { r[c.key] = hit.id }
  else {
    ElMessage.info('未找到「' + txt + '」，可双击弹出窗口选择')
    input.value = refName(c, r)
  }
}

// 表头显示名
const unitName = computed(() => { const u = units.value.find(x => x.id === head.unit_id); return u ? u.name : '' })
function whName(id) { const w = warehouses.value.find(x => x.id === id); return w ? w.name : '' }

// 资料选取窗口：点击表头字段 或 双击行内编码/库位/仓库 弹出（所有单据一致）
const pickOn = ref(false)
const pickEntity = ref('goods')
let pickTarget = null
function openPick(entity, target) {
  pickTarget = target
  pickEntity.value = entity
  pickOn.value = true
}
function openHeadPick(key) {
  const entity = key === 'unit_id' ? 'units' : (key === 'category' ? 'categories' : 'warehouses')
  openPick(entity, { head: true, key })
}
// 签字行（供货人/经办人/审核人等）：点击弹「工作人员」窗口选取
function openSigPick(i) { openPick('personnel', { sig: i }) }
function openRowPick(c, i) {
  activeIdx.value = i
  const entity = c.key === 'code' ? 'goods' : (c.key === 'warehouse_id' ? 'warehouses' : 'locations')
  openPick(entity, { idx: i, key: c.key })
}
function onRowPicked(id, name) {
  if (!pickTarget) return
  if (pickTarget.sig != null) {
    head.sigs[pickTarget.sig] = name || ''
  } else if (pickTarget.head) {
    if (pickTarget.key === 'category') head.category = name || (categories.value.find(x => x.id === id)?.name ?? '')
    else head[pickTarget.key] = id
  } else {
    const r = rows.value[pickTarget.idx]
    if (r) {
      if (pickTarget.key === 'code') {
        const g = goods.value.find(x => x.id === id)
        if (g) fillFromGoods(r, g)
      } else {
        r[pickTarget.key] = id
        if (pickTarget.key === 'warehouse_id') r.location_id = null
      }
    }
  }
  pickOn.value = false
}
function onWhChange() { /* 库位下拉随仓库过滤 */ }

function insertRow() {
  rows.value.splice(Math.max(activeIdx.value, 0), 0, blankRow())
}
function deleteRow() {
  if (rows.value.length <= 1) { rows.value = [blankRow()]; return }
  rows.value.splice(activeIdx.value, 1)
  activeIdx.value = Math.min(activeIdx.value, rows.value.length - 1)
}

function filled() { return rows.value.filter(r => (r.code || '').trim() && Number(r.qty || r.actual_qty) !== 0) }

async function save(andNew) {
  const fs = filled()
  if (!fs.length) return ElMessage.warning('请先录入货物（编码 + 数量）')
  if (type === 'transfer' && (!head.from_warehouse_id || !head.to_warehouse_id)) return ElMessage.warning('请选择调出/调入仓库')
  if (['inbound', 'outbound', 'check'].includes(type) && !head.warehouse_id) return ElMessage.warning('请选择仓库')
  const items = fs.map(r => {
    const g = goods.value.find(x => (x.code || '').toLowerCase() === (r.code || '').toLowerCase())
    const base = { goods_id: g ? g.id : null, qty: Number(r.qty) || 0, price: Number(r.price) || 0 }
    if (type === 'transfer') { base.from_location_id = r.from_location_id; base.to_location_id = r.to_location_id }
    else if (type === 'initial') { base.warehouse_id = r.warehouse_id; base.location_id = r.location_id }
    else { base.location_id = r.location_id }
    if (type === 'check') { base.book_qty = Number(r.book_qty) || 0; base.actual_qty = Number(r.actual_qty) || 0 }
    return base
  })
  if (items.some(x => !x.goods_id)) return ElMessage.warning('存在无法匹配的货物编码，请检查')
  const payload = {
    date: (head.time || nowStr()).slice(0, 10),
    remark: head.remark || null,
    category: head.category || null,
    operator: head.sigs[1] || null,
    sign_a: head.sigs[0] || null,
    sign_b: head.sigs[2] || null,
    items,
  }
  if (type === 'inbound' || type === 'outbound' || type === 'check') payload.warehouse_id = head.warehouse_id
  if (type === 'inbound' || type === 'outbound') payload.unit_id = head.unit_id
  if (type === 'transfer') { payload.from_warehouse_id = head.from_warehouse_id; payload.to_warehouse_id = head.to_warehouse_id }
  loading.value = true
  try {
    const res = await api.create(type, payload)
    currentId.value = res.id
    head.doc_no = res.doc_no
    ElMessage.success('单据已保存：' + res.doc_no)
    if (andNew) doNew()
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function loadDoc({ id }) {
  try {
    const res = await api.get(type + '/' + id)
    const h = res.header
    currentId.value = id
    head.doc_no = h.doc_no
    head.time = (h.created_at || h.date || '') .slice(0, 16).replace('T', ' ')
    head.unit_id = h.unit_id ?? null
    head.warehouse_id = h.warehouse_id ?? null
    head.from_warehouse_id = h.from_warehouse_id ?? null
    head.to_warehouse_id = h.to_warehouse_id ?? null
    head.category = h.category || ''
    head.remark = h.remark || ''
    head.sigs = [h.sign_a || '', h.operator || '', h.sign_b || '']
    rows.value = res.items.map(it => {
      const g = goods.value.find(x => x.id === it.goods_id) || {}
      const r = blankRow()
      r.code = g.code || ''; r.name = g.name || ''; r.spec = g.spec || ''; r.model = g.model || ''; r.unit = g.unit || ''
      r.location_id = it.location_id ?? null; r.warehouse_id = it.warehouse_id ?? null
      r.from_location_id = it.from_location_id ?? null; r.to_location_id = it.to_location_id ?? null
      r.qty = it.qty ?? 0; r.price = it.price ?? 0; r.book_qty = it.book_qty ?? 0; r.actual_qty = it.actual_qty ?? 0
      r.remark = it.remark || ''
      return r
    })
    ensureRows()
    ElMessage.success('已载入单据 ' + h.doc_no + '（查看模式，保存将生成新单）')
  } catch (e) { ElMessage.error(e.message) }
}

async function removeDoc() {
  if (!currentId.value) return ElMessage.info('当前是新单据，请先通过【单据查询】载入要删除的单据')
  await ElMessageBox.confirm('确认删除单据 ' + head.doc_no + ' ？删除后库存将同步回退。', '删除单据', { type: 'warning' }).catch(() => Promise.reject())
  try {
    await api.remove(type, currentId.value)
    ElMessage.success('已删除')
    doNew()
  } catch (e) { ElMessage.error(e.message) }
}

function doPrint() { window.print() }
function goHome() { router.push('/home') }

onMounted(async () => {
  try {
    const cfg = await api.get(type + '/config')
    cfgRows.value = cfg.rows || 6
    if (cfg.title) sh.title = cfg.title
  } catch (e) {}
  try {
    const st = await api.get('system/settings')
    companyName.value = st.company_name || ''
  } catch (e) {}
  try {
    const [g, u, w, l, c] = await Promise.all([
      api.list('goods'), api.list('units'), api.list('warehouses'), api.list('locations'), api.list('categories'),
    ])
    goods.value = g; units.value = u; warehouses.value = w; locations.value = l; categories.value = c
  } catch (e) { ElMessage.error('基础资料加载失败：' + e.message) }
  doNew()
  // 从"单据查询"页点"打开单据"跳回：按 URL 参数自动载入（查看模式）
  if (route.query.docid) loadDoc({ id: route.query.docid })
})

// 同一单据页内通过 URL 参数切换打开不同单据
watch(() => route.query.docid, (id) => { if (id) loadDoc({ id }) })
</script>

<style scoped>
.sheet-page { background: var(--ku-page); min-height: calc(100vh - 60px); padding: 0 0 24px; font-family: "Microsoft YaHei", sans-serif; }

/* 工具栏 */
.toolbar {
  display: flex; align-items: center; gap: 6px; padding: 5px 10px;
  background: var(--ku-accent); border-bottom: 1px solid #1f6474;
}
.tb {
  border: 1px solid var(--ku-accent); background: var(--ku-accent); color: #fff; font-size: 14px;
  padding: 5px 16px; cursor: pointer; border-radius: 2px; white-space: nowrap;
}
.tb:hover { background: var(--ku-accent-dark); }
.tb.key { color: #ffe36e; }
.tb.home { background: #3aa25e; border-color: #2f8a4f; color: #fff; }
.tb.home:hover { background: #338d52; }
.tb.del { background: #4b97a8; }
.tb:disabled { opacity: .5; cursor: not-allowed; }

/* 单据主体 */
.sheet { background: var(--ku-panel); margin: 0 auto; max-width: 980px; padding: 14px 22px 16px; min-height: calc(100vh - 62px); }
.company { text-align: center; color: #1f6fc0; font-size: 22px; font-weight: 700; letter-spacing: 2px; }
.doc-title { text-align: center; color: #223; font-size: 24px; font-weight: 700; letter-spacing: 14px; margin: 6px 0 14px; }

/* 表头字段 */
.head-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.hrow { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 0; }
.hl { font-size: 14px; color: var(--ku-text); margin-left: 14px; white-space: nowrap; }
.hrow .hl:first-child { margin-left: 0; }
.hi {
  height: 28px; border: 1px solid var(--ku-border-soft); background: #fff; border-radius: 2px;
  padding: 0 6px; font-size: 14px; color: #222; outline: none;
}
input.hi { font-family: inherit; }
.hi:focus { border-color: var(--ku-accent); }
.w-party { width: 240px; } .w-ware { width: 150px; } .w-cat { width: 150px; }
.w-no { width: 190px; background: #f2fafd; color: #555; }
.w-remark { width: 300px; } .w-sig { width: 120px; }
.hi-pick { cursor: pointer; }
.hi-pick:hover { border-color: var(--ku-accent); }
:deep(.el-select .el-select__wrapper) { min-height: 28px; height: 28px; padding: 0 6px; font-size: 14px; }

/* 表格 */
.grid { width: 100%; border-collapse: collapse; background: #fff; }
.grid th, .grid td { border: 1px solid var(--ku-border); padding: 0; height: 34px; }
.grid th {
  background: var(--ku-panel); color: var(--ku-text); font-size: 14px; font-weight: 600; position: relative; text-align: center;
}
.grid th.req::after {
  content: ''; position: absolute; top: 0; right: 0;
  border-top: 7px solid #e0342b; border-left: 7px solid transparent;
}
.grid tr.cur td { background: #ffe9a8 !important; }
.grid td { background: #fff; }
.grid td.fill { background: var(--ku-head); }
.c-idx { width: 44px; text-align: center; color: var(--ku-text); font-size: 13px; }
.c-idx.fill { background: var(--ku-head); }
.cell { width: 100%; height: 32px; border: none; background: transparent; padding: 0 6px; font-size: 14px; outline: none; }
.cell:focus { background: #fff; box-shadow: inset 0 0 0 2px #2fa25e; }
.cell.num { text-align: right; }
.cell.sel { cursor: text; }
.th-tip { cursor: help; }
td.num { text-align: right; padding-right: 6px; font-size: 14px; }

/* 行内资料选取窗口（双击编码/库位弹出，复用 MasterView 选取窗） */
.unit-pick-body { height: 62vh; display: flex; }
.unit-pick-body :deep(.ku-win) { flex: 1; min-width: 0; }
.unit-pick-dlg :deep(.ku-win-main) { max-height: none; height: calc(100% - 54px); }

/* 快捷查询「单据查询」选单窗口（原版 xllList 弹窗：浅蓝窗体+列表+分页+底部按钮条+状态栏） */
.kj-dlg :deep(.el-dialog__body) { padding: 0; background: #cde9f5; overflow: hidden; }
.kj-inner { padding: 10px 12px 0; }
.kj-body { border: 1px solid #7fb8cf; background: #fff; }
.kj-scroll { height: 46vh; overflow: auto; }
.kj-pager { display: flex; align-items: center; gap: 16px; border-top: 1px solid #7fb8cf; padding: 6px 10px; font-size: 13px; color: var(--ku-text); }
.kj-pginfo { margin-left: auto; color: var(--ku-text); }
.kj-pgbtn { border: none; background: transparent; color: #1f6474; font-size: 13px; cursor: pointer; padding: 2px 4px; }
.kj-pgbtn:hover:not(:disabled) { text-decoration: underline; }
.kj-pgbtn:disabled { color: #9ab4c0; cursor: default; }
.kj-bar { display: flex; align-items: center; gap: 10px; padding: 10px 2px; }
.kj-field { display: flex; align-items: stretch; gap: 3px; }
.kj-w240 { width: 240px; }
.kj-in { flex: 1; min-width: 0; height: 26px; border: 1px solid #9fc6d8; border-radius: 3px; background: #fff; padding: 0 6px; font-size: 13px; color: var(--ku-text); outline: none; }
.kj-in::placeholder { color: #9ab4c0; }
.kj-sq { width: 28px; border: 1px solid #9fc6d8; border-radius: 3px; background: #e8f5fb; color: #1f6474; cursor: pointer; font-size: 12px; padding: 0; }
.kj-sq:hover { background: #d5edf8; }
.kj-x { color: #c0392b; }
.kj-sp { flex: 1; }
.kj-act { border: 1px solid #2478a8; border-radius: 3px; color: #fff; font-size: 13px; padding: 5px 24px; cursor: pointer; }
.kj-del { background: #1f6474; }
.kj-pick { background: #2f9bd4; }
.kj-act:hover { filter: brightness(1.08); }
.kj-grid tr.sel td, .kj-scroll tr.sel td { background: #ffe9a8 !important; }
.kj-scroll tbody tr { cursor: pointer; }

/* 合计与签字 */
.totals { display: flex; gap: 60px; padding: 10px 4px 6px; font-size: 15px; color: var(--ku-text); }
.totals b { color: #d0342b; margin-left: 4px; }
.sigs { display: flex; gap: 34px; padding: 8px 4px; font-size: 14px; color: var(--ku-text); flex-wrap: wrap; }
.sig { display: flex; align-items: center; gap: 4px; white-space: nowrap; }

@media print {
  body * { visibility: hidden; }
  .print-area, .print-area * { visibility: visible; }
  .print-area {
    position: absolute; left: 0; top: 0; width: 100%; min-height: auto;
    box-shadow: none; max-width: none;
  }
}
</style>
