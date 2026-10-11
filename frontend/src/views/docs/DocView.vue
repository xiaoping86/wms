<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:12px">
        <h3 style="margin:0">{{ cfg.title }}</h3>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增单据</el-button>
      </div>
      <el-table :data="docs" stripe border>
        <el-table-column prop="doc_no" label="单据号" width="160" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column :label="partyLabel" v-if="cfg.party">
          <template #default="{row}">{{ nameOf(cfg.party.ref, row[cfg.party.key]) }}</template>
        </el-table-column>
        <el-table-column v-if="cfg.wh" :label="cfg.wh.label">
          <template #default="{row}">{{ nameOf('warehouses', row[cfg.wh.key]) }}</template>
        </el-table-column>
        <el-table-column v-if="cfg.wh2" :label="cfg.wh2.label">
          <template #default="{row}">{{ nameOf('warehouses', row[cfg.wh2.key]) }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="经手人" />
        <el-table-column prop="remark" label="备注" show-overflow-tooltip />
        <el-table-column label="操作" width="150">
          <template #default="{row}">
            <el-button size="small" @click="view(row)">查看</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog draggable overflow class="win-dlg" v-model="visible" :title="(detailMode?'查看':'新增')+cfg.title" width="860px">
      <el-form :model="head" inline label-width="90px">
        <el-form-item label="日期"><el-date-picker v-model="head.date" type="date" value-format="YYYY-MM-DD" :disabled="detailMode" /></el-form-item>
        <el-form-item v-for="h in cfg.header" :key="h.key" :label="h.label">
          <el-select v-if="h.ref" v-model="head[h.key]" placeholder="请选择" :disabled="detailMode" style="width:160px" clearable>
            <el-option v-for="o in options[h.ref]" :key="o.id" :label="o.name" :value="o.id" />
          </el-select>
          <el-input v-else v-model="head[h.key]" :disabled="detailMode" style="width:160px" />
        </el-form-item>
      </el-form>

      <el-table :data="lines" border>
        <el-table-column type="index" label="#" width="50" />
        <el-table-column v-for="l in cfg.lines" :key="l.key" :label="l.label">
          <template #default="{row,$index}">
            <el-select v-if="l.ref" v-model="row[l.key]" :disabled="detailMode" placeholder="选择" style="width:100%" clearable filterable>
              <el-option v-for="o in options[l.ref]" :key="o.id" :label="(o.code?o.code+' ':'')+o.name" :value="o.id" />
            </el-select>
            <span v-else-if="l.computed">{{ computedVal(l, row) }}</span>
            <el-input v-else v-model="row[l.key]" :disabled="detailMode" type="number" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" v-if="!detailMode">
          <template #default="{row}"><el-button size="small" type="danger" @click="lines.splice(lines.indexOf(row),1)">删行</el-button></template>
        </el-table-column>
      </el-table>
      <el-button v-if="!detailMode" style="margin-top:10px" :icon="Plus" @click="addLine">添加行</el-button>

      <template #footer>
        <el-button @click="visible=false">关闭</el-button>
        <el-button v-if="!detailMode" type="primary" @click="save">保存单据</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const DOCS = {
  inbound: {
    title: '入库单', endpoint: 'inbound',
    header: [{ key: 'date', label: '日期' }, { key: 'unit_id', label: '供货单位', ref: 'units' }, { key: 'warehouse_id', label: '仓库', ref: 'warehouses' }, { key: 'operator', label: '经手人' }, { key: 'remark', label: '备注' }],
    party: { key: 'unit_id', ref: 'units' }, wh: { key: 'warehouse_id', label: '仓库' },
    lines: [{ key: 'goods_id', label: '货物', ref: 'goods', required: true }, { key: 'location_id', label: '库位', ref: 'locations' }, { key: 'qty', label: '数量', type: 'number' }, { key: 'price', label: '单价', type: 'number' }],
  },
  outbound: {
    title: '出库单', endpoint: 'outbound',
    header: [{ key: 'date', label: '日期' }, { key: 'unit_id', label: '客户', ref: 'units' }, { key: 'warehouse_id', label: '仓库', ref: 'warehouses' }, { key: 'operator', label: '经手人' }, { key: 'remark', label: '备注' }],
    party: { key: 'unit_id', ref: 'units' }, wh: { key: 'warehouse_id', label: '仓库' },
    lines: [{ key: 'goods_id', label: '货物', ref: 'goods', required: true }, { key: 'location_id', label: '库位', ref: 'locations' }, { key: 'qty', label: '数量', type: 'number' }, { key: 'price', label: '单价', type: 'number' }],
  },
  transfer: {
    title: '调拨单', endpoint: 'transfer',
    header: [{ key: 'date', label: '日期' }, { key: 'from_warehouse_id', label: '调出仓库', ref: 'warehouses' }, { key: 'to_warehouse_id', label: '调入仓库', ref: 'warehouses' }, { key: 'operator', label: '经手人' }, { key: 'remark', label: '备注' }],
    wh: { key: 'from_warehouse_id', label: '调出仓库' }, wh2: { key: 'to_warehouse_id', label: '调入仓库' },
    lines: [{ key: 'goods_id', label: '货物', ref: 'goods', required: true }, { key: 'from_location_id', label: '调出库位', ref: 'locations' }, { key: 'to_location_id', label: '调入库位', ref: 'locations' }, { key: 'qty', label: '数量', type: 'number' }, { key: 'price', label: '单价', type: 'number' }],
  },
  check: {
    title: '盘点单', endpoint: 'check',
    header: [{ key: 'date', label: '日期' }, { key: 'warehouse_id', label: '仓库', ref: 'warehouses' }, { key: 'operator', label: '经手人' }, { key: 'remark', label: '备注' }],
    wh: { key: 'warehouse_id', label: '仓库' },
    lines: [{ key: 'goods_id', label: '货物', ref: 'goods', required: true }, { key: 'location_id', label: '库位', ref: 'locations' }, { key: 'book_qty', label: '账存', type: 'number' }, { key: 'actual_qty', label: '实存', type: 'number' }, { key: 'price', label: '单价', type: 'number' }, { key: 'diff', label: '盈亏', computed: true }],
  },
  initial: {
    title: '期初库存', endpoint: 'initial',
    header: [{ key: 'date', label: '日期' }, { key: 'operator', label: '经手人' }, { key: 'remark', label: '备注' }],
    lines: [{ key: 'goods_id', label: '货物', ref: 'goods', required: true }, { key: 'warehouse_id', label: '仓库', ref: 'warehouses' }, { key: 'location_id', label: '库位', ref: 'locations' }, { key: 'qty', label: '数量', type: 'number' }, { key: 'price', label: '单价', type: 'number' }],
  },
}

