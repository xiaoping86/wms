/**
 * Excel 式表格列宽 + 表格横向宽度拖拽（全局生效，无需在组件里登记）。
 * 在 main.js 调用一次 initColResize()：
 *
 * 纵向（列宽）拖拽：
 * - 任意含 thead 的 HTML 表格，鼠标移到表头单元格右缘约 8px 内出现 col-resize 光标；
 * - 按住左右拖动即可拉宽/拉窄该列；
 * - 首次拖动把各列宽度固化为 <colgroup>（table-layout: fixed），列宽精确可见；
 * - 列宽持久化到【服务器】（按当前登录用户），下次打开自动恢复，不存浏览器；
 *   表格需带 data-grid-key 属性（每个表格唯一），如 data-grid-key="doc"。
 *
 * 横向（表格宽度）拖拽：
 * - 表格右下角自动插入 .ku-h-resize 手柄（8px 热区，ew-resize 光标）；
 * - 按住左右拖动改变 table.style.width（px），超出父容器即触发横向滚动条；
 * - 表格宽度同样持久化到服务器 grid-layout 接口的 width 字段。
 *
 * 通用限制：
 * - 不支持含 colspan 表头的表格（跳过），避免列错位；
 * - 跳过 Element Plus 内部表格（.el-table）：它自带 colgroup 且自行管理布局，
 *   再插入一个 colgroup 会导致列整体错位，因此不接管。
 */
import api from '../api'

const EDGE        = 8       // 表头右缘热区宽度（px）
const MIN_W       = 36      // 列最小宽度（px）
const MIN_TABLE_W = 120    // 表格横向拖拽最小宽度（px）

let drag    = null            // 列宽拖拽状态 { x, w, col, table }
let hDrag   = null            // 表格横向宽度拖拽状态 { x, w, table, handle }
const layoutCache = {}        // gridKey -> { widths: [..], width: number }
const initDone = new WeakSet()   // 表格是否已做过"加载服务器布局"
const touched  = new WeakSet()    // 用户已手动拖拽过的表格，不再用服务器布局覆盖

/* ───────── 基本工具 ───────── */

function usable(table) {
  if (!table || table.tagName !== 'TABLE' || !table.querySelector('thead')) return false
  // Element Plus 表格自带 colgroup 并自行计算布局，插入额外 colgroup 会错位，跳过
  if (table.closest && table.closest('.el-table')) return false
  // 分组/合并表头（colspan/rowspan）已由 columnMap() 支持映射，不再跳过
  return true
}

/**
 * 解析表头（支持分组/合并单元格）：
 * 返回 { n: 总列数, host: [每列"最底层"表头单元格] }。
 * 关键：必须按 HTML 表格模型处理 rowspan 占位——下一行的单元格要从
 * 未被上方 rowspan 覆盖的列开始排，否则子表头会错误映射到前面的列。
 * 后渲染的行覆盖先渲染的行：分组子列映射到子表头 th，
 * rowspan 的普通列映射到自身；因此每一个列边界都是某个 th 的右缘。
 */
function columnMap(table) {
  const rows = Array.from(table.querySelectorAll('thead tr'))
  const occupied = rows.map(() => new Set())   // occupied[r] = 被上方 rowspan 覆盖的列号
  const host = []
  rows.forEach((tr, ri) => {
    let ci = 0
    const skip = () => { while (occupied[ri].has(ci)) ci++ }
    Array.from(tr.children).forEach(th => {
      const cs = th.colSpan || 1
      const rs = th.rowSpan || 1
      skip()
      for (let k = 0; k < cs; k++) {
        host[ci + k] = th
        for (let r2 = ri + 1; r2 < ri + rs; r2++) occupied[r2].add(ci + k)
      }
      ci += cs
    })
  })
  let n = host.length
  for (let i = 1; i < n; i++) if (!host[i]) host[i] = host[i - 1]
  return { n, host }
}

/**
 * 取表格父容器（.scroll）的可用内容宽度（扣除左右内边距），
 * 用于初始列宽铺满计算与横向拖拽时计算最小参考。
 */
function parentWidth(table) {
  let el = table.closest('.scroll') || table.parentElement
  while (el && el.clientWidth <= 0) el = el.parentElement
  if (el && el.clientWidth > 0) {
    const cs = getComputedStyle(el)
    return el.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0)
  }
  return window.innerWidth
}

