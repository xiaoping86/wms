/** 操作权限：键 -> 显示名（与后端 PERMISSION_TREE 保持一致） */
import api from './api'

export const PERM_ITEMS = [
  { key: 'settings', label: '系统设置' },
  { key: 'users', label: '账号权限' },
  { key: 'data', label: '数据管理' },
  { key: 'personnel', label: '工作人员' },
  { key: 'categories', label: '进出类别' },
  { key: 'warehouses', label: '仓库信息' },
  { key: 'locations', label: '库区库位' },
  { key: 'units', label: '往来单位' },
  { key: 'goods', label: '货物资料' },
  { key: 'goods-categories', label: '货物分类' },
  { key: 'initial', label: '期初库存' },
  { key: 'inbound', label: '入库单' },
  { key: 'outbound', label: '出库单' },
  { key: 'transfer', label: '调拨单' },
  { key: 'check', label: '盘点单' },
  { key: 'docquery', label: '单据查询' },
  { key: 'reports', label: '报表中心' },
]

let myPerms = null
let myRole = null

/** 拉取当前登录用户的权限（登录后/刷新后调用一次） */
export async function loadMe(force = false) {
  if (myPerms !== null && !force) return
  try {
    const me = await api.get('auth/me')
    myRole = me.role
    myPerms = me.role === 'admin' ? PERM_ITEMS.map(p => p.key) : (me.permissions || [])
  } catch (e) {
    myPerms = []
  }
}

/** 登录成功后可直接注入，避免重复请求 */
export function setMe(user) {
  myRole = user ? user.role : null
  myPerms = user
    ? (user.role === 'admin' ? PERM_ITEMS.map(p => p.key) : (user.permissions || []))
    : null
}

export function logout() {
  myPerms = null
  myRole = null
}

/** 是否拥有某项操作权限 */
export function hasPerm(key) {
  if (myRole === 'admin') return true
  if (myPerms === null) return true // 尚未加载完成时先放行
  return myPerms.includes(key)
}