const route = useRoute()
const type = ref(route.params.type)
const cfg = ref(DOCS[type.value])
const docs = ref([])
const visible = ref(false)
const detailMode = ref(false)
const head = reactive({})
const lines = ref([])
const options = reactive({})

function nameOf(refKey, id) {
  const list = options[refKey] || []
  const o = list.find(x => x.id === id)
  return o ? o.name : (id || '')
}
function computedVal(l, row) {
  if (l.key === 'diff') return ((Number(row.actual_qty) || 0) - (Number(row.book_qty) || 0))
  return ''
}
async function loadOptions() {
  for (const key of ['goods', 'units', 'warehouses', 'locations']) {
    options[key] = await api.list(key)
  }
}
async function load() {
  docs.value = await api.list(cfg.value.endpoint)
}
function emptyHead() {
  Object.keys(head).forEach(k => delete head[k])
  head.date = new Date().toISOString().slice(0, 10)
  for (const h of cfg.value.header) if (h.ref) head[h.key] = null
}
function addLine() {
  const line = {}
  for (const l of cfg.value.lines) line[l.key] = (l.type === 'number' || l.key === 'qty' || l.key === 'price' || l.key.endsWith('_qty')) ? 0 : null
  lines.value.push(line)
}
function openCreate() {
  detailMode.value = false
  emptyHead(); lines.value = []; addLine()
  visible.value = true
}
async function view(row) {
  detailMode.value = true
  const res = await api.get(cfg.value.endpoint + '/' + row.id)
  Object.keys(head).forEach(k => delete head[k])
  Object.assign(head, res.header)
  lines.value = res.items.map(it => ({ ...it }))
  visible.value = true
}
async function save() {
  const items = lines.value.map(l => {
    const o = {}
    for (const f of cfg.value.lines) o[f.key] = (l[f.key] === '' || l[f.key] == null) ? (f.type === 'number' || f.key.endsWith('_qty') ? 0 : null) : l[f.key]
    return o
  })
  try {
    await api.create(cfg.value.endpoint, { ...head, items })
    ElMessage.success('单据已保存')
    visible.value = false
    load()
  } catch (e) { ElMessage.error(e.message) }
}
async function remove(row) {
  await ElMessageBox.confirm('确认删除该单据？', '提示', { type: 'warning' }).catch(() => Promise.reject())
  try { await api.remove(cfg.value.endpoint, row.id); ElMessage.success('已删除'); load() } catch (e) { ElMessage.error(e.message) }
}
onMounted(() => { loadOptions(); load() })
</script>
