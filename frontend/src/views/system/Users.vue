<template>
  <div class="users-window" :class="{ embedded }">
    <div v-if="!embedded" class="win-titlebar"><span>账号权限</span><span class="win-x" @click="goHome">×</span></div>
    <div class="win-body">
      <table class="u-table" data-grid-key="users">
        <thead>
          <tr><th>账号</th><th>姓名</th><th>职务</th><th>启用</th><th>备注</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in paged" :key="r.id" :class="{ sel: selId === r.id }" @click="selId = r.id">
            <td>{{ r.username }}</td>
            <td>{{ r.name }}</td>
            <td>{{ r.title }}</td>
            <td>{{ r.enabled === 0 ? '否' : '是' }}</td>
            <td>{{ r.remark }}</td>
          </tr>
          <tr v-if="!rows.length"><td colspan="5" class="empty">暂无账号</td></tr>
        </tbody>
      </table>
      <div class="pager">
        <span>每页{{ pageSize }}行</span>
        <span class="pager-right">
          第{{ page }}页 / 共{{ totalPages }}页
          <a @click="page = 1">首页</a><a @click="page = Math.max(1, page-1)">上页</a>
          <a @click="page = Math.min(totalPages, page+1)">下页</a><a @click="page = totalPages">尾页</a>
        </span>
      </div>
      <div class="toolbar">
        <input class="ku-input" v-model="keyword" placeholder="模糊搜索" />
        <button class="ku-btn sq" title="查询" @click="page = 1">🔍</button>
        <button class="ku-btn sq" title="清空" @click="keyword = ''">✕</button>
        <button class="ku-btn" @click="openCreate">添加</button>
        <button class="ku-btn" :disabled="!selRow" @click="del">删除</button>
        <button class="ku-btn" :disabled="!selRow" @click="openEdit(selRow)">编辑</button>
      </div>
    </div>

    <el-dialog draggable overflow class="win-dlg" v-model="visible" :title="editing ? '编辑账号' : '添加账号'" width="660px" append-to-body>
      <el-form :model="form" label-width="64px" size="default">
        <el-row :gutter="18">
          <el-col :span="12">
            <el-form-item label="账号"><el-input v-model="form.username" :disabled="editing" /></el-form-item>
            <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="editing ? '密码' : '密码'">
              <el-input v-model="form.password" type="password" show-password
                        :placeholder="editing ? '留空则不修改密码' : ''" />
            </el-form-item>
            <el-form-item label="职务"><el-input v-model="form.title" /></el-form-item>
            <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
          </el-col>
        </el-row>
        <div class="perm-box">
          <el-tree ref="treeRef" :data="permTree" node-key="key" show-checkbox default-expand-all
                   :props="{ label: 'label', children: 'children' }" :disabled="form.role === 'admin'"
                   style="height:220px;overflow:auto" />
        </div>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" @click="save">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import { PERM_ITEMS } from '../../perm'

const router = useRouter()
const props = defineProps({ embedded: Boolean })
const emit = defineEmits(['close'])
const rows = ref([])
const selId = ref(null)
const keyword = ref('')
const page = ref(1)
const pageSize = 10
const visible = ref(false)
const editing = ref(false)
const form = reactive({})
const treeRef = ref(null)

// 操作权限树：根节点 + 各功能项（与原版一致）
const permTree = [{ key: 'root', label: '操作权限', children: PERM_ITEMS }]
const ALL_KEYS = PERM_ITEMS.map(p => p.key)

const filtered = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return rows.value
  return rows.value.filter(r => (r.username || '').toLowerCase().includes(k) || (r.name || '').includes(k))
})
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const selRow = computed(() => rows.value.find(r => r.id === selId.value))

async function load() {
  try { rows.value = await api.list('users') } catch (e) { ElMessage.error(e.message) }
}
onMounted(load)