/**
 * 读取表格当前像素宽度。
 * style.width 为空/''（自适应）时返回 0（表示不锁死）；否则解析数值。
 */
function readTableWidth(table) {
  const s = table.style.width
  if (s === '' || s === undefined || s === '100%') return 0
  return Math.round(parseFloat(s) || table.offsetWidth)
}

/* ───────── colgroup 管理 ───────── */

/**
 * 确保表格存在 xls-cols 的 <colgroup>，并按 widths（或当前实测宽度）固化各列像素宽。
 * 表格宽度不再锁死为列宽求和——保持自适应（style.width 为空 = 100%）。
 * @param {HTMLTableElement} table 目标表格
 * @param {number[]=} widths 可选：按列顺序的像素宽度；缺省时用当前渲染宽度
 * @returns {Element|null} colgroup 元素；表格不可用/无表头行时返回 null
 */
/**
 * 无保存布局时的初始列宽测量：
 * 按表头【文字】实际渲染宽度计算（用 canvas measureText，不受表格 width:100% 的
 * auto 布局挤压影响——空列如「备注」在 auto 布局下会被挤成几像素的细条，
 * 若直接量 getBoundingClientRect 会把错误宽度固化）。
 * 若各列之和小于父容器宽度，则按比例放大铺满容器（与原版视觉一致）。
 */
function measureColumns(table, host) {
  const ctx = document.createElement('canvas').getContext('2d')
  const out = host.map(th => {
    if (!th) return MIN_W
    const cs = getComputedStyle(th)
    ctx.font = [cs.fontStyle, cs.fontWeight, cs.fontSize, cs.fontFamily].join(' ')
    const label = (th.textContent || '').trim()
    const pad = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0)
    // 组件里显式写死的 px 宽度优先（如 BOM 的编号/备注列），
    // 否则只按表头文字测量会把长内容列压窄，导致单元格换行撑高整行。
    const declared = (th.style.width || '').trim()
    const fixed = /px$/.test(declared) ? parseFloat(declared) : 0
    const measured = ctx.measureText(label).width + pad + 26
    return Math.max(MIN_W, Math.round(fixed > 0 ? fixed : measured))
  })
  const sum = out.reduce((a, b) => a + b, 0)
  const pw = parentWidth(table)
  if (sum > 0 && pw > 0 && sum < pw) {
    const k = pw / sum
    let acc = 0
    for (let i = 0; i < out.length; i++) { out[i] = Math.max(MIN_W, Math.round(out[i] * k)); acc += out[i] }
    // 取整差额补到最宽一列，使总和恰好等于容器宽度
    if (out.length) out[out.indexOf(Math.max.apply(null, out))] += (pw - acc)
  }
  return out
}

function buildColgroup(table, widths) {
  if (!usable(table)) return null
  const map = columnMap(table)
  if (!map.n) return null
  // 关键：必须在切换 table-layout:fixed 之前测量各列宽度。
  // 若先插入空 colgroup 再切 fixed，浏览器会把所有列均分表格宽度（窄列瞬间"弹开"），
  // 之后量到的也是弹开后的错误宽度。
  const measured = widths
    ? widths.map(w => Math.max(MIN_W, Math.round(w || 0)))
    : measureColumns(table, map.host)
  let cg = table.querySelector('colgroup.xls-cols')
  if (!cg) {
    cg = document.createElement('colgroup')
    cg.className = 'xls-cols'
    table.insertBefore(cg, table.firstChild)
    table.style.tableLayout = 'fixed'
    table.classList.add('xls-resized')
  }
  cg.innerHTML = ''
  let spec = measured.slice()
  if (widths) {
    // 恢复用户保存的列宽：必须逐像素照搬，绝不再按容器缩放，
    // 否则每次关闭重开都会被拉回容器宽度，用户调的宽度等于没保存。
    // 关闭最后一列"吸收余量"的铺满模式，保证渲染宽度 == 保存宽度。
    table.dataset.xlsFit = '0'
  } else {
    delete table.dataset.xlsFit   // 首次测量：按容器铺满
  }
  spec.forEach(w => {
    const col = document.createElement('col')
    col.dataset.w = Math.max(MIN_W, Math.round(w))   // 用户设定宽度（权威值）
    col.style.width = col.dataset.w + 'px'
    cg.appendChild(col)
  })
  render(table)
  watchTable(table)
  return cg
}

