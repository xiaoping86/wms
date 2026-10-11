<template>
  <div class="ku-page">
    <!-- 工具栏（原版：<主页 查询 清空 预览 打印） -->
    <div class="ku-toolbar no-print">
      <button class="ku-tb home" @click="$router.push('/home')">&lt;主页</button>
      <button class="ku-tb key" @click="filterVisible = true">查询</button>
      <button class="ku-tb" @click="rows = []">清空</button>
      <button class="ku-tb" @click="doPrint">预览</button>
      <button class="ku-tb" @click="doPrint">打印</button>
      <span style="flex:1"></span>
      <span v-if="condTip" class="ftip">{{ condTip }}</span>
    </div>

    <!-- 打印/显示区域 -->
    <div class="print-area">
      <div class="ku-titlebar">{{ cfg.title }}</div>
      <div class="ku-grid-wrap">
        <div class="scroll" style="max-height: calc(100vh - 190px); overflow: auto">
          <table class="ku-grid" :data-grid-key="'rep.' + type">
            <thead>
              <tr v-if="visibleGroups.length">
                <th v-for="c in visibleFlat" :key="c.key" rowspan="2" :class="{ req: c.first }">{{ c.label }}</th>
                <th v-for="g in visibleGroups" :key="g.label" :colspan="g.cols.length" class="grp">{{ g.label }}</th>
                <th v-for="c in (cfg.flat2 || [])" :key="'f2-' + c.key" rowspan="2">{{ c.label }}</th>
              </tr>
              <tr v-if="visibleGroups.length">
                <template v-for="g in visibleGroups" :key="g.label">
                  <th v-for="c in g.cols" :key="c.key" class="sub">{{ c.label }}</th>
                </template>
              </tr>
              <tr v-else>
                <th v-for="c in allCols" :key="c.key">{{ c.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in displayRows" :key="i" :class="{ total: r.__total }">
                <template v-for="c in allCols" :key="c.key">
                  <td :class="{ num: c.num && !r.__total }">{{ cell(r, c) }}</td>
                </template>
              </tr>
              <tr v-if="!displayRows.length" class="ku-empty-row"><td :colspan="allCols.length"></td></tr>
            </tbody>
          </table>
        </div>
        <div class="ku-foot">
          <span>共 {{ rows.length }} 行</span>
          <span>每页 {{ pageSize }} 行</span>
        </div>
      </div>
    </div>

    <!-- 查询条件窗口（原版：各报表独立条件 + 重置/确定） -->
    <el-dialog draggable overflow class="win-dlg q-dlg" v-model="filterVisible" :title="cfg.dlgTitle" width="820px" append-to-body>
      <div class="qgrid">
        <template v-for="(row, ri) in dlgRows" :key="ri">
          <div v-for="fd in row" :key="fd.k" class="qf">
            <span class="ql">{{ fd.label }}：</span>
            <!-- 下拉选择（分类/单据类型） -->
            <el-select v-if="['cat','docty'].includes(fd.t)"
              v-model="f[fd.k]" filterable clearable placeholder="" class="qctl">
              <el-option v-for="o in options(fd.t)" :key="String(o.v)" :label="o.l" :value="o.v" />
            </el-select>
            <!-- 货物/仓库/往来单位/进出类别/人员：点击弹对应资料窗口（原版） -->
            <div v-else-if="PICK_T.has(fd.t)" class="qctl qpick" @click="openPick(fd)">
              <input class="qp-in" :value="pickLabel(fd)" readonly placeholder="" />
              <a class="qp-btn dn" title="选择">▼</a><a class="qp-btn" title="清空" @click.stop="clearPick(fd)">✕</a>
            </div>
            <!-- 开始/结束时间：点击弹「日期时间」窗口（原版） -->
            <div v-else-if="fd.t === 'date'" class="qctl qpick" @click="openDate(fd)">
              <input class="qp-in" :value="f[fd.k]" readonly placeholder="" />
              <a class="qp-btn dn" title="选择">▼</a><a class="qp-btn" title="清空" @click.stop="f[fd.k] = null">✕</a>
            </div>
            <!-- 开关 -->
            <el-switch v-else-if="fd.t === 'sw'" v-model="f[fd.k]" class="qsw" />
            <!-- 文本 -->
            <el-input v-else v-model="f[fd.k]" clearable class="qctl" />
          </div>
        </template>
      </div>
      <div class="qbtns">
        <button class="ku-tb" @click="resetFilter">重置</button>
        <button class="ku-tb key" @click="doQuery">确定</button>
      </div>
    </el-dialog>

    <!-- 资料选取窗口（原版：点 货物/仓库/往来单位/进出类别/人员 弹对应资料窗） -->
    <el-dialog draggable overflow v-model="pickOn" :title="PICK_TITLES[pickEntity] || '选择数据'" width="1000px" append-to-body class="win-dlg unit-pick-dlg">
      <div class="unit-pick-body">
        <MasterView :entity="pickEntity" pick-mode @pick="onPicked" />
      </div>
    </el-dialog>

    <!-- 日期时间窗口（原版：年月切换 + 日历 + 时/分 + 此时/确定） -->
    <el-dialog draggable overflow v-model="dateOn" title="日期时间" width="380px" append-to-body class="win-dlg date-dlg">
      <div class="dt-head">
        <a class="dt-arr" @click="dt.y--">▲</a>
        <select class="dt-sel" v-model.number="dt.y"><option v-for="y in dtYears" :key="y" :value="y">{{ y }}</option></select>
        <a class="dt-arr" @click="dt.y++">▼</a>
        <a class="dt-arr" @click="addMonth(-1)">▲</a>
        <select class="dt-sel" v-model.number="dt.m"><option v-for="(nm, i) in MONTHS" :key="i" :value="i">{{ nm }}</option></select>
        <a class="dt-arr" @click="addMonth(1)">▼</a>
      </div>
      <div class="dt-week">
        <span v-for="w in ['周一','周二','周三','周四','周五','周六','周日']" :key="w">{{ w }}</span>
      </div>
      <div class="dt-grid">
        <a v-for="(c, i) in dayCells" :key="i" class="dt-day"
          :class="{ dim: !c.cur, wk: c.cur && i % 7 >= 5, sel: c.cur && c.d === dt.d }"
          @click="c.cur && (dt.d = c.d)">{{ c.d }}</a>
      </div>
      <div class="dt-time">
        <select class="dt-sel sm" v-model.number="dt.h"><option v-for="h in 24" :key="h" :value="h - 1">{{ h - 1 }}</option></select><span>时</span>
        <select class="dt-sel sm" v-model.number="dt.min"><option v-for="m in 60" :key="m" :value="m - 1">{{ m - 1 }}</option></select><span>分</span>
        <button class="ku-tb" @click="setNow">此时</button>
        <button class="ku-tb key" @click="dateOk">确定</button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import MasterView from '../master/MasterView.vue'

const REPORTS = {
  inventory: {
    title: '库存表', dlgTitle: '库存查询', endpoint: 'inventory',
    sumCols: ['qty', 'amt'],
    flat: [
      { key: 'code', label: '编码', first: true }, { key: 'name', label: '名称' },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' }, { key: 'unit', label: '单位' },
      { key: 'min_stock', label: '最低库存', num: true }, { key: 'max_stock', label: '最高库存', num: true },
      { key: 'alarm', label: '库存报警' }, { key: 'warehouse_name', label: '仓库' },
      { key: 'qty', label: '数量', num: true }, { key: 'amt', label: '成本', num: true },
      { key: 'remark', label: '货物备注' },
    ],
    groups: [],
  },
  jxc: {
    title: '进销存', dlgTitle: '进销存', endpoint: 'reports/jxc',
    sumCols: ['begin_qty', 'begin_cost', 'in_qty', 'in_cost', 'out_qty', 'out_cost', 'end_qty', 'end_cost'],
    flat: [
      { key: 'code', label: '编码', first: true }, { key: 'name', label: '名称' },
      { key: 'spec', label: '规格', opt: 'simple' }, { key: 'model', label: '型号', opt: 'simple' },
      { key: 'unit', label: '单位', opt: 'simple' }, { key: 'warehouse', label: '仓库', opt: 'simple' },
    ],
    groups: [
      { label: '期初', cols: [{ key: 'begin_qty', label: '数量', num: true }, { key: 'begin_cost', label: '成本', num: true }] },
      { label: '进货', cols: [{ key: 'in_qty', label: '数量', num: true }, { key: 'in_cost', label: '成本', num: true }] },
      { label: '出货', cols: [{ key: 'out_qty', label: '数量', num: true }, { key: 'out_cost', label: '成本', num: true }] },
      { label: '结存', cols: [{ key: 'end_qty', label: '数量', num: true }, { key: 'end_cost', label: '成本', num: true }] },
    ],
  },
  inoutsum: {
    title: '进出汇总', dlgTitle: '进出汇总', endpoint: 'reports/inout-summary',
    sumCols: ['in_qty', 'in_amt', 'in_cost', 'out_qty', 'out_amt', 'out_cost'],
    flat: [
      { key: 'code', label: '编码', first: true }, { key: 'name', label: '名称' },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' }, { key: 'unit', label: '单位' },
      { key: 'warehouse', label: '仓库' },
    ],
    groups: [
      { label: '进货', cols: [{ key: 'in_qty', label: '数量', num: true }, { key: 'in_amt', label: '单据金额', num: true }, { key: 'in_cost', label: '成本', num: true }] },
      { label: '出货', cols: [{ key: 'out_qty', label: '数量', num: true }, { key: 'out_amt', label: '单据金额', num: true }, { key: 'out_cost', label: '成本', num: true }] },
    ],
  },
  inout: {
    title: '进出明细', dlgTitle: '进出明细', endpoint: 'reports/inout', wide: true,
    sumCols: ['qty', 'amount', 'cost'],
    flat: [
      { key: 'date', label: '时间' }, { key: 'code', label: '编码' }, { key: 'name', label: '名称' },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' }, { key: 'unit', label: '单位' },
      { key: 'doc_type', label: '单据类型' }, { key: 'category', label: '进出类别' }, { key: 'direction', label: '方向' },
      { key: 'warehouse_name', label: '仓库', opt: 'whcol' }, { key: 'location_name', label: '库位', opt: 'loccol' },
    ],
    groups: [
      { label: '进出', cols: [
        { key: 'qty', label: '数量', num: true }, { key: 'price', label: '单价', num: true },
        { key: 'amount', label: '金额', num: true }, { key: 'avg_price', label: '均价', num: true },
        { key: 'cost', label: '成本', num: true }] },
      { label: '汇总结存', cols: [
        { key: 'sum_qty', label: '数量', num: true, opt: 'sumcol' },
        { key: 'sum_cost', label: '成本', num: true, opt: 'sumcol' }] },
      { label: '结存均价成本', cols: [
        { key: 'sum_avg', label: '均价', num: true, opt: 'avgcol' },
        { key: 'sum_cost2', label: '成本', num: true, opt: 'avgcol' }] },
    ],
    flat2: [
      { key: 'remark', label: '明细备注' }, { key: 'doc_no', label: '单号' },
      { key: 'unit_name', label: '往来单位' }, { key: 'sign_a', label: '供货人' },
      { key: 'operator', label: '经办人' }, { key: 'sign_b', label: '审核人' }, { key: 'doc_remark', label: '单据备注' },
    ],
  },
  profit: {
    title: '利润分析', dlgTitle: '利润分析', endpoint: 'reports/profit-goods',
    sumCols: ['qty', 'amt', 'cost', 'profit'],
    flat: [
      { key: 'code', label: '编码', first: true }, { key: 'name', label: '名称' },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' }, { key: 'unit', label: '单位' },
      { key: 'warehouse', label: '仓库' },
    ],
    groups: [
      { label: '出货', cols: [
        { key: 'qty', label: '数量', num: true }, { key: 'amt', label: '单据金额', num: true },
        { key: 'cost', label: '成本', num: true }, { key: 'profit', label: '毛利润', num: true }] },
    ],
  },
  borrow: {
    title: '借还统计', dlgTitle: '借还统计', endpoint: 'reports/borrow-summary',
    sumCols: ['lend_qty', 'lend_ret', 'lend_pending', 'lend_cost', 'in_qty', 'in_ret', 'in_pending', 'in_cost'],
    flat: [
      { key: 'code', label: '编码', first: true }, { key: 'name', label: '名称' },
      { key: 'spec', label: '规格' }, { key: 'model', label: '型号' }, { key: 'unit', label: '单位' },
      { key: 'warehouse', label: '仓库' },
    ],
    groups: [
      { label: '借出', cols: [
        { key: 'lend_qty', label: '借出', num: true }, { key: 'lend_ret', label: '归还', num: true },
        { key: 'lend_pending', label: '待还', num: true }, { key: 'lend_cost', label: '成本', num: true }] },
      { label: '借入', cols: [
        { key: 'in_qty', label: '借入', num: true }, { key: 'in_ret', label: '归还', num: true },
        { key: 'in_pending', label: '待还', num: true }, { key: 'in_cost', label: '成本', num: true }] },
    ],
  },
}

// 各报表查询窗口字段（原版布局，每行两项；t: cat货物分类 goods货物 wh仓库 unit往来单位
// doccat进出类别 docty单据类型 date时间 sw开关 text文本）
const DIALOGS = {
  inventory: [
    [{ k: 'category_id', t: 'cat', label: '分类' }, { k: 'goods_id', t: 'goods', label: '货物' }],
    [{ k: 'warehouse_id', t: 'wh', label: '仓库' }, { k: 'filter_zero', t: 'sw', label: '过滤零库存' }],
    [{ k: 'summary', t: 'sw', label: '显示汇总' }, { k: 'by_wh', t: 'sw', label: '显示分仓' }],
  ],
  jxc: [
    [{ k: 'category_id', t: 'cat', label: '分类' }, { k: 'goods_id', t: 'goods', label: '货物' }],
    [{ k: 'start', t: 'date', label: '开始时间' }, { k: 'end', t: 'date', label: '结束时间' }],
    [{ k: 'warehouse_id', t: 'wh', label: '仓库' }, { k: 'simple', t: 'sw', label: '简略模式' }],
    [{ k: 'no_move', t: 'sw', label: '过滤无进出' }, { k: 'filter_zero', t: 'sw', label: '过滤零库存' }],
    [{ k: 'summary', t: 'sw', label: '显示汇总' }, { k: 'by_wh', t: 'sw', label: '显示分仓' }],
  ],
  inoutsum: [
    [{ k: 'category_id', t: 'cat', label: '分类' }, { k: 'goods_id', t: 'goods', label: '货物' }],
    [{ k: 'warehouse_id', t: 'wh', label: '仓库' }, { k: 'doc_category', t: 'doccat', label: '进出类别' }],
    [{ k: 'unit_id', t: 'unit', label: '往来单位' }, { k: 'person', t: 'person', label: '供领人员' }],
    [{ k: 'start', t: 'date', label: '开始时间' }, { k: 'end', t: 'date', label: '结束时间' }],
    [{ k: 'summary', t: 'sw', label: '显示汇总' }, { k: 'by_wh', t: 'sw', label: '显示分仓' }],
  ],
  inout: [
    [{ k: 'doc_type', t: 'docty', label: '单据类型' }, { k: 'doc_category', t: 'doccat', label: '进出类别' }],
    [{ k: 'category_id', t: 'cat', label: '货物分类' }, { k: 'goods_id', t: 'goods', label: '指定货物' }],
    [{ k: 'unit_id', t: 'unit', label: '往来单位' }, { k: 'warehouse_id', t: 'wh', label: '进出仓库' }],
    [{ k: 'person', t: 'person', label: '供领人员' }, { k: 'operator', t: 'person', label: '经办人员' }],
    [{ k: 'start', t: 'date', label: '开始时间' }, { k: 'end', t: 'date', label: '结束时间' }],
    [{ k: 'sumcol', t: 'sw', label: '汇总结存' }, { k: 'whcol', t: 'sw', label: '分仓结存' }],
    [{ k: 'avgcol', t: 'sw', label: '均价成本' }, { k: 'loccol', t: 'sw', label: '库位结存' }],
  ],
  profit: [
    [{ k: 'category_id', t: 'cat', label: '分类' }, { k: 'goods_id', t: 'goods', label: '货物' }],
    [{ k: 'warehouse_id', t: 'wh', label: '仓库' }, { k: 'doc_category', t: 'doccat', label: '进出类别' }],
    [{ k: 'unit_id', t: 'unit', label: '往来单位' }, { k: 'person', t: 'person', label: '供领人员' }],
    [{ k: 'start', t: 'date', label: '开始时间' }, { k: 'end', t: 'date', label: '结束时间' }],
    [{ k: 'summary', t: 'sw', label: '显示汇总' }, { k: 'by_wh', t: 'sw', label: '显示分仓' }],
  ],
  borrow: [
    [{ k: 'category_id', t: 'cat', label: '分类' }, { k: 'goods_id', t: 'goods', label: '货物' }],
    [{ k: 'warehouse_id', t: 'wh', label: '仓库' }, { k: 'doc_category', t: 'doccat', label: '进出类别' }],
    [{ k: 'unit_id', t: 'unit', label: '往来单位' }, { k: 'person', t: 'person', label: '供领人员' }],
    [{ k: 'start', t: 'date', label: '开始时间' }, { k: 'end', t: 'date', label: '结束时间' }],
    [{ k: 'summary', t: 'sw', label: '显示汇总' }, { k: 'by_wh', t: 'sw', label: '显示分仓' }],
  ],
}

// 开关默认值（原版：多数报表 显示汇总/显示分仓 默认开；进销存另三个默认开；进出明细四个默认关）
const SW_DEFS = {
  inventory: { filter_zero: 1, summary: 1, by_wh: 1 },
  jxc: { simple: 1, no_move: 1, filter_zero: 1, summary: 1, by_wh: 1 },
  inoutsum: { summary: 1, by_wh: 1 },
  inout: { sumcol: 1 },   // 原版进出明细默认显示「汇总结存」
  profit: { summary: 1, by_wh: 1 },
  borrow: { summary: 1, by_wh: 1 },
}
// 单据类型下拉（原版）：标签 → 后端 type 值
const DOC_TYPES = [
  { l: '入库单', v: '入库' }, { l: '出库单', v: '出库' }, { l: '调拨单', v: '调拨' },
  { l: '盘点单', v: '盘点' }, { l: '期初库存', v: '期初' },
]

const props = defineProps({ type: String })
const route = useRoute()
const type = ref(props.type || route.params.type)
const cfg = computed(() => REPORTS[type.value] || REPORTS.inventory)
const dlgRows = DIALOGS[type.value] || DIALOGS.inventory
const rows = ref([])
const pageSize = 20
const filterVisible = ref(false)

// 查询条件（含全部字段的统一对象，按报表取用）
const DEFAULTS = {
  category_id: null, goods_id: null, warehouse_id: null, unit_id: null,
  doc_category: null, doc_type: null, person: '', operator: '',
  start: null, end: null,
  ...(SW_DEFS[type.value] || SW_DEFS.inventory),
}
const f = reactive({ ...DEFAULTS })

const goodsList = ref([])
const warehouses = ref([])
const units = ref([])
const docCats = ref([])
const catTree = ref([])   // [{v, l}] 缩进平铺

const visibleFlat = computed(() => (cfg.value.flat || []).filter(c => !c.opt || f[c.opt]))
const visibleGroups = computed(() =>
  (cfg.value.groups || []).map(g => ({ label: g.label, cols: g.cols.filter(c => !c.opt || f[c.opt]) }))
    .filter(g => g.cols.length))
const allCols = computed(() => [
  ...visibleFlat.value, ...visibleGroups.value.flatMap(g => g.cols), ...(cfg.value.flat2 || [])])

// 显示汇总：表格底部追加合计行
const displayRows = computed(() => {
  const rs = rows.value
  if (!f.summary || !rs.length) return rs
  const keys = cfg.value.sumCols || []
  const t = { __total: true }
  for (const k of keys) t[k] = Math.round(rs.reduce((s, r) => s + (Number(r[k]) || 0), 0) * 100) / 100
  if (allCols.value.length) t[allCols.value[0].key] = '合计'
  if (type.value === 'profit') t.profit = Math.round(((t.amt || 0) - (t.cost || 0)) * 100) / 100
  return [...rs, t]
})

const condTip = computed(() => {
  const parts = []
  if (f.start || f.end) parts.push((f.start || '…') + ' ~ ' + (f.end || '…'))
  if (f.warehouse_id) {
    const w = warehouses.value.find(x => x.id === f.warehouse_id)
    if (w) parts.push(w.name)
  }
  return parts.join('　')
})

function options(t) {
  if (t === 'cat') return catTree.value
  if (t === 'docty') return DOC_TYPES
  return []
}

// ---------- 资料选取窗口（原版：点 货物/仓库/往来单位/进出类别/人员 弹对应资料窗） ----------
const PICK_T = new Set(['goods', 'wh', 'unit', 'doccat', 'person'])
const PICK_TITLES = { goods: '货物资料', wh: '仓库信息', unit: '往来单位', doccat: '进出类别', person: '工作人员' }
const PICK_ENTITY = { goods: 'goods', wh: 'warehouses', unit: 'units', doccat: 'categories', person: 'personnel' }
const pickOn = ref(false)
const pickEntity = ref('goods')
let pickField = null
function openPick(fd) {
  pickField = { k: fd.k, t: fd.t }
  pickEntity.value = PICK_ENTITY[fd.t]
  pickOn.value = true
}
function clearPick(fd) { f[fd.k] = (fd.t === 'person' || fd.t === 'doccat') ? '' : null }
function pickLabel(fd) {
  const v = f[fd.k]
  if (v === null || v === undefined || v === '') return ''
  if (fd.t === 'doccat' || fd.t === 'person') return String(v)
  if (fd.t === 'goods') { const g = goodsList.value.find(x => x.id === v); return g ? [g.code, g.name].filter(Boolean).join(' ') : '' }
  if (fd.t === 'wh') { const w = warehouses.value.find(x => x.id === v); return w ? w.name : '' }
  if (fd.t === 'unit') { const u = units.value.find(x => x.id === v); return u ? u.name : '' }
  return ''
}
function onPicked(id, name) {
  if (!pickField) return
  if (pickField.t === 'doccat' || pickField.t === 'person') f[pickField.k] = name || ''
  else f[pickField.k] = id
  pickOn.value = false
}

// ---------- 日期时间窗口（原版：年月切换 + 日历 + 时/分 + 此时/确定） ----------
const MONTHS = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月']
const dtYears = Array.from({ length: 21 }, (_, i) => 2020 + i)
const dateOn = ref(false)
let dateField = null
const dt = reactive({ y: 2026, m: 0, d: 1, h: 0, min: 0 })
function openDate(fd) {
  dateField = fd.k
  const v = f[fd.k] ? new Date(String(f[fd.k]).replace(' ', 'T')) : null
  if (v && !isNaN(v)) {
    dt.y = v.getFullYear(); dt.m = v.getMonth(); dt.d = v.getDate(); dt.h = v.getHours(); dt.min = v.getMinutes()
  } else {
    const now = new Date()
    dt.y = now.getFullYear(); dt.m = now.getMonth(); dt.d = now.getDate()
    if (fd.k === 'end') { dt.h = 23; dt.min = 59 } else { dt.h = 0; dt.min = 0 }  // 原版：开始 0时0分 / 结束 23时59分
  }
  dateOn.value = true
}
function addMonth(d) {
  let m = dt.m + d
  if (m < 0) { m = 11; dt.y-- } else if (m > 11) { m = 0; dt.y++ }
  dt.m = m
}
const dayCells = computed(() => {
  const off = (new Date(dt.y, dt.m, 1).getDay() + 6) % 7  // 周一为第一列
  const dim = new Date(dt.y, dt.m + 1, 0).getDate()
  const prevDim = new Date(dt.y, dt.m, 0).getDate()
  const cells = []
  for (let i = off - 1; i >= 0; i--) cells.push({ d: prevDim - i, cur: false })
  for (let d = 1; d <= dim; d++) cells.push({ d, cur: true })
  for (let d = 1; cells.length % 7; d++) cells.push({ d, cur: false })
  return cells
})
function setNow() {
  const n = new Date()
  dt.y = n.getFullYear(); dt.m = n.getMonth(); dt.d = n.getDate(); dt.h = n.getHours(); dt.min = n.getMinutes()
}
function p2(x) { return String(x).padStart(2, '0') }
function dateOk() {
  if (dateField) f[dateField] = `${dt.y}-${p2(dt.m + 1)}-${p2(dt.d)} ${p2(dt.h)}:${p2(dt.min)}`
  dateOn.value = false
}

function cell(r, c) {
  if (r.__total) {
    if (c.key in r) return r[c.key]
    return ''
  }
  const v = r[c.key]
  return (v === null || v === undefined || v === '') ? '' : v
}

function resetFilter() {
  Object.keys(f).forEach(k => delete f[k])
  Object.assign(f, DEFAULTS)
}

function params() {
  const p = {}
  for (const row of dlgRows) for (const fd of row) {
    const v = f[fd.k]
    if (fd.t === 'sw') p[fd.k] = v ? 1 : 0
    else if (v !== null && v !== undefined && v !== '') p[fd.k] = fd.t === 'date' ? String(v).slice(0, 10) : v
  }
  // 字段名 → 后端参数名（filter_zero/no_move/by_wh/simple 同名直接用）
  return p
}

async function doQuery() {
  filterVisible.value = false
  try {
    let data = await api.list(cfg.value.endpoint, params())
    if (cfg.value.endpoint === 'inventory') {
      data = data.map(r => ({ ...r, alarm: r.status === '正常' ? '' : r.status }))
    }
    // 明细补汇总结存（累计数量/成本，显示随开关）
    if (cfg.value.endpoint === 'reports/inout') {
      const acc = {}
      data = [...data].sort((a, b) => (a.date + a.doc_no).localeCompare(b.date + b.doc_no))
      data = data.map(r => {
        const k = r.code + '|' + r.name
        acc[k] = acc[k] || { qty: 0, cost: 0 }
        acc[k].qty += (r.direction === '进' ? 1 : -1) * r.qty
        acc[k].cost += (r.direction === '进' ? 1 : -1) * r.cost
        const sq = Math.round(acc[k].qty * 100) / 100, sc = Math.round(acc[k].cost * 100) / 100
        return { ...r, sum_qty: sq, sum_cost: sc, sum_avg: sq ? Math.round(sc / sq * 100) / 100 : 0, sum_cost2: sc }
      }).reverse()
    }
    rows.value = data
  } catch (e) { ElMessage.error(e.message) }
}
function doPrint() { window.print() }

onMounted(async () => {
  try {
    const [g, w, u, c, gc] = await Promise.all([
      api.list('goods'), api.list('warehouses'), api.list('units'),
      api.list('categories'), api.list('goods-categories'),
    ])
    goodsList.value = g; warehouses.value = w; units.value = u; docCats.value = c
    // 货物分类 → 缩进平铺
    const byP = {}
    for (const n of gc) (byP[n.parent_id || 0] = byP[n.parent_id || 0] || []).push(n)
    const flat = []
    const walk = (pid, d) => { for (const n of (byP[pid] || [])) { flat.push({ v: n.id, l: '　'.repeat(d) + n.name }); walk(n.id, d + 1) } }
    walk(0, 0)
    const known = new Set(flat.map(n => n.v))
    for (const n of gc) if (!known.has(n.id)) flat.push({ v: n.id, l: n.name })
    catTree.value = flat
  } catch (e) {}
  doQuery()
})
</script>

<style scoped>
.ftip { color: #ffe36e; font-size: 13px; }
.scroll table { min-width: 100%; }
tr.total td { background: var(--ku-head); font-weight: 700; }

/* 原版查询条件窗口：两列布局 + 底部 重置/确定 */
.qgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 22px; padding: 6px 4px 2px; }
.qf { display: flex; align-items: center; }
.ql { width: 88px; text-align: right; font-size: 14px; color: var(--ku-text); white-space: nowrap; flex: 0 0 auto; }
.qctl { flex: 1; min-width: 0; }
.qf :deep(.el-select), .qf :deep(.el-date-editor) { flex: 1; min-width: 0; width: 100%; }
.qf :deep(.el-select__wrapper) { min-height: 30px; height: 30px; }
.qsw { height: 26px; }
.qbtns { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 6px 4px; }
.qbtns .ku-tb { min-width: 88px; }

/* 弹窗选取字段：输入框 + ▼选择 / ✕清空（原版样式） */
.qpick { display: flex; align-items: center; gap: 3px; cursor: pointer; }
.qp-in { flex: 1; min-width: 0; height: 30px; border: 1px solid var(--ku-border-soft); background: #fff; border-radius: 2px; padding: 0 6px; font-size: 14px; color: #222; outline: none; font-family: inherit; }
.qp-in:focus { border-color: var(--ku-accent); }
.qp-btn { flex: 0 0 auto; width: 26px; height: 30px; line-height: 28px; text-align: center; border: 1px solid var(--ku-border-soft); background: var(--ku-panel); border-radius: 2px; font-size: 12px; color: var(--ku-text); cursor: pointer; user-select: none; }
.qp-btn:hover { background: var(--ku-head); }

/* 资料选取窗口（复用 MasterView 选取窗） */
.unit-pick-body { height: 62vh; display: flex; }
.unit-pick-body :deep(.ku-win) { flex: 1; min-width: 0; }
.unit-pick-dlg :deep(.ku-win-main) { max-height: none; height: calc(100% - 54px); }

/* 日期时间窗口（原版样式） */
.date-dlg :deep(.el-dialog__body) { padding-top: 8px; }
.dt-head { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 2px 0 8px; }
.dt-arr { cursor: pointer; color: var(--ku-text); font-size: 13px; padding: 2px 4px; user-select: none; }
.dt-arr:hover { color: var(--ku-accent); }
.dt-sel { height: 26px; border: 1px solid var(--ku-border-soft); border-radius: 2px; background: #fff; font-size: 13px; color: #222; }
.dt-sel.sm { width: 56px; }
.dt-week { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-size: 12px; color: #4a7a8a; padding-bottom: 2px; }
.dt-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px 0; }
.dt-day { text-align: center; line-height: 28px; height: 28px; font-size: 14px; color: #222; cursor: pointer; border-radius: 2px; user-select: none; }
.dt-day.wk { color: #e0342b; }
.dt-day.dim { color: #bbb; cursor: default; }
.dt-day:hover { background: var(--ku-head); }
.dt-day.sel { background: var(--ku-accent); color: #fff; font-weight: 700; }
.dt-time { display: flex; align-items: center; gap: 6px; padding-top: 10px; font-size: 14px; color: var(--ku-text); }
.dt-time .ku-tb { margin-left: 6px; min-width: 60px; }
</style>