function openCreate() {
  editing.value = false
  Object.assign(form, { username: '', password: '', name: '', title: '', role: 'user', enabled: true, remark: '', permissions: [] })
  visible.value = true
  nextTick(() => treeRef.value && treeRef.value.setCheckedKeys([...ALL_KEYS]))
}
function openEdit(r) {
  if (!r) return
  editing.value = true
  Object.assign(form, { id: r.id, username: r.username, password: '', name: r.name || '', title: r.title || '',
                        role: r.role, enabled: r.enabled !== 0, remark: r.remark || '', permissions: r.permissions || [] })
  visible.value = true
  nextTick(() => treeRef.value && treeRef.value.setCheckedKeys(r.role === 'admin' ? [...ALL_KEYS] : [...(r.permissions || [])]))
}
async function save() {
  try {
    const perms = form.role === 'admin'
      ? ALL_KEYS
      : (treeRef.value ? treeRef.value.getCheckedKeys().filter(k => k !== 'root') : [])
    if (editing.value) {
      const d = { name: form.name, title: form.title, enabled: form.enabled, remark: form.remark, permissions: perms }
      if (form.password) d.password = form.password
      await api.update('users', form.id, d)
    } else {
      if (!form.username || !form.password) { ElMessage.warning('账号和密码不能为空'); return }
      await api.create('users', { username: form.username, password: form.password, name: form.name,
                                  title: form.title, enabled: form.enabled, remark: form.remark,
                                  role: 'user', permissions: perms })
    }
    ElMessage.success('已保存'); visible.value = false; load()
  } catch (e) { ElMessage.error(e.message) }
}
async function del() {
  const r = selRow.value
  if (!r) return
  if (r.role === 'admin') { ElMessage.warning('管理员账号不可删除'); return }
  await ElMessageBox.confirm(`确认删除账号「${r.username}」？`, '提示', { type: 'warning' }).catch(() => Promise.reject())
  try { await api.remove('users', r.id); ElMessage.success('已删除'); selId.value = null; load() } catch (e) { ElMessage.error(e.message) }
}
function goHome() {
  if (props.embedded) emit('close')
  else router.push('/home')
}
</script>

<style scoped>
.users-window {
  max-width: 640px; margin: 10px auto; background: var(--ku-panel-soft); border: 1px solid var(--ku-border);
  box-shadow: 0 4px 18px rgba(0,0,0,.18); display: flex; flex-direction: column;
  min-height: calc(100vh - 140px); font-family: "Microsoft YaHei", sans-serif;
}
.users-window.embedded { max-width: none; margin: 0; min-height: auto; border: none; box-shadow: none; background: transparent; }
.win-titlebar {
  height: 32px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 12px; background: var(--ku-panel-2); border-bottom: 1px solid var(--ku-border-soft); font-size: 14px; color: var(--ku-text-soft);
}
.win-x { font-size: 20px; color: #666; cursor: pointer; line-height: 1; }
.win-body { flex: 1; padding: 12px; display: flex; flex-direction: column; }
.u-table { width: 100%; border-collapse: collapse; background: #fff; flex: 1; }
.u-table th {
  background: var(--ku-head); color: var(--ku-text); font-size: 14px; padding: 9px 10px; text-align: left;
  border: 1px solid var(--ku-border); font-weight: 600;
}
.u-table td { border: 1px solid var(--ku-border); padding: 9px 10px; font-size: 14px; color: #333; }
.u-table tbody tr { cursor: pointer; }
.u-table tbody tr.sel { background: var(--ku-sel); }
.u-table tbody tr:hover { background: var(--ku-hover); }
.empty { text-align: center; color: #999; }
.pager {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 4px; font-size: 13px; color: #456;
  border-top: 1px solid #cfe4ec; background: #f4fafc;
}
.pager-right a { margin-left: 10px; color: var(--ku-accent); cursor: pointer; }
.toolbar { display: flex; justify-content: center; gap: 10px; padding: 12px 0 4px; }
.perm-box { border: 1px solid var(--ku-border-soft); background: #fff; border-radius: 4px; padding: 6px; }
.win-foot {
  padding: 8px 12px; font-size: 12px; color: var(--ku-muted);
  background: var(--ku-panel-2); border-top: 1px solid var(--ku-border-soft);
}
</style>