/**
 * 按用户设定宽度（col.dataset.w）渲染 colgroup 与表格宽度。
 *
 * 关键原则：**表格渲染宽度恒等于各列宽度之和**，绝不让浏览器去平摊宽度。
 * table-layout:fixed 下，只要表格实际宽度 ≠ 列宽之和（例如被 CSS min-width:100%
 * 撑到容器宽），浏览器就会把差额按比例分给每一列，于是拖动某一列时连前面的列
 * 都会跟着变宽变窄。这里由 JS 精确控制总宽，拖拽列之前的列宽恒定不变，
 * 之后的列只整体平移，不会出现重分配。
 *
 * 铺满策略：若各列之和小于容器宽度，差额交给【最后一列】吸收（fill 模式），
 * 这样表格始终贴满容器右侧，不会出现右侧空白，同时前面的列依旧不受影响。
 */
function fillMode(table) {
  // 用户用过横向手柄把表格缩得比容器窄时，不再强制铺满
  return table.dataset.xlsFit !== '0'
}

function render(table) {
  const cg = table.querySelector('colgroup.xls-cols')
  if (!cg) return
  const n = cg.children.length
  const spec = Array.from(cg.children).map(c => parseFloat(c.dataset.w) || parseFloat(c.style.width) || MIN_W)
  let rest = 0
  for (let i = 0; i < n - 1; i++) rest += spec[i]
  const pw = fillMode(table) ? parentWidth(table) : 0
  const need = pw - rest
  // 最后一列渲染宽度 = max(用户设定宽度, 容器剩余宽度)
  let last = n ? Math.max(MIN_W, Math.max(spec[n - 1], need)) : 0
  const apply = () => {
    for (let i = 0; i < n - 1; i++) cg.children[i].style.width = spec[i] + 'px'
    if (n) cg.children[n - 1].style.width = last + 'px'
    table.style.width = (rest + last) + 'px'
  }
  apply()
  // 精修：合并边框会让表格实际占用宽度比 style.width 多 1~3px，
  // 那点溢出会把 .scroll 的横向滚动条挤出来，用最后一列吸收掉。
  if (n && pw > 0 && need > MIN_W && spec[n - 1] <= need) {
    const diff = table.offsetWidth - pw
    if (Math.abs(diff) >= 1) { last = Math.max(MIN_W, last - diff); apply() }
  }
}

/**
 * 看门狗：Vue 等框架重渲染表格（切换列、载入数据）时，可能把注入的 colgroup 清掉，
 * 导致列宽"复位"。这里监听表格子节点变化，一旦 colgroup 丢失，立即用缓存宽度重建，
 * 保证"下一次打开/载入单据"列宽都和上次一致。
 */
const _obs = new WeakMap()
function watchTable(table) {
  if (!table || _obs.has(table)) return
  const obs = new MutationObserver(() => {
    if (!table.isConnected) return
    if (table.querySelector('colgroup.xls-cols')) return
    const key = table.dataset.gridKey
    const c = layoutCache[key]
    const n = columnMap(table).n
    // 列数一致才用缓存宽度精确还原；否则按当前渲染宽度重新测量
    const w = (c && c.widths && c.widths.length === n) ? c.widths : undefined
    buildColgroup(table, w)
  })
  obs.observe(table, { childList: true })
  _obs.set(table, obs)
}

/** 取表格当前列宽之和（px） */
function sumWidths(table) {
  const cg = table.querySelector('colgroup.xls-cols')
  if (!cg) return 0
  let s = 0
  Array.from(cg.children).forEach(c => { s += parseFloat(c.style.width) || 0 })
  return s
}

/**
 * 取（必要时创建）表格的 xls-cols colgroup。
 * @param {HTMLTableElement} table 目标表格
 * @returns {Element|null}
 */
function ensureColgroup(table) {
  return table.querySelector('colgroup.xls-cols') || buildColgroup(table)
}

function nearEdge(th, e) {
  const r = th.getBoundingClientRect()
  return r.right - e.clientX <= EDGE && r.right - e.clientX > -4
}

/**
 * 取列宽之和。prefer=true 时取用户设定宽度之差（dataset.w），
 * 否则取渲染宽度（style.width）。
 */
function readWidths(table) {
  const cg = table.querySelector('colgroup.xls-cols')
  if (!cg) return null
  // dataset.w 才是用户真正调好的宽度：最后一列的 style.width 可能被临时拉去吸收铺满余量
  return Array.from(cg.children).map(col => parseFloat(col.dataset.w) || parseFloat(col.style.width) || 0)
}

