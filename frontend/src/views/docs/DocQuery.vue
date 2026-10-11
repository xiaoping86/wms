<template>
  <div class="ku-page" :class="{ 'ku-embedded': docType }" :style="docType ? '' : ''">
    <!-- 工具栏（整页模式） -->
    <div v-if="!docType" class="ku-toolbar no-print">
      <button class="ku-tb home" @click="$router.push('/home')">&lt;主页</button>
      <button class="ku-tb key" @click="filterVisible = true">查询</button>
      <button class="ku-tb" @click="rowsAll = []; rows = []">清空</button>
      <button class="ku-tb" @click="doPrint">预览</button>
      <button class="ku-tb" @click="doPrint">打印</button>
      <button class="ku-tb key" :disabled="!selected" @click="openDoc">打开单据</button>
      <button class="ku-tb" @click="goBack">返回前页</button>
    </div>
    <!-- 内嵌模式小工具栏 -->
    <div v-else class="ku-toolbar no-print">
      <button class="ku-tb key" @click="filterVisible = true">查询</button>
      <button class="ku-tb" @click="rowsAll = []; rows = []">清空</button>
    </div>

    <div class="print-area">
      <div class="ku-titlebar" style="letter-spacing:4px">{{ docType ? typeLabel : '单据查询' }}</div>
      <div class="ku-grid-wrap">
        <div class="scroll" style="max-height: calc(100vh - 200px); overflow: auto">
          <table class="ku-grid" data-grid-key="docquery">
            <thead>
              <tr>
                <th v-for="c in cols" :key="c.key" :class="{ req: c.key === 'date' }">{{ c.label }}</th>
                <th v-if="picker" style="width:70px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in rows" :key="r.type + r.id" :class="{ sel: selected === r }" @click="selected = r" @dblclick="picker ? emit('pick', { type: r.type, id: r.id }) : openDoc()">
                <td v-for="c in cols" :key="c.key" :class="{ num: c.num }">{{ r[c.key] }}</td>
                <td v-if="picker">
                  <button class="ku-tb" style="padding:2px 10px" @click.stop="emit('pick', { type: r.type, id: r.id })">选单</button>
                </td>
              </tr>
              <tr v-if="!rows.length" class="ku-empty-row"><td :colspan="cols.length + (picker ? 1 : 0)"></td></tr>
            </tbody>
          </table>
        </div>
        <div class="ku-foot">
          <span>每页 20 行</span>
          <span>共 {{ rows.length }} 张单据</span>
        </div>
      </div>
    </div>

    <!-- 查询条件（原版"单据查询"条件窗口：两列 8 项，▼ 弹对应选择窗口 / ✕ 清空） -->
    <el-dialog draggable overflow class="win-dlg cx-dlg" v-model="filterVisible" title="单据查询" width="720px" append-to-body>
      <div class="cx-grid">
        <div class="cx-row" v-if="!docType">
          <span class="cx-lb">单据类型：</span>
          <div class="cx-field">
            <input class="cx-input" readonly placeholder="请选择" :value="f.type ? TYPE_LABELS[f.type] : ''" @click="typeVisible = true" />
            <button class="cx-pick" title="选择" @click="typeVisible = true">▼</button>
            <button class="cx-clear" title="清空" @click="f.type = ''">✕</button>
          </div>
        </div>
        <div class="cx-row" v-if="!docType">
          <span class="cx-lb">进出类别：</span>
          <div class="cx-field">
            <input class="cx-input" readonly placeholder="请选择" :value="f.category" @click="openPick('category', 'categories')" />
            <button class="cx-pick" title="选择" @click="openPick('category', 'categories')">▼</button>
            <button class="cx-clear" title="清空" @click="f.category = ''">✕</button>
          </div>
        </div>
        <div class="cx-row">
          <span class="cx-lb">往来单位：</span>
          <div class="cx-field">
            <input class="cx-input" readonly placeholder="请选择" :value="f.unit" @click="openPick('unit', 'units')" />
            <button class="cx-pick" title="选择" @click="openPick('unit', 'units')">▼</button>
            <button class="cx-clear" title="清空" @click="f.unit = ''">✕</button>
          </div>
        </div>
        <div class="cx-row">
          <span class="cx-lb">进出仓库：</span>
          <div class="cx-field">
            <input class="cx-input" readonly placeholder="请选择" :value="f.warehouse" @click="openPick('warehouse', 'warehouses')" />
            <button class="cx-pick" title="选择" @click="openPick('warehouse', 'warehouses')">▼</button>
            <button class="cx-clear" title="清空" @click="f.warehouse = ''">✕</button>
          </div>
        </div>
        <div class="cx-row">
          <span class="cx-lb">供领人员：</span>
          <div class="cx-field">
            <input class="cx-input" readonly placeholder="请选择" :value="f.sign_a" @click="openPick('sign_a', 'personnel')" />
            <button class="cx-pick" title="选择" @click="openPick('sign_a', 'personnel')">▼</button>
            <button class="cx-clear" title="清空" @click="f.sign_a = ''">✕</button>
          </div>
        </div>
        <div class="cx-row">
          <span class="cx-lb">经办人员：</span>
          <div class="cx-field">
            <input class="cx-input" readonly placeholder="请选择" :value="f.operator" @click="openPick('operator', 'personnel')" />
            <button class="cx-pick" title="选择" @click="openPick('operator', 'personnel')">▼</button>
            <button class="cx-clear" title="清空" @click="f.operator = ''">✕</button>
          </div>
        </div>
        <div class="cx-row">
          <span class="cx-lb">开始时间：</span>
          <el-date-picker v-model="f.start" type="date" value-format="YYYY-MM-DD" style="flex:1; min-width:0" />
        </div>
        <div class="cx-row">
          <span class="cx-lb">结束时间：</span>
          <el-date-picker v-model="f.end" type="date" value-format="YYYY-MM-DD" style="flex:1; min-width:0" />
        </div>
      </div>
      <template #footer>
        <span class="cx-foot-spacer"></span>
        <button class="ku-btn cx-btn" @click="resetFilter">重置</button>
        <button class="ku-btn cx-btn" @click="query">确定</button>
      </template>
    </el-dialog>

    <!-- 单据类型选择（原版"选择分类"树窗口：入库单/出库单/调拨单/盘点单） -->
    <el-dialog draggable overflow class="win-dlg dlg-fit" v-model="typeVisible" title="选择分类" width="320px" append-to-body>
      <div class="type-tree">
        <div class="type-root">单据类型</div>
        <div v-for="(v, k) in TYPE_TREE" :key="k" class="type-item" :class="{ sel: typeSel === k }" @click="typeSel = k" @dblclick="typeSel = k; confirmType()">{{ v }}</div>
      </div>
      <template #footer>
        <span class="cx-foot-spacer"></span>
        <button class="ku-btn cx-btn" @click="confirmType">确定</button>
        <button class="ku-btn cx-btn" @click="typeVisible = false">取消</button>
      </template>
    </el-dialog>

    <!-- 资料选择窗口（原版：进出类别/往来单位/进出仓库/供领人员/经办人员 弹对应资料窗） -->
    <el-dialog draggable overflow v-model="pickOn" :title="PICK_TITLES[pickEntity] || '选择数据'" width="1000px" append-to-body class="win-dlg">
      <div style="min-height:420px">
        <MasterView v-if="pickOn" :key="pickEntity" :entity="pickEntity" pick-mode @pick="onPicked" />
      </div>
    </el-dialog>

    <!-- 单据明细 -->
    <el-dialog draggable overflow class="win-dlg" v-model="detailVisible" :title="typeLabel + '明细 - ' + (detail.header?.doc_no || '')" width="820px" append-to-body>
      <el-descriptions :column="3" border size="small" style="margin-bottom:12px">
        <el-descriptions-item label="单据号">{{ detail.header?.doc_no }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ detail.header?.date }}</el-descriptions-item>
        <el-descriptions-item label="类别">{{ detail.header?.category }}</el-descriptions-item>
        <el-descriptions-item label="供领人">{{ detail.header?.sign_a }}</el-descriptions-item>
        <el-descriptions-item label="经办人">{{ detail.header?.operator }}</el-descriptions-item>
        <el-descriptions-item label="审核人">{{ detail.header?.sign_b }}</el-descriptions-item>
      </el-descriptions>
      <el-table :data="detail.items" stripe border size="small" max-height="360">
        <el-table-column type="index" label="#" width="46" />
        <el-table-column v-for="c in itemCols" :key="c.key" :prop="c.key" :label="c.label" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import MasterView from '../master/MasterView.vue'

