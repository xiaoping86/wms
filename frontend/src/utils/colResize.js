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
  for (const th of table.querySelectorAll('thead th')) {
    if (th.colSpan > 1) return false  // 横向合并列会改变列索引映射，跳过
  }
  return true
}

// 取叶子（含实际列数最多的）表头行，用于对齐列宽
function leafRow(table) {
  let best = null, n = 0
  table.querySelectorAll('thead tr').forEach(tr => {
    const c = tr.children.length
    if (c > n) { n = c; best = tr }
  })
  return best || table.querySelector('thead tr')
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
function measureColumns(table, ths) {
  const ctx = document.createElement('canvas').getContext('2d')
  const out = ths.map(th => {
    const cs = getComputedStyle(th)
    ctx.font = [cs.fontStyle, cs.fontWeight, cs.fontSize, cs.fontFamily].join(' ')
    const label = (th.textContent || '').trim()
    const pad = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0)
    return Math.max(MIN_W, Math.round(ctx.measureText(label).width + pad + 26))
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
  const row = leafRow(table)
  if (!row) return null
  const ths = Array.from(row.children)
  // 关键：必须在切换 table-layout:fixed 之前测量各列宽度。
  // 若先插入空 colgroup 再切 fixed，浏览器会把所有列均分表格宽度（窄列瞬间"弹开"），
  // 之后量到的也是弹开后的错误宽度。
  const measured = widths
    ? widths.map(w => Math.max(MIN_W, Math.round(w || 0)))
    : measureColumns(table, ths)
  let cg = table.querySelector('colgroup.xls-cols')
  if (!cg) {
    cg = document.createElement('colgroup')
    cg.className = 'xls-cols'
    table.insertBefore(cg, table.firstChild)
    table.style.tableLayout = 'fixed'
    table.classList.add('xls-resized')
  }
  cg.innerHTML = ''
  let sum = 0
  measured.forEach(w => {
    const col = document.createElement('col')
    col.style.width = w + 'px'
    col.dataset.w = w                 // 记录原始宽度，供横向手柄整体缩放使用
    cg.appendChild(col)
    sum += w
  })
  // 表格宽度 = 各列宽度之和（而非 CSS 的 100%）。
  // 这样拖动某一列时只改该列宽度、其余列仅整体平移，不会"牵一发而动全身"。
  table.style.width = sum + 'px'
  watchTable(table)
  return cg
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
    const row = leafRow(table)
    const n = row ? row.children.length : 0
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

function readWidths(table) {
  const cg = table.querySelector('colgroup.xls-cols')
  if (!cg) return null
  return Array.from(cg.children).map(col => parseFloat(col.style.width) || 0)
}

/* ───────── 横向手柄 ───────── */

/**
 * 在表格所属父容器（.scroll 或 parentElement）中插入（或复用）横向拖拽手柄。
 * 手柄 class: .ku-h-resize，带 data-grid-key，宽 8px，cursor: ew-resize。
 * 幂等：同 grid-key 的手柄只插入一次。
 */
function ensureHResize(table) {
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
    const ow = (orig && orig[i]) || parseFloat(c.style.width) || 0
    c.style.width = Math.max(MIN_W, Math.round(ow * factor)) + 'px'
  })
}

function onHMouseMove(e) {
  if (!hDrag) return
  const newW = Math.max(MIN_TABLE_W, hDrag.w + (e.clientX - hDrag.x))
  const factor = hDrag.w ? newW / hDrag.w : 1
  scaleColumns(hDrag.table, hDrag.orig, factor)
  hDrag.table.style.width = newW + 'px'
  positionHResize(hDrag.table, hDrag.handle)
}

function onHTouchMove(e) {
  if (!hDrag) return
  const tx = e.touches[0].clientX
  const newW = Math.max(MIN_TABLE_W, hDrag.w + (tx - hDrag.x))
  const factor = hDrag.w ? newW / hDrag.w : 1
  scaleColumns(hDrag.table, hDrag.orig, factor)
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
  scaleColumns(table, readWidths(table), target / sum)
  table.style.width = sumWidths(table) + 'px'
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
    const row = leafRow(table)
    const n = row ? row.children.length : 0
    if (widths.length === n) { buildColgroup(table, widths); return }
  }
  buildColgroup(table)  // 列数不符或缺省：按表头文字重新测量
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
    drag.col.style.width = w + 'px'
    // 表格总宽跟随各列之和变化：只改当前列，其余列仅平移，不会整体变动
    drag.table.style.width = sumWidths(drag.table) + 'px'
    return
  }
  const th = e.target && e.target.closest ? e.target.closest('th') : null
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
  const idx = Array.from(th.parentElement.children).indexOf(th)
  const col = cg.children[idx]
  if (!col) return
  drag = { x: e.clientX, w: parseFloat(col.style.width) || th.offsetWidth, col, table }
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