/** 表格横向手柄 */

/**
 * 取前 n-1 列（即除最后一列外）的宽度之和，用于计算最后一列的铺满余量。
 */
function restWidth(table) {
  const cg = table.querySelector('colgroup.xls-cols')
  if (!cg) return 0
  let s = 0
  for (let i = 0; i < cg.children.length - 1; i++)
    s += parseFloat(cg.children[i].dataset.w) || parseFloat(cg.children[i].style.width) || 0
  return s
}

/**
 * 在表格所属父容器（.scroll 或 parentElement）中插入（或复用）横向拖拽手柄。
 * 手柄 class: .ku-h-resize，带 data-grid-key，宽 8px，cursor: ew-resize。
 * 幂等：同 grid-key 的手柄只插入一次。
 */
function ensureHResize(table) {
  // 用户要求取消表格右下角的横向宽度拖拽竖条；列宽拖拽与持久化保持不变。
  return null
  const key = table.dataset.gridKey
  if (!key) return null
  let container = table.closest('.scroll') || table.parentElement
  if (!container) return null
  let handle = container.querySelector('.ku-h-resize[data-grid-key="' + key + '"]')
  if (!handle) {
    handle = document.createElement('div')
    handle.className = 'ku-h-resize'
    handle.dataset.gridKey = key
    handle.title = '拖动改变表格宽度（双击恢复自适应）'
    handle.addEventListener('mousedown', onHDown, false)
    handle.addEventListener('touchstart', onHTouchStart, { passive: false })
    handle.addEventListener('dblclick', onHDouble, false)
    container.appendChild(handle)
  }
  positionHResize(table, handle)
  return handle
}

/**
 * 将横向手柄定位到表格右下角（紧贴表格右缘、底缘，8px 宽热区）。
 * 手柄是 .scroll 容器的子元素，position:absolute 跟随容器内容一起横向滚动。
 * left = 表格自身渲染宽度 - 8px（表格从容器左缘开始，所以 offsetX ≈ 0）
 */
function positionHResize(table, handle) {
  if (!handle || !table) return
  handle.style.position = 'absolute'
  handle.style.bottom = '0'
  handle.style.right  = 'auto'
  // 表格左缘对齐容器内容左缘（offsetX=0），所以手柄 left = 表格实际渲染宽度 - 8
  const tw = table.offsetWidth
  handle.style.left = Math.max(0, tw - 8) + 'px'
}

function onHDown(e) {
  if (e.button != null && e.button !== 0) return
  const handle = e.currentTarget
  const key = handle.dataset.gridKey
  const table = document.querySelector('table[data-grid-key="' + key + '"]')
  if (!table) return
  e.preventDefault()
  e.stopPropagation()
  // 记录拖拽起点：当前各列宽度（orig）与列宽之和，后续按整体比例缩放
  const orig = readWidths(table) || []
  const startW = orig.reduce((a, b) => a + b, 0) || table.offsetWidth
  hDrag = { x: e.clientX, w: startW, table, handle, orig }
  document.body.classList.add('ku-h-resizing')
  window.addEventListener('mousemove', onHMouseMove, false)
  window.addEventListener('mouseup', onHUp, false)
}

function onHTouchStart(e) {
  e.preventDefault()
  const handle = e.currentTarget
  const key = handle.dataset.gridKey
  const table = document.querySelector('table[data-grid-key="' + key + '"]')
  if (!table) return
  const tx = e.touches[0].clientX
  const orig = readWidths(table) || []
  const startW = orig.reduce((a, b) => a + b, 0) || table.offsetWidth
  hDrag = { x: tx, w: startW, table, handle, orig }
  document.body.classList.add('ku-h-resizing')
  window.addEventListener('touchmove', onHTouchMove, { passive: false })
  window.addEventListener('touchend', onHUp, false)
}

// 横向手柄：整体缩放所有列（表格变宽/变窄），不是重新分配剩余空间
function scaleColumns(table, orig, factor) {
  const cg = table.querySelector('colgroup.xls-cols')
  if (!cg) return
  Array.from(cg.children).forEach((c, i) => {
    const ow = (orig && orig[i]) || parseFloat(c.dataset.w) || parseFloat(c.style.width) || 0
    const w = Math.max(MIN_W, Math.round(ow * factor))
    c.dataset.w = w                 // 缩放结果即新的用户设定宽度
    c.style.width = w + 'px'
  })
}

