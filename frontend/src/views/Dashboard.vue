<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="6" v-for="c in cards" :key="c.label">
        <el-card shadow="hover">
          <div style="color:#888;font-size:13px">{{ c.label }}</div>
          <div style="font-size:26px;font-weight:700;margin-top:6px">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:16px" header="库存预警（低 / 无库位）">
      <el-table :data="alerts" stripe height="320">
        <el-table-column prop="code" label="编码" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="warehouse_name" label="仓库" />
        <el-table-column prop="location_name" label="库位" />
        <el-table-column prop="qty" label="数量" />
        <el-table-column prop="status" label="状态">
          <template #default="{row}"><el-tag :type="row.status==='低'?'danger':'warning'">{{ row.status }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const cards = ref([])
const alerts = ref([])

onMounted(async () => {
  const [goods, inv] = await Promise.all([
    api.list('goods'),
    api.list('inventory'),
  ])
  const low = inv.filter(x => x.status === '低' || x.status === '无库位')
  cards.value = [
    { label: '货物种类', value: goods.length },
    { label: '库存记录', value: inv.length },
    { label: '预警条目', value: low.length },
    { label: '当前日期', value: new Date().toLocaleDateString('zh-CN') },
  ]
  alerts.value = low
})
</script>
