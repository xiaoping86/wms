<template>
  <div class="bom-page">
    <!-- 顶部工具条 -->
    <div class="bom-top">
      <b>BOM 表管理</b>
      <span class="sp"></span>
      <button class="bom-btn" @click="exportAll">导出全部 BOM</button>
      <button class="bom-btn primary" @click="openEdit(null)">＋ 新建 BOM</button>
    </div>

    <!-- 搜索 -->
    <div class="bom-card">
      <input class="bom-input" v-model="kw" placeholder="搜索型号 / 名称..." @keyup.enter="load" />
      <button class="bom-btn" @click="load">查询</button>
    </div>

    <!-- BOM 列表（列名随字段定义） -->
    <div class="bom-card grow">
      <table class="bom-grid" data-grid-key="bom.head">
        <thead>
          <tr>
            <th style="width:110px">{{ lval('model') }}</th>
            <th v-for="d in listHeadDefs" :key="d.key" :style="{ width: colW(d.key) }">{{ d.label }}</th>
            <th style="width:70px">零件数</th>
            <th style="width:130px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in list" :key="b.id">
            <td class="strong">{{ b.values && b.values.model }}</td>
            <td v-for="d in listHeadDefs" :key="d.key">{{ b.values ? (b.values[d.key] || '') : '' }}</td>
            <td>{{ b.part_count }}</td>
            <td class="ops">
              <button class="bom-btn sm" @click="openView(b)">查看</button>
              <button class="bom-btn sm" @click="openEdit(b)">编辑</button>
              <button class="bom-btn sm danger" @click="del(b)">删除</button>
            </td>
          </tr>
          <tr v-if="!list.length"><td :colspan="3 + listHeadDefs.length" class="empty">暂无 BOM，点右上角「＋ 新建 BOM」创建</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 查看 BOM 详情 -->
    <el-dialog draggable overflow v-model="viewOn" :title="'BOM：' + vVal('model')" width="900px" append-to-body class="win-dlg">
      <div class="bom-info" v-if="view.values">
        <span class="tag">{{ vVal('model') }}</span>
        <template v-for="d in (view.field_defs || []).filter(x => x.key !== 'model')" :key="d.key">
          <span v-if="vVal(d.key) !== ''">| {{ d.label }}：{{ vVal(d.key) }}</span>
        </template>
        <span>| {{ (view.items || []).length }}项</span>
      </div>
      <div class="view-grid-wrap">
        <table class="bom-grid view-grid" data-grid-key="bom.view">
          <thead>
            <tr><th style="width:56px">序号</th>
                <th v-for="d in (view.col_defs || [])" :key="d.key" :style="{ width: colW(d.key) }">{{ d.label }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in view.items" :key="i">
              <td>{{ r.seq }}</td>
              <td v-for="d in (view.col_defs || [])" :key="d.key">{{ r[d.key] }}</td>
            </tr>
            <tr v-if="!(view.items || []).length"><td :colspan="1 + (view.col_defs || []).length" class="empty">无明细</td></tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <button class="bom-btn" @click="exportOne(view)">导出 Excel</button>
        <button class="bom-btn" @click="viewOn = false">关 闭</button>
      </template>
    </el-dialog>

    <!-- 新建 / 编辑 BOM -->
    <el-dialog draggable overflow v-model="editOn" :title="editTitle" width="1020px" append-to-body class="win-dlg">
      <!-- 表头字段：双击字段名可改名，➕ 增加字段，自定义字段可 ✕ 删除 -->
      <div class="edit-head">
        <label v-for="(d, i) in editForm.field_defs" :key="d.key" class="hd">
          <span class="lbl" :title="'双击可改字段名' + (isCustom(d) ? '，✕ 删除该字段' : '')" @dblclick="renameHead(i)">
            {{ d.label }}<button v-if="isCustom(d)" class="x" @click.prevent="delHead(i)" title="删除该字段">✕</button>
          </span>
          <input class="bom-input" v-model="editForm.values[d.key]" :style="{ width: headW(d.key) }"
                 :placeholder="d.key === 'model' ? '如 D809A' : ''" />
        </label>
        <button class="bom-btn sm" @click="addHead" title="增加表头字段">➕ 字段</button>
      </div>

      <div class="edit-toolbar">
        <button class="bom-btn sm" @click="addRow">➕ 加一行</button>
        <button class="bom-btn sm" @click="pasteOn = !pasteOn">📋 从 Excel 粘贴</button>
        <button class="bom-btn sm danger" @click="delRow">🗑 删除选中行</button>
        <span class="sp"></span>
        <span class="hint">双击单元格编辑内容；双击列名改名；表头「➕ 字段」、明细「➕ 列」可增加项目</span>
      </div>
      <textarea v-if="pasteOn" class="paste-area" v-model="pasteText"
                placeholder="从 Excel 复制后，点这里按 Ctrl+V 粘贴（按列顺序：数量 图号 名称 基型 备注 … Tab 分隔）"
                @paste.prevent="doPaste"></textarea>

      <div class="view-grid-wrap tall">
        <table class="bom-grid edit-grid" data-grid-key="bom.edit">
          <thead>
            <tr>
              <th style="width:48px">序号</th>
              <th v-for="(d, ci) in editForm.col_defs" :key="d.key" :style="{ width: colW(d.key) }"
                  :title="'双击可改列名' + (isCustom(d) ? '，✕ 删除该列' : '')" @dblclick="renameCol(ci)">
                {{ d.label }}<button v-if="isCustom(d)" class="x" @click.stop="delCol(ci)" title="删除该列">✕</button>
              </th>
              <th class="addcol"><button class="bom-btn sm" @click="addCol" title="增加明细列">➕ 列</button></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in editForm.items" :key="i" :class="{ sel: editSel === i }" @click="editSel = i">
              <td>{{ i + 1 }}</td>
              <td v-for="d in editForm.col_defs" :key="d.key">
                <input v-if="d.key === 'qty'" v-model="r[d.key]" type="number" step="any" />
                <input v-else v-model="r[d.key]" />
              </td>
              <td></td>
            </tr>
            <tr v-if="!editForm.items.length"><td :colspan="2 + editForm.col_defs.length" class="empty">还没有明细，点「加一行」或从 Excel 粘贴</td></tr>
          </tbody>
        </table>
      </div>

      <template #footer>
        <button class="bom-btn" @click="editOn = false">取消</button>
        <button class="bom-btn primary" @click="save">保 存</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

/* 默认定义：表头字段（model=型号必填）与明细列（qty/dwg/name/base/remark 固定列） */
const DEF_HEAD = [
  { key: 'model', label: '型号' }, { key: 'name', label: '名称' },
  { key: 'voltage', label: '电压' }, { key: 'current', label: '电流' },
  { key: 'doc_no', label: '编号' }, { key: 'remark', label: '备注' },
]
const DEF_COLS = [
  { key: 'qty', label: '数量' }, { key: 'dwg', label: '图号' }, { key: 'name', label: '名称' },
  { key: 'base', label: '基型' }, { key: 'remark', label: '备注' },
]
const DEF_KEY = new Set(['model', 'name', 'voltage', 'current', 'doc_no', 'remark'])
const COL_KEY = new Set(['qty', 'dwg', 'name', 'base', 'remark'])
const HEAD_W = { model: 170, name: 170, voltage: 90, current: 90, doc_no: 150, remark: 150 }
const COL_W = { qty: 70, dwg: 150, name: 0, base: 120, remark: 140 } // 0 = 自动撑开

const list = ref([])
const kw = ref('')
const viewOn = ref(false)
const view = reactive({ values: {}, field_defs: [], col_defs: [], items: [] })
const editOn = ref(false)
const editSel = ref(-1)
const pasteOn = ref(false)
const pasteText = ref('')
const editForm = reactive({ id: null, values: {}, field_defs: [], col_defs: [], items: [] })

const editTitle = computed(() => editForm.id ? ('编辑 BOM：' + (editForm.values.model || '')) : '新建 BOM')
const listHeadDefs = computed(() => (list.value[0] && list.value[0].field_defs) || DEF_HEAD)

function defsOf(d, dflt) { return (Array.isArray(d) && d.length) ? d : dflt }
function colW(key) { const w = COL_W[key]; return w ? w + 'px' : undefined }
function headW(key) { return (HEAD_W[key] || 120) + 'px' }
function isCustom(d) { return d.key !== 'model' && !DEF_KEY.has(d.key) && !COL_KEY.has(d.key) }
function lval(k) { const d = listHeadDefs.value.find(x => x.key === k); return d ? d.label : k }
function vVal(k) { return (view.values || {})[k] || '' }

/* 上次用过的字段/列定义记到 localStorage，新建 BOM 沿用 */
function rememberDefs() {
  try {
    localStorage.setItem('bom_defs', JSON.stringify({ field_defs: editForm.field_defs, col_defs: editForm.col_defs }))
  } catch (e) { /* 忽略 */ }
}
function savedDefs() {
  try { return JSON.parse(localStorage.getItem('bom_defs') || 'null') } catch (e) { return null }
}

async function load() {
  list.value = await api.list('boms', kw.value ? { q: kw.value } : {})
}
onMounted(load)

function openView(b) {
  api.get('boms/' + b.id).then(d => {
    Object.assign(view, { ...d, values: d.values || {} })
    viewOn.value = true
  }).catch(e => ElMessage.error(e.message))
}

function openEdit(b) {
  editSel.value = -1
  pasteOn.value = false
  pasteText.value = ''
  if (b) {
    api.get('boms/' + b.id).then(d => {
      Object.assign(editForm, {
        id: d.id,
        values: { ...(d.values || {}) },
        field_defs: defsOf(d.field_defs, DEF_HEAD).map(x => ({ ...x })),
        col_defs: defsOf(d.col_defs, DEF_COLS).map(x => ({ ...x })),
        items: (d.items || []).map(x => ({ ...x })),
      })
      editOn.value = true
    }).catch(e => ElMessage.error(e.message))
  } else {
    const saved = savedDefs() || {}
    const field_defs = defsOf(saved.field_defs, DEF_HEAD).map(x => ({ ...x }))
    const col_defs = defsOf(saved.col_defs, DEF_COLS).map(x => ({ ...x }))
    const values = {}
    field_defs.forEach(d => { values[d.key] = '' })
    Object.assign(editForm, { id: null, values, field_defs, col_defs, items: [emptyRow()] })
    editOn.value = true
  }
}
function emptyRow() {
  const r = {}
  editForm.col_defs.forEach(d => { r[d.key] = d.key === 'qty' ? 1 : '' })
  r.seq = null
  return r
}
function addRow() { editForm.items.push(emptyRow()); editSel.value = editForm.items.length - 1 }
function delRow() {
  if (editSel.value < 0) return ElMessage.info('请先点击选中一行')
  editForm.items.splice(editSel.value, 1)
  editSel.value = -1
}

/* ---------- 表头字段：改名 / 增加 / 删除 ---------- */
async function renameHead(i) {
  const d = editForm.field_defs[i]
  try {
    const r = await ElMessageBox.prompt('修改表头字段名（双击字段名也可打开）', '字段名', {
      inputValue: d.label, inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    })
    d.label = r.value.trim()
    rememberDefs()
  } catch (e) { /* 取消 */ }
}
async function addHead() {
  try {
    const r = await ElMessageBox.prompt('输入新表头字段的名称（如：功率、颜色）', '增加表头字段', {
      inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    })
    const label = r.value.trim()
    if (editForm.field_defs.some(d => d.label === label)) return ElMessage.warning('已有同名字段')
    const used = editForm.field_defs.map(d => d.key)
    let n = 1
    while (used.includes('h' + n)) n++
    editForm.field_defs.push({ key: 'h' + n, label })
    editForm.values['h' + n] = ''
    rememberDefs()
  } catch (e) { /* 取消 */ }
}
function delHead(i) {
  const d = editForm.field_defs[i]
  if (!isCustom(d)) return
  ElMessageBox.confirm(`删除表头字段「${d.label}」？其已填内容一并清除。`, '提示', { type: 'warning' })
    .then(() => {
      editForm.field_defs.splice(i, 1)
      delete editForm.values[d.key]
      rememberDefs()
    }).catch(() => {})
}

/* ---------- 明细列：改名 / 增加 / 删除 ---------- */
async function renameCol(ci) {
  const d = editForm.col_defs[ci]
  try {
    const r = await ElMessageBox.prompt('修改明细列名（双击列名也可打开）', '列名', {
      inputValue: d.label, inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    })
    d.label = r.value.trim()
    rememberDefs()
  } catch (e) { /* 取消 */ }
}
async function addCol() {
  try {
    const r = await ElMessageBox.prompt('输入新明细列的名称（如：材料、供应商）', '增加明细列', {
      inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    })
    const label = r.value.trim()
    if (editForm.col_defs.some(d => d.label === label)) return ElMessage.warning('已有同名列')
    const used = editForm.col_defs.map(d => d.key)
    let n = 1
    while (used.includes('c' + n)) n++
    editForm.col_defs.push({ key: 'c' + n, label })
    editForm.items.forEach(it => { it['c' + n] = '' })
    rememberDefs()
  } catch (e) { /* 取消 */ }
}
function delCol(ci) {
  const d = editForm.col_defs[ci]
  if (!isCustom(d)) return
  ElMessageBox.confirm(`删除明细列「${d.label}」？该列已填内容一并清除。`, '提示', { type: 'warning' })
    .then(() => {
      editForm.col_defs.splice(ci, 1)
      editForm.items.forEach(it => { delete it[d.key] })
      rememberDefs()
    }).catch(() => {})
}

/* ---------- 粘贴：按当前列顺序逐格落位 ---------- */
function doPaste(e) {
  const text = (e.clipboardData || window.clipboardData).getData('text') || ''
  const cols = editForm.col_defs
  let n = 0
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue
    const c = line.split('\t').map(s => s.trim())
    const row = emptyRow()
    cols.forEach((d, i) => {
      row[d.key] = d.key === 'qty' ? (parseFloat(c[i]) || 1) : (c[i] || '')
    })
    editForm.items.push(row)
    n++
  }
  pasteText.value = ''
  pasteOn.value = false
  ElMessage.success('已粘贴 ' + n + ' 行明细')
}

