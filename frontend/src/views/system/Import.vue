<template>
  <el-card>
    <h3 style="margin-top:0">批量导入</h3>
    <el-alert type="info" :closable="false" style="margin-bottom:16px">
      支持 CSV 文件导入。首行表头可用中文或英文：<br />
      货物：编码,名称,规格,型号,单位,分类,最低库存,最高库存,入库单价,出库单价<br />
      往来单位：编码,名称,联系人,电话,地址,类型
    </el-alert>
    <el-form inline>
      <el-form-item label="导入类型">
        <el-select v-model="kind" style="width:160px">
          <el-option label="货物资料" value="goods" />
          <el-option label="往来单位" value="units" />
        </el-select>
      </el-form-item>
      <el-upload :auto-upload="false" :show-file-list="true" :on-change="onFile" accept=".csv" style="display:inline-block">
        <el-button :icon="Upload">选择 CSV 文件</el-button>
      </el-upload>
      <el-button type="primary" :disabled="!file" :loading="loading" @click="doImport">开始导入</el-button>
    </el-form>
    <div v-if="result" style="margin-top:12px;color:#666">导入完成：共导入 {{ result.imported }} 条</div>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const kind = ref('goods')
const file = ref(null)
const loading = ref(false)
const result = ref(null)
function onFile(u) { file.value = u.raw }
async function doImport() {
  loading.value = true; result.value = null
  try {
    const fd = new FormData(); fd.append('file', file.value)
    const t = api.getToken()
    const r = await api.raw.post('/import/' + kind.value, fd, { headers: { Authorization: 'Bearer ' + t } })
    result.value = r.data
    ElMessage.success('导入成功')
  } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}
</script>