const TYPE_LABELS = { inbound: '入库单', outbound: '出库单', transfer: '调拨单', check: '盘点单', initial: '期初库存' }
const ITEM_COLS = {
  inbound: [{ key: 'goods_name', label: '货物' }, { key: 'location_name', label: '库位' }, { key: 'qty', label: '数量' }, { key: 'price', label: '单价' }, { key: 'amount', label: '金额' }],
  outbound: [{ key: 'goods_name', label: '货物' }, { key: 'location_name', label: '库位' }, { key: 'qty', label: '数量' }, { key: 'price', label: '单价' }, { key: 'amount', label: '金额' }],
  transfer: [{ key: 'goods_name', label: '货物' }, { key: 'from_location_name', label: '调出库位' }, { key: 'to_location_name', label: '调入库位' }, { key: 'qty', label: '数量' }, { key: 'price', label: '单价' }, { key: 'amount', label: '金额' }],
  check: [{ key: 'goods_name', label: '货物' }, { key: 'location_name', label: '库位' }, { key: 'book_qty', label: '账面数量' }, { key: 'actual_qty', label: '实盘数量' }, { key: 'diff_qty', label: '差异' }],
  initial: [{ key: 'goods_name', label: '货物' }, { key: 'warehouse_name', label: '仓库' }, { key: 'location_name', label: '库位' }, { key: 'qty', label: '数量' }, { key: 'price', label: '单价' }, { key: 'amount', label: '金额' }],
}