async function save() {
  const modelKey = (editForm.field_defs[0] && editForm.field_defs[0].key) || 'model'
  if (!(editForm.values[modelKey] || '').trim()) return ElMessage.warning('请填写 BOM 型号')
  const items = editForm.items.filter(r =>
    editForm.col_defs.some(d => d.key !== 'qty' && (r[d.key] || '').toString().trim()))
  if (!items.length) return ElMessage.warning('请至少填写一行明细')
  const body = {
    id: editForm.id,
    field_defs: editForm.field_defs,
    col_defs: editForm.col_defs,
    values: editForm.values,
    items,
  }
  try {
    if (editForm.id) await api.update('boms', editForm.id, body)
    else await api.create('boms', body)
    ElMessage.success('已保存')
    editOn.value = false
    load()
  } catch (e) { ElMessage.error(e.message) }
}

async function del(b) {
  try { await ElMessageBox.confirm(`确认删除 BOM【${(b.values || {}).model}】及其全部明细？`, '提示', { type: 'warning' }) } catch (e) { return }
  try { await api.remove('boms', b.id); ElMessage.success('已删除'); load() } catch (e) { ElMessage.error(e.message) }
}

/* ---------- 导出 CSV（Excel 可直接打开，列随定义） ---------- */
function csvOf(name, head, rows) {
  const esc = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"'
  const csv = '\uFEFF' + [head.map(esc).join(','), ...rows.map(r => r.map(esc).join(','))].join('\r\n')
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}
function exportOne(b) {
  const defs = defsOf(b.col_defs, DEF_COLS)
  csvOf(`BOM_${vVal('model') || (b.values || {}).model || '导出'}.csv`,
    ['序号', ...defs.map(d => d.label)],
    (b.items || []).map(r => [r.seq, ...defs.map(d => r[d.key])]))
}
function exportAll() {
  if (!list.value.length) return ElMessage.info('暂无 BOM 可导出')
  const defs = listHeadDefs.value.filter(d => d.key !== 'model')
  const rows = list.value.map(b => [
    (b.values || {}).model || '',
    ...defs.map(d => (b.values || {})[d.key] || ''),
    b.part_count,
  ])
  csvOf('BOM_全部.csv', [lval('model'), ...defs.map(d => d.label), '零件数'], rows)
  // 再逐个导出明细文件
  for (const b of list.value) api.get('boms/' + b.id).then(d => exportOne({ ...d, values: d.values || {} })).catch(() => {})
}
</script>

