<template>
  <div class="pq-page">
    <!-- 原版风格操作栏 -->
    <div class="ku-toolbar no-print">
      <button class="ku-tb home" @click="$router.push('/home')">&lt;主页</button>
      <button class="ku-tb key" @click="doCheck" :disabled="!bomId || loading">查询</button>
      <button class="ku-tb" @click="doClear">清空</button>
      <button class="ku-tb" @click="doPrint" :disabled="!res">预览</button>
      <button class="ku-tb" @click="doPrint" :disabled="!res">打印</button>
      <span style="flex:1"></span>
      <span v-if="res" class="pq-ftip">{{ res.bom.model }} × {{ res.plan_qty }}</span>
    </div>

    <div class="print-area">
    <!-- 查询条件卡片 -->
    <div class="pq-card no-print">
      <div class="pq-title">产品查询</div>
      <div class="pq-form">
        <label>电机型号
          <select v-model="bomId" class="pq-select">
            <option value="" disabled>请选择型号</option>
            <option v-for="b in boms" :key="b.id" :value="b.id">{{ b.model }}（{{ b.name }}）</option>
          </select>
        </label>
        <label>生产数量
          <input class="pq-input" v-model.number="planQty" type="number" min="1" step="1" />
        </label>
        <button class="pq-btn" :disabled="!bomId || loading" @click="doCheck">查询库存是否足够</button>
      </div>
      <div v-if="!boms.length" class="pq-tip">还没有 BOM，请先在【资料 → BOM】里新建</div>
    </div>

    <!-- 结果 -->
    <template v-if="res">
      <div class="pq-card">
        <div class="pq-sum">
          <span class="pq-bom">{{ res.bom.model }}</span>
          <span>{{ res.bom.name }}</span>
          <span class="sep">|</span><span>生产 {{ res.plan_qty }} 台</span>
          <span class="sep">|</span><span>配件 {{ res.summary.parts }} 项</span>
          <span class="sep">|</span>
          <span v-if="res.summary.unmatched" class="bad">未匹配货物 {{ res.summary.unmatched }} 项</span>
          <span class="sp"></span>
          <span :class="res.summary.enough ? 'good' : 'bad'">
            {{ res.summary.enough ? '✅ 库存充足，可以生产' : '❌ 缺料 ' + res.summary.short + ' 项，不能生产' }}
          </span>
        </div>
        <div class="pq-grid-wrap">
          <table class="pq-grid" data-grid-key="productquery">
            <thead>
              <tr>
                <th style="width:50px">序号</th><th style="width:130px">图号</th><th>名称</th>
                <th style="width:110px">基型</th><th style="width:76px">单台用量</th>
                <th style="width:86px">需求数量</th><th style="width:86px">当前库存</th>
                <th style="width:80px">缺口</th><th style="width:70px">状态</th><th style="width:90px">对应货物</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in res.rows" :key="r.seq" :class="{ lack: !r.ok }">
                <td>{{ r.seq }}</td><td>{{ r.dwg }}</td><td>{{ r.name }}</td><td>{{ r.base }}</td>
                <td>{{ r.per }}</td><td>{{ r.need }}</td>
                <td :class="{ zero: r.stock != null && r.stock <= 0 }">{{ r.stock == null ? '—' : r.stock }}</td>
                <td>{{ r.gap != null && r.gap > 0 ? r.gap : '—' }}</td>
                <td><span :class="r.ok ? 'good' : 'bad'">{{ r.ok ? '✔ 足够' : (r.stock == null ? '✘ 未匹配' : '✘ 不足') }}</span></td>
                <td>{{ r.goods_code || '—' }}</td>
              </tr>
              <tr v-if="!res.rows.length"><td colspan="10" class="empty">该 BOM 没有明细</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const boms = ref([])
const bomId = ref('')
const planQty = ref(1)
const loading = ref(false)
const res = ref(null)

onMounted(async () => {
  try { boms.value = await api.list('boms') } catch (e) { boms.value = [] }
})

async function doCheck() {
  if (!bomId.value) return
  if (!(planQty.value > 0)) return ElMessage.warning('生产数量必须大于 0')
  loading.value = true
  try {
    res.value = await api.list(`boms/${bomId.value}/check`, { qty: planQty.value })
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

/* 原版操作栏：清空 / 预览 / 打印 */
function doClear() {
  res.value = null
  bomId.value = ''
  planQty.value = 1
}
function doPrint() {
  if (!res.value) return ElMessage.info('请先点「查询」出结果再打印')
  window.print()
}
</script>

<style scoped>
.pq-page { padding: 0; }
.pq-ftip { font-size: 12px; color: #eaf7ee; background: rgba(255,255,255,.18); border-radius: 4px; padding: 2px 8px; }
.pq-card { background: #fff; border: 1px solid #dbe4ee; border-radius: 10px; padding: 12px 14px; margin-bottom: 12px; }
.pq-title { color: #1f5fa9; font-weight: 600; font-size: 15px; padding-bottom: 10px; }
.pq-form { display: flex; align-items: flex-end; gap: 18px; flex-wrap: wrap; }
.pq-form label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #44586c; }
.pq-select { width: 260px; border: 1px solid #c9d6e4; border-radius: 6px; padding: 8px 10px; font-size: 13px; background: #fff; outline: none; }
.pq-input { width: 140px; border: 1px solid #c9d6e4; border-radius: 6px; padding: 8px 10px; font-size: 13px; outline: none; }
.pq-select:focus, .pq-input:focus { border-color: #2f6fd0; box-shadow: 0 0 0 2px rgba(47,111,208,.15); }
.pq-btn { background: #2f6fd0; color: #fff; border: none; border-radius: 7px; padding: 10px 22px; font-size: 14px; cursor: pointer; }
.pq-btn:hover { background: #255cab; }
.pq-btn:disabled { background: #a9c1e4; cursor: not-allowed; }
.pq-btn.sm { padding: 5px 14px; font-size: 12px; }
.pq-tip { padding-top: 8px; font-size: 12px; color: #b26a00; }
/* 汇总 */
.pq-sum { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; color: #44586c; padding-bottom: 10px; }
.pq-bom { background: #2f6fd0; color: #fff; border-radius: 5px; padding: 2px 9px; font-weight: 600; }
.pq-sum .sep { color: #c9d6e4; }
.pq-sum .sp { flex: 1; }
.good { color: #1d9e55; font-weight: 600; }
.bad { color: #d64545; font-weight: 600; }
/* 表格 */
.pq-grid-wrap { max-height: 56vh; overflow: auto; border: 1px solid #dbe4ee; border-radius: 8px; }
.pq-grid { width: 100%; border-collapse: collapse; font-size: 13px; }
.pq-grid th { background: #eef4fb; color: #24425f; text-align: left; padding: 7px 9px; border-bottom: 1px solid #dbe4ee; position: sticky; top: 0; z-index: 1; }
.pq-grid td { padding: 7px 9px; border-bottom: 1px solid #edf2f8; color: #2b3a4a; }
.pq-grid tr:hover td { background: #f6f9fd; }
.pq-grid tr.lack td { background: #fdf2f2; }
.pq-grid td.zero { color: #d64545; font-weight: 600; }
.pq-grid td.empty { text-align: center; color: #9aa7b5; padding: 22px 0; }
</style>
