<template>
  <div class="logs-wrap">
    <div class="filter-bar">
      <span>日期</span>
      <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" size="small"
        range-separator="至" start-placeholder="开始" end-placeholder="结束" style="width:230px" />
      <span>账号</span>
      <el-select v-model="fuser" size="small" clearable filterable style="width:120px" placeholder="全部">
        <el-option v-for="u in users" :key="u" :label="u" :value="u" />
      </el-select>
      <el-input v-model="q" size="small" clearable placeholder="模块/操作/详情" style="width:160px" @keyup.enter="load" />
      <el-button size="small" type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="load">查询</el-button>
      <span style="flex:1"></span>
      <span class="cnt">共 {{ total }} 条</span>
    </div>

    <table class="l-table" data-grid-key="logs">
      <thead>
        <tr><th style="width:150px">时间</th><th style="width:90px">账号</th><th style="width:110px">模块</th>
            <th style="width:100px">操作</th><th>详情</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in logs" :key="r.id">
          <td>{{ r.time }}</td><td>{{ r.username }}</td><td>{{ r.module }}</td>
          <td>{{ r.action }}</td><td class="dtl">{{ r.detail }}</td>
        </tr>
        <tr v-if="!logs.length"><td colspan="5" class="empty">暂无日志（进行一次数据操作后再来查看）</td></tr>
      </tbody>
    </table>
    <div class="l-foot">仅保存于服务器数据库 · 仅管理员可查看 · 最多显示最近 {{ limit }} 条</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const logs = ref([])
const users = ref([])
const total = ref(0)
const range = ref(null)
const fuser = ref('')
const q = ref('')
const limit = 500

async function load() {
  try {
    const p = { limit }
    if (range.value) { p.start = range.value[0]; p.end = range.value[1] }
    if (fuser.value) p.user = fuser.value
    if (q.value) p.q = q.value
    const d = await api.list('op-logs', p)
    logs.value = d.logs || []
    users.value = d.users || []
    total.value = (d.logs || []).length
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(load)
</script>

<style scoped>
.logs-wrap { font-family: "Microsoft YaHei", sans-serif; }
.filter-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; color: #333; }
.cnt { color: var(--ku-muted); font-size: 13px; }
.l-table { width: 100%; border-collapse: collapse; background: #fff; }
.l-table th { background: var(--ku-head); color: var(--ku-text); font-size: 13px; padding: 7px 9px; border: 1px solid var(--ku-border); text-align: left; font-weight: 600; }
.l-table td { border: 1px solid var(--ku-border); padding: 6px 9px; font-size: 13px; color: #333; }
.dtl { color: #555; }
.empty { text-align: center; color: #999; padding: 20px 0; }
.l-foot { padding: 8px 4px 2px; font-size: 12px; color: var(--ku-muted); text-align: center; }
</style>