const props = defineProps({ docType: String, picker: Boolean })
const emit = defineEmits(['pick'])
const router = useRouter()

const rowsAll = ref([])
const rows = ref([])
const selected = ref(null)
const filterVisible = ref(false)
const detailVisible = ref(false)
const detail = reactive({ header: {}, items: [] })
const f = reactive({ type: '', category: '', unit: '', warehouse: '', sign_a: '', operator: '', start: '', end: '' })

// 原版"选择分类"树（期初库存不在单据查询类型树内）
const TYPE_TREE = { inbound: '入库单', outbound: '出库单', transfer: '调拨单', check: '盘点单' }
const PICK_TITLES = { categories: '进出类别', units: '往来单位', warehouses: '仓库信息', personnel: '工作人员' }
const typeVisible = ref(false)
const typeSel = ref('')
const pickOn = ref(false)
const pickEntity = ref('')
const pickTarget = ref('')

function confirmType() {
  if (typeSel.value) f.type = typeSel.value
  typeVisible.value = false
}
function openPick(target, entity) {
  pickTarget.value = target
  pickEntity.value = entity
  pickOn.value = true
}
function onPicked(id, name) {
  if (pickTarget.value) f[pickTarget.value] = name || ''
  pickOn.value = false
}

const cols = [
  { key: 'date', label: '时间' }, { key: 'doc_no', label: '单号' }, { key: 'unit', label: '往来单位' },
  { key: 'type_label', label: '单据类型' }, { key: 'category', label: '进出类别' },
  { key: 'wh1', label: '仓库1' }, { key: 'wh2', label: '仓库2' }, { key: 'amount', label: '金额', num: true },
  { key: 'sign_a', label: '供领人' }, { key: 'operator', label: '经办人' }, { key: 'sign_b', label: '审核人' },
  { key: 'remark', label: '备注说明' },
]
const typeLabel = computed(() => TYPE_LABELS[props.docType] || '单据查询')
const itemCols = computed(() => ITEM_COLS[detail.type] || [])

