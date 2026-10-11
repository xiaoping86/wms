import axios from 'axios'

const TOKEN_KEY = 'wms_token'

// 登录凭证用 sessionStorage：关闭浏览器即清空，下次打开需重新登录（不自动登录）
function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || ''
}
function setToken(t) {
  if (t) sessionStorage.setItem(TOKEN_KEY, t)
  else sessionStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({ baseURL: '/api' })

// 通讯状态：供顶栏指示灯使用（进行中的请求数 > 0 = 正在通讯）
let inflight = 0
function notifyNet() {
  try { window.dispatchEvent(new CustomEvent('wms-net', { detail: { busy: inflight > 0 } })) } catch (e) {}
}
http.interceptors.request.use((cfg) => {
  inflight++; notifyNet()
  const t = getToken()
  if (t) cfg.headers.Authorization = 'Bearer ' + t
  return cfg
})
http.interceptors.response.use(
  (res) => { inflight--; notifyNet(); return res.data },
  (err) => {
    inflight--; notifyNet()
    if (err.response && err.response.status === 401) {
      setToken('')
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    // 统一将常见错误翻译为中文，避免弹英文提示
    const STATUS_CN = {
      400: '请求参数有误', 401: '登录已失效，请重新登录', 403: '没有权限执行此操作',
      404: '接口不存在（请求地址有误）', 405: '请求方式有误（接口地址不正确）',
      409: '数据冲突，请刷新后重试', 413: '文件过大', 422: '提交的数据校验未通过',
      429: '操作过于频繁，请稍后再试', 500: '服务器内部错误', 502: '服务暂不可用', 503: '服务暂不可用', 504: '服务器响应超时',
    }
    const detail = err.response && err.response.data && err.response.data.detail
    let msg
    if (typeof detail === 'string' && detail && !/^https?:|^\s*(Method Not Allowed|Not Found|Internal Server Error|Forbidden|Unauthorized|Bad Request|Unprocessable Entity)/i.test(detail)) {
      msg = detail // 后端返回的中文业务提示，原样使用
    } else {
      msg = STATUS_CN[err.response && err.response.status] || '网络异常，请检查与服务器的连接'
    }
    return Promise.reject(new Error(msg))
  }
)

const api = {
  getToken, setToken,
  login: (username, password) => http.post('/auth/login', { username, password }),
  me: () => http.get('/auth/me'),
  changePwd: (old_password, new_password) => http.post('/auth/change-password', { old_password, new_password }),
  // 规范化：去掉调用方误传的前导斜杠，避免拼出 "//xxx" 被当成协议相对 URL（主机名解析错误）
  list: (url, params) => http.get('/' + String(url || '').replace(/^\/+/, ''), { params }),
  get: (url) => http.get('/' + String(url || '').replace(/^\/+/, '')),
  create: (url, data) => http.post('/' + String(url || '').replace(/^\/+/, ''), data),
  update: (url, id, data) => http.put('/' + String(url || '').replace(/^\/+/, '') + '/' + id, data),
  remove: (url, id) => http.delete('/' + String(url || '').replace(/^\/+/, '') + '/' + id),
  put: (url, data) => http.put('/' + String(url || '').replace(/^\/+/, ''), data),
  post: (url, data) => http.post('/' + String(url || '').replace(/^\/+/, ''), data),
  raw: http,
}

export default api