function onHMouseMove(e) {
  if (!hDrag) return
  const newW = Math.max(MIN_TABLE_W, hDrag.w + (e.clientX - hDrag.x))
  const factor = hDrag.w ? newW / hDrag.w : 1
  scaleColumns(hDrag.table, hDrag.orig, factor)
  setFitFlag(hDrag.table, newW)
  hDrag.table.style.width = newW + 'px'
  positionHResize(hDrag.table, hDrag.handle)
}

/** 表格被横向缩到比容器窄时，取消铺满，避免最后一列被重新拉长填回去 */
function setFitFlag(table, total) {
  table.dataset.xlsFit = (total < parentWidth(table) - 1) ? '0' : '1'
}

function onHTouchMove(e) {
  if (!hDrag) return
  const tx = e.touches[0].clientX
  const newW = Math.max(MIN_TABLE_W, hDrag.w + (tx - hDrag.x))
  const factor = hDrag.w ? newW / hDrag.w : 1
  scaleColumns(hDrag.table, hDrag.orig, factor)
  setFitFlag(hDrag.table, newW)
  hDrag.table.style.width = newW + 'px'
  positionHResize(hDrag.table, hDrag.handle)
  e.preventDefault()
}

async function onHUp() {
  if (!hDrag) return
  const table = hDrag.table
  const key = table.dataset.gridKey
  hDrag = null
  document.body.classList.remove('ku-h-resizing')
  window.removeEventListener('mousemove', onHMouseMove)
  window.removeEventListener('mouseup', onHUp)
  window.removeEventListener('touchmove', onHTouchMove)
  window.removeEventListener('touchend', onHUp)
  window.dispatchEvent(new Event('resize'))
  if (key) {
    touched.add(table)
    const widths = readWidths(table) || []
    const width = readTableWidth(table)
    layoutCache[key] = { widths, width }
    try { await api.put('grid-layout', { grid: key, widths, width }) } catch (e) {}
  }
}

/** 双击手柄：把表格整体缩放至恰好铺满父容器宽度（fit），并同步持久化 */
async function onHDouble(e) {
  e.preventDefault()
  const handle = e.currentTarget
  const key = handle.dataset.gridKey
  const table = document.querySelector('table[data-grid-key="' + key + '"]')
  if (!table) return
  const sum = sumWidths(table) || 1
  const target = parentWidth(table)
  delete table.dataset.xlsFit            // 双击恢复铺满
  scaleColumns(table, readWidths(table), target / sum)
  render(table)
  positionHResize(table, handle)
  window.dispatchEvent(new Event('resize'))
  if (key) {
    const widths = readWidths(table) || []
    layoutCache[key] = { widths, width: sumWidths(table) }
    try { await api.put('grid-layout', { grid: key, widths, width: sumWidths(table) }) } catch (e) {}
  }
}

/* ───────── 服务器布局加载 ───────── */

/**
 * 按保存的 widths 恢复列宽——但必须与当前表头列数一致才套用。
 * 列数不一致（如不同单据类型列数不同）时按表头重新测量，
 * 否则 fixed 布局下多出的列会分到 0 宽、表头文字溢出到表格外。
 */
function buildIfCountMatches(table, widths) {
  if (widths && widths.length) {
    const n = columnMap(table).n
    if (widths.length === n) { buildColgroup(table, widths); return }
  }
  buildColgroup(table)  // 列数不符或缺省：按表头重新测量
}

async function applySaved(table) {
  const key = table.dataset.gridKey
  if (!key || initDone.has(table)) return
  initDone.add(table)
  if (touched.has(table)) { ensureHResize(table); return }

  // 命中内存缓存
  if (layoutCache[key]) {
    const c = layoutCache[key]
    buildIfCountMatches(table, c.widths)
    ensureHResize(table)
    return
  }

  try {
    const res = await api.get('grid-layout?grid=' + encodeURIComponent(key))
    if (res && res.widths && res.widths.length) {
      layoutCache[key] = { widths: res.widths, width: res.width || 0 }
      if (!touched.has(table)) buildIfCountMatches(table, res.widths)
    } else {
      layoutCache[key] = { widths: [], width: 0 }
      if (!table.querySelector('colgroup.xls-cols')) buildColgroup(table)
    }
  } catch (e) {
    // 接口失败（未登录/网络异常）也先按测量固化列宽，保证初始视图正常且可拖拽
    if (!table.querySelector('colgroup.xls-cols')) buildColgroup(table)
  } finally {
    ensureHResize(table)
  }
}

