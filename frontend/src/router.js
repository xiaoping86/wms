import { createRouter, createWebHashHistory } from 'vue-router'
import api from './api'
import { loadMe, hasPerm } from './perm'
import Login from './views/Login.vue'
import Layout from './views/Layout.vue'
import Home from './views/Home.vue'
import MasterView from './views/master/MasterView.vue'
import DocQuery from './views/docs/DocQuery.vue'
import DocSheet from './views/docs/DocSheet.vue'
import ReportView from './views/reports/ReportView.vue'
import ProductQuery from './views/reports/ProductQuery.vue'
import Users from './views/system/Users.vue'
import Settings from './views/system/Settings.vue'
import Profile from './views/system/Profile.vue'
import Backup from './views/system/Backup.vue'
import ImportData from './views/system/Import.vue'

const routes = [
  { path: '/login', name: 'login', component: Login },
  {
    path: '/', component: Layout, redirect: '/home',
    children: [
      { path: 'home', name: 'home', component: Home, meta: { title: '仓库管理系统' } },
      { path: 'master/:entity', name: 'master', component: MasterView, props: true, meta: { title: '基础资料', perm: p => p.entity } },
      { path: 'doc/:type', name: 'doc', component: DocSheet, props: true, meta: { title: '业务单据', perm: p => p.type } },
      { path: 'docquery', name: 'docquery', component: DocQuery, meta: { title: '单据查询', perm: () => 'docquery' } },
      { path: 'report/:type', name: 'report', component: ReportView, props: true, meta: { title: '报表中心', perm: () => 'reports' } },
      { path: 'productquery', name: 'productquery', component: ProductQuery, meta: { title: '产品查询', perm: () => 'reports' } },
      { path: 'system/users', name: 'users', component: Users, meta: { title: '账号权限', perm: () => 'users' } },
      { path: 'system/settings', name: 'settings', component: Settings, meta: { title: '系统设置', perm: () => 'settings' } },
      { path: 'system/profile', name: 'profile', component: Profile, meta: { title: '个人设置' } },
      { path: 'system/backup', name: 'backup', component: Backup, meta: { title: '备份 / 还原', perm: () => 'data' } },
      { path: 'system/import', name: 'import', component: ImportData, meta: { title: '批量导入', perm: () => 'data' } },
    ],
  },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach(async (to) => {
  const token = api.getToken()
  if (to.path !== '/login' && !token) return '/login'
  if (to.path === '/login' && token) return '/'
  // 路由级操作权限拦截
  if (to.meta && to.meta.perm) {
    await loadMe()
    const params = to.params || {}
    const key = typeof to.meta.perm === 'function' ? to.meta.perm(params) : to.meta.perm
    if (key && !hasPerm(key)) return '/home'
  }
  return true
})

export default router