async function query() {
  filterVisible.value = false
  try {
    const p = {}
    if (f.start) p.start = f.start
    if (f.end) p.end = f.end
    if (props.docType) p.doc_type = props.docType
    else if (f.type) p.doc_type = f.type
    if (f.unit) p.unit = f.unit
    if (f.category) p.category = f.category
    if (f.warehouse) p.warehouse = f.warehouse
    if (f.sign_a) p.sign_a = f.sign_a
    if (f.operator) p.operator = f.operator
    rowsAll.value = await api.list('docs-query', p)
    rows.value = rowsAll.value
    selected.value = null
  } catch (e) { ElMessage.error(e.message) }
}

function resetFilter() {
  f.type = ''; f.category = ''; f.unit = ''; f.warehouse = ''
  f.sign_a = ''; f.operator = ''; f.start = ''; f.end = ''
  typeSel.value = ''
}

function doPrint() { window.print() }

onMounted(() => { query() })

async function openDoc() {
  if (!selected.value) return
  const r = selected.value
  // 独立单据查询页：点"打开单据"跳转到对应单据编辑页（查看模式），由 DocSheet 按 URL 参数自动载入
  router.push('/doc/' + r.type + '?docid=' + r.id)
}

// 返回前页：回浏览器上一页（如从入库单跳来则回入库单）；无历史记录时回主页
function goBack() {
  if (window.history.state && window.history.state.back) router.back()
  else router.push('/home')
}

let _maps = null
function nameMaps() {
  if (_maps) return Promise.resolve(_maps)
  return Promise.all([api.list('goods'), api.list('warehouses'), api.list('locations')]).then(([g, w, l]) => {
    _maps = {
      goods: Object.fromEntries(g.map(x => [x.id, x.name])),
      warehouses: Object.fromEntries(w.map(x => [x.id, x.name])),
      locations: Object.fromEntries(l.map(x => [x.id, x.name])),
    }
    return _maps
  })
}
</script>

<style scoped>
tr.sel td { background: #ffe9a8 !important; }
/* 原版查询条件窗口：浅蓝底两列网格 */
.cx-dlg .cx-grid { display: grid; grid-template-columns: 1fr 1fr; column-gap: 18px; row-gap: 14px; padding: 8px 6px 4px; }
.cx-row { display: flex; align-items: center; gap: 4px; }
.cx-lb { flex: 0 0 auto; font-size: 13px; color: var(--ku-text); white-space: nowrap; }
.cx-dlg .el-date-editor, .cx-dlg .el-select { --el-component-size: 26px; }
.cx-dlg .el-date-editor { width: 100% !important; }
.cx-foot-spacer { flex: 1; }
.cx-btn { min-width: 76px; }

/* 原版字段样式：只读输入框 + ▼选择 / ✕清空 两个小按钮 */
.cx-field { flex: 1; display: flex; align-items: stretch; gap: 3px; min-width: 0; }
.cx-input { flex: 1; min-width: 0; height: 26px; border: 1px solid #9fc6d8; border-radius: 3px; background: #fff; padding: 0 6px; font-size: 13px; color: var(--ku-text); }
.cx-input::placeholder { color: #9ab4c0; }
.cx-pick, .cx-clear { flex: 0 0 auto; width: 26px; border: 1px solid #9fc6d8; border-radius: 3px; background: #e8f5fb; color: #1f6474; cursor: pointer; font-size: 11px; line-height: 1; padding: 0; }
.cx-clear { color: #c0392b; }
.cx-pick:hover, .cx-clear:hover { background: #d5edf8; }

/* 原版"选择分类"树窗口 */
.type-tree { border: 1px solid #9fc6d8; border-radius: 4px; background: #fff; padding: 6px; min-height: 220px; overflow: auto; }
.type-root { font-weight: 600; color: #1f6474; padding: 2px 4px; }
.type-item { padding: 3px 4px 3px 28px; cursor: pointer; color: var(--ku-text); border-radius: 3px; }
.type-item:hover { background: #e8f5fb; }
.type-item.sel { background: #1f6474; color: #fff; }
</style>