<style scoped>
.bom-page { padding: 0; }
.bom-top { display: flex; align-items: center; gap: 10px; padding: 10px 2px; }
.bom-top b { color: #1f5fa9; font-size: 15px; }
.sp { flex: 1; }
.bom-card { background: #fff; border: 1px solid #dbe4ee; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; }
.bom-input { border: 1px solid #c9d6e4; border-radius: 6px; padding: 7px 10px; font-size: 13px; outline: none; min-width: 220px; }
.bom-input:focus { border-color: #2f6fd0; box-shadow: 0 0 0 2px rgba(47,111,208,.15); }
.bom-btn { border: 1px solid #c9d6e4; background: #fff; color: #24425f; border-radius: 7px; padding: 7px 14px; font-size: 13px; cursor: pointer; }
.bom-btn:hover { border-color: #2f6fd0; color: #2f6fd0; }
.bom-btn.primary { background: #2f6fd0; border-color: #2f6fd0; color: #fff; }
.bom-btn.primary:hover { background: #255cab; color: #fff; }
.bom-btn.danger { background: #e05252; border-color: #e05252; color: #fff; }
.bom-btn.danger:hover { background: #c74141; color: #fff; }
.bom-btn.sm { padding: 4px 10px; font-size: 12px; }
.bom-grid { width: 100%; border-collapse: collapse; font-size: 13px; }
.bom-grid th { background: #eef4fb; color: #24425f; text-align: left; padding: 7px 9px; border-bottom: 1px solid #dbe4ee; }
.bom-grid td { padding: 7px 9px; border-bottom: 1px solid #edf2f8; color: #2b3a4a; }
.bom-grid tr:hover td { background: #f6f9fd; }
.bom-grid td.strong { font-weight: 600; color: #1f5fa9; }
.bom-grid td.ops { white-space: nowrap; }
.bom-grid td.ops .bom-btn { margin-right: 5px; }
.bom-grid td.empty, .bom-grid .empty { text-align: center; color: #9aa7b5; padding: 22px 0; }
/* 详情 */
.bom-info { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 13px; color: #44586c; padding-bottom: 8px; }
.bom-info .tag { background: #2f6fd0; color: #fff; border-radius: 5px; padding: 2px 8px; font-weight: 600; }
.view-grid-wrap { max-height: 46vh; overflow: auto; border: 1px solid #dbe4ee; border-radius: 8px; }
.view-grid-wrap.tall { max-height: 40vh; }
.view-grid th { position: sticky; top: 0; z-index: 1; }
/* 编辑 */
.edit-head { display: flex; flex-wrap: wrap; gap: 10px 14px; padding-bottom: 10px; align-items: center; }
.edit-head label.hd { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #44586c; }
.edit-head .bom-input { min-width: 0; }
.edit-head .lbl { cursor: default; user-select: none; white-space: nowrap; display: inline-flex; align-items: center; gap: 3px; }
.edit-head .lbl:hover { color: #2f6fd0; }
.edit-head .x, .edit-grid th .x { border: none; background: transparent; color: #c05656; cursor: pointer; font-size: 11px; padding: 0 2px; }
.edit-head .x:hover, .edit-grid th .x:hover { color: #e05252; }
.edit-toolbar { display: flex; align-items: center; gap: 8px; padding-bottom: 8px; }
.edit-toolbar .hint { font-size: 12px; color: #9aa7b5; }
.paste-area { width: 100%; height: 84px; border: 1px dashed #2f6fd0; border-radius: 8px; padding: 8px 10px; font-size: 13px; margin-bottom: 8px; box-sizing: border-box; resize: vertical; }
.edit-grid td { padding: 2px 4px; }
.edit-grid tr.sel td { background: #e8f1fc; }
.edit-grid input { width: 100%; border: 1px solid transparent; background: transparent; padding: 5px 6px; font-size: 13px; border-radius: 4px; outline: none; box-sizing: border-box; }
.edit-grid input:hover { border-color: #c9d6e4; }
.edit-grid input:focus { border-color: #2f6fd0; background: #fff; }
.edit-grid th { white-space: nowrap; }
.edit-grid th.addcol { width: 64px; }
</style>