/* ───────── 列宽拖拽事件（纵向） ───────── */

function onMove(e) {
  if (hDrag) return  // 横向拖拽中不响应列宽拖拽
  if (drag) {
    const w = Math.max(MIN_W, drag.w + (e.clientX - drag.x))
    drag.col.dataset.w = w            // 用户设定宽度
    // 拖的是最后一列时，若已被拖得比"铺满所需宽度"还窄，就取消铺满，
    // 否则会被容器余量重新拉回去，看起来像拖不动
    if (drag.last || drag.col === drag.col.parentNode.lastElementChild) setFitFlag(drag.table, w + restWidth(drag.table))
    // 只改当前列：前面各列宽度恒定，后面各列仅整体平移
    render(drag.table)
    return
  }  const th = e.target && e.target.closest ? e.target.closest('th') : null
  if (!th) { document.body.classList.remove('ku-col-hot'); return }
  const table = th.closest('table')
  if (usable(table) && nearEdge(th, e)) document.body.classList.add('ku-col-hot')
  else document.body.classList.remove('ku-col-hot')
}

async function onUp() {
  if (hDrag) return  // 横向拖拽结束时不经过这里
  if (!drag) return
  const table = drag.table
  const key = table.dataset.gridKey
  drag = null
  document.body.classList.remove('ku-col-resizing')
  window.dispatchEvent(new Event('resize'))
  if (key) {
    touched.add(table)
    const widths = readWidths(table) || []
    const width = readTableWidth(table)  // 0 表示自适应（未锁死）
    layoutCache[key] = { widths, width }
    try { await api.put('grid-layout', { grid: key, widths, width }) } catch (e) {}
  }
}

function onDown(e) {
  if (e.button != null && e.button !== 0) return
  if (hDrag) return  // 横向拖拽中不响应列宽拖拽
  const th = e.target && e.target.closest ? e.target.closest('th') : null
  if (!th) return
  const table = th.closest('table')
  if (!usable(table) || !nearEdge(th, e)) return
  e.preventDefault()
  e.stopPropagation()
  const cg = ensureColgroup(table)
  if (!cg) return
  // 首次拖拽时把当前渲染宽度固化为设定宽度并关闭铺满模式：
  // 这样用户看到多少就保存多少，下次打开逐像素还原，不会被最后一列重新吸收余量。
  if (fillMode(table)) {
    Array.from(cg.children).forEach(c => { c.dataset.w = parseFloat(c.style.width) || parseFloat(c.dataset.w) || MIN_W })
    table.dataset.xlsFit = '0'
  }
  // 分组/合并表头：th 右缘 = 它覆盖的【最后一列】的右边界，故拖拽映射到最后一列
  const { host } = columnMap(table)
  let idx = -1
  for (let i = 0; i < host.length; i++) if (host[i] === th) idx = i
  const col = cg.children[idx]
  if (!col) return
  // 起点用【渲染宽度】：最后一列可能正被临时拉长用于铺满，从渲染宽度起拖才不会跳
  drag = { x: e.clientX, w: parseFloat(col.style.width) || parseFloat(col.dataset.w) || th.offsetWidth, col, table, last: idx === cg.children.length - 1 }
  document.body.classList.add('ku-col-resizing')
}

/* ───────── 扫描与初始化 ───────── */

function scanTables(root) {
  if (!root || !root.querySelectorAll) return
  root.querySelectorAll('table[data-grid-key]').forEach(t => { if (usable(t)) applySaved(t) })
}

let _inited = false
export function initColResize() {
  if (_inited) return
  _inited = true
  document.addEventListener('mousemove', onMove, true)
  document.addEventListener('mousedown', onDown, true)
  document.addEventListener('mouseup', onUp, true)
  // 表格首次出现即从其服务器布局恢复列宽和横向宽度
  const mo = new MutationObserver(muts => {
    for (const m of muts) {
      for (const n of m.addedNodes) {
        if (!(n instanceof HTMLElement)) continue
        if (n.matches && n.matches('table[data-grid-key]') && usable(n)) applySaved(n)
        scanTables(n)
      }
    }
  })
  mo.observe(document.body, { childList: true, subtree: true })
  // 初始化前已存在于 DOM 的表格（例如路由首屏直接渲染）也补一次回读
  if (document.body) scanTables(document.body)
}
