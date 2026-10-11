<template>
  <div class="profile-window" :class="{ embedded }">
    <div v-if="!embedded" class="win-titlebar"><span>个人设置</span><span class="win-x" @click="goHome">×</span></div>
    <div class="win-body">
      <div class="form-row">
        <label>账号：</label>
        <el-input v-model="username" disabled />
      </div>
      <div class="form-row">
        <label>原密码：</label>
        <el-input v-model="oldPwd" type="password" show-password placeholder="修改密码则需输入" />
      </div>
      <div class="form-row">
        <label>新密码：</label>
        <el-input v-model="newPwd" type="password" show-password placeholder="留空则不修改密码" />
      </div>
      <div class="form-row">
        <label>名称：</label>
        <el-input v-model="name" />
      </div>
      <div class="form-row">
        <label>职务：</label>
        <el-input v-model="title" />
      </div>
      <div class="btn-row">
        <el-button type="warning" plain @click="logout">注 销</el-button>
        <el-button type="primary" style="background:var(--ku-accent);border-color:var(--ku-accent)" :loading="saving" @click="save">保 存</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { logout as clearPerms } from '../../perm'

const props = defineProps({ embedded: Boolean })
const emit = defineEmits(['close'])
const router = useRouter()
const username = ref('')
const oldPwd = ref('')
const newPwd = ref('')
const name = ref('')
const title = ref('')
const saving = ref(false)

onMounted(async () => {
  try {
    const me = await api.me()
    username.value = me.username
    name.value = me.name || ''
    title.value = me.title || ''
  } catch (e) {}
})

async function save() {
  if (newPwd.value && !oldPwd.value) {
    ElMessage.warning('修改密码需先输入原密码')
    return
  }
  saving.value = true
  try {
    await api.raw.put('/auth/profile', {
      name: name.value, title: title.value,
      old_password: oldPwd.value || null, new_password: newPwd.value || null,
    })
    ElMessage.success('已保存')
    oldPwd.value = ''; newPwd.value = ''
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}

function logout() {
  api.setToken('')
  clearPerms()
  router.push('/login')
}

function goHome() {
  if (props.embedded) emit('close')
  else router.push('/home')
}
</script>

<style scoped>
.profile-window {
  width: 420px; margin: 24px auto; background: var(--ku-panel-soft); border: 1px solid var(--ku-border);
  box-shadow: 0 4px 18px rgba(0,0,0,.18); font-family: "Microsoft YaHei", sans-serif;
}
.profile-window.embedded { width: auto; margin: 0; border: none; box-shadow: none; background: transparent; }
.win-titlebar {
  height: 32px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 12px; background: var(--ku-panel-2); border-bottom: 1px solid var(--ku-border-soft); font-size: 14px; color: var(--ku-text-soft);
}
.win-x { font-size: 20px; color: #666; cursor: pointer; line-height: 1; }
.win-body { padding: 26px 30px 18px; }
.form-row { display: flex; align-items: center; margin-bottom: 16px; }
.form-row label { width: 72px; font-size: 14px; color: #333; }
.btn-row { display: flex; justify-content: space-between; margin-top: 22px; }
.win-foot {
  padding: 8px 12px; font-size: 12px; color: var(--ku-muted);
  background: var(--ku-panel-2); border-top: 1px solid var(--ku-border-soft);
}
</style>
