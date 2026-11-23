/**
 * 全局弹窗八向调整大小。
 *
 * Element Plus 的 el-dialog 会 Teleport 到 body，组件指令无法取得真实弹窗节点，
 * 因此在 main.js 中调用一次 initDialogResize()，通过 MutationObserver 为每个
 * 新出现的 .el-dialog 挂载八个方向的拖拽热区。
 */
const MIN_W = 320
const MIN_H = 200
const VIEWPORT_GAP = 8
const DIRECTIONS = ['n', 's', 'w', 'e', 'nw', 'ne', 'sw', 'se']
const CURSORS = {
  n: 'ns-resize',
  s: 'ns-resize',
  w: 'ew-resize',
  e: 'ew-resize',
  nw: 'nwse-resize',
  se: 'nwse-resize',
  ne: 'nesw-resize',
  sw: 'nesw-resize'
}
const STORE_KEY = 'wms_dialog_sizes'

/* ───── 弹窗尺寸记忆（浏览器本地 UI 偏好，不保存业务数据） ───── */

function loadSizes() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || '{}') || {}
  } catch (e) {
    return {}
  }
}

function saveSize(key, rect) {
  if (!key || !rect || rect.width <= 0 || rect.height <= 0) return
  const all = loadSizes()
  all[key] = { width: Math.round(rect.width), height: Math.round(rect.height) }
  try { localStorage.setItem(STORE_KEY, JSON.stringify(all)) } catch (e) {}
}

function forgetSize(key) {
  if (!key) return
  const all = loadSizes()
  delete all[key]
  try { localStorage.setItem(STORE_KEY, JSON.stringify(all)) } catch (e) {}
}

/** 给弹窗取稳定 key：优先用内部表格的 data-grid-key，其次标题+样式类。 */
function sizeKey(dlg) {
  if (dlg.dataset.kuSizeKey) return dlg.dataset.kuSizeKey
  const grid = dlg.querySelector('[data-grid-key]')?.dataset.gridKey
  const title = dlg.querySelector('.el-dialog__title')?.textContent.trim() || ''
  const cls = Array.from(dlg.classList)
    .filter(c => c !== 'el-dialog' && !c.startsWith('ku-') && !c.startsWith('el-dialog'))
    .join('.')
  dlg.dataset.kuSizeKey = grid ? 'grid:' + grid : 'dlg:' + cls + '|' + title
  return dlg.dataset.kuSizeKey
}

/** 恢复上次拖过的尺寸；只恢复宽高，不锁死位置，仍由 Element Plus 居中。 */
function applySavedSize(dlg, saved) {
  if (!dlg.isConnected || !saved) return
  const maxW = Math.max(MIN_W, window.innerWidth - VIEWPORT_GAP)
  const maxH = Math.max(MIN_H, window.innerHeight - VIEWPORT_GAP)
  const width = clamp(Math.round(saved.width || 0), MIN_W, maxW)
  const height = clamp(Math.round(saved.height || 0), MIN_H, maxH)
  dlg.dataset.kuFixed = '1'
  dlg.style.width = width + 'px'
  dlg.style.height = height + 'px'
  window.dispatchEvent(new Event('resize'))
}

/** 读取鼠标或单指触摸坐标。 */
function getPoint(event) {
  const touch = event.touches && event.touches[0]
  const clientX = event.clientX ?? (touch && touch.clientX)
  const clientY = event.clientY ?? (touch && touch.clientY)
  if (clientX == null || clientY == null) return null
  return { x: clientX, y: clientY }
}

/** 将数值限制在指定范围内。 */
function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

/** 为单个弹窗安装八向拖拽热区。 */
function setup(dlg) {
  if (!dlg || dlg.dataset.kuResized) return
  dlg.dataset.kuResized = '1'

  const key = sizeKey(dlg)
  const saved = loadSizes()[key]
  if (saved && saved.width > 0 && saved.height > 0) {
    // 等 Element Plus 完成一次布局后再套用保存的宽高，避免被默认 width 覆盖。
    requestAnimationFrame(() => applySavedSize(dlg, saved))
  }

  let direction = ''
  let dragging = false
  let startX = 0
  let startY = 0
  let startW = 0
  let startH = 0
  let startLeft = 0
  let startTop = 0

  function onMove(event) {
    if (!dragging) return
    const point = getPoint(event)
    if (!point) return

    const deltaX = point.x - startX
    const deltaY = point.y - startY
    const viewportRight = Math.max(0, window.innerWidth - VIEWPORT_GAP)
    const viewportBottom = Math.max(0, window.innerHeight - VIEWPORT_GAP)
    const resizeWest = direction.includes('w')
    const resizeEast = direction.includes('e')
    const resizeNorth = direction.includes('n')
    const resizeSouth = direction.includes('s')

    if (resizeWest || resizeEast) {
      let newLeft = clamp(startLeft, 0, viewportRight)
      let newWidth = startW

      if (resizeWest) {
        // 左边拖拽时固定右边界；原弹窗小于最小宽度时向右补足。
        const anchoredRight = clamp(Math.max(startLeft + startW, MIN_W), 0, viewportRight)
        const minWidth = Math.min(MIN_W, anchoredRight)
        newLeft = clamp(startLeft + deltaX, 0, anchoredRight - minWidth)
        newWidth = anchoredRight - newLeft
      } else {
        const availableWidth = Math.max(0, viewportRight - newLeft)
        const minWidth = Math.min(MIN_W, availableWidth)
        newWidth = clamp(startW + deltaX, minWidth, availableWidth)
      }

      dlg.style.left = `${newLeft}px`
      dlg.style.width = `${newWidth}px`
    }

    if (resizeNorth || resizeSouth) {
      let newTop = clamp(startTop, 0, viewportBottom)
      let newHeight = startH
      // 小表单弹窗（dlg-fit）：高度不允许超过自然内容高，防止内容下方出现空白。
      const natural = dlg.dataset.kuNatural ? Number(dlg.dataset.kuNatural) : 0

      if (resizeNorth) {
        // 上边拖拽时固定下边界；原弹窗小于最小高度时向下补足。
        const anchoredBottom = clamp(Math.max(startTop + startH, MIN_H), 0, viewportBottom)
        const minHeight = Math.min(MIN_H, anchoredBottom)
        newTop = clamp(startTop + deltaY, 0, anchoredBottom - minHeight)
        newHeight = anchoredBottom - newTop
      } else {
        const availableHeight = Math.max(0, viewportBottom - newTop)
        const minHeight = Math.min(MIN_H, availableHeight)
        newHeight = clamp(startH + deltaY, minHeight, availableHeight)
      }
      if (natural) newHeight = Math.min(newHeight, natural)

      dlg.style.top = `${newTop}px`
      dlg.style.height = `${newHeight}px`
    }

    event.preventDefault && event.preventDefault()
  }

  function removeDragListeners() {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    window.removeEventListener('touchmove', onMove)
    window.removeEventListener('touchend', onUp)
    window.removeEventListener('touchcancel', onUp)
  }

  function onUp() {
    if (!dragging) return
    dragging = false
    document.body.classList.remove('ku-resizing')
    document.body.style.removeProperty('--ku-resize-cursor')
    removeDragListeners()
    saveSize(key, dlg.getBoundingClientRect())
    window.dispatchEvent(new Event('resize'))
  }

  function onDown(event, nextDirection) {
    if (event.button != null && event.button !== 0) return
    const point = getPoint(event)
    if (!point) return

    const rect = dlg.getBoundingClientRect()
    // 首次调整大小时固定当前绝对坐标，避免居中弹窗从两侧同时漂移。
    // kuFixed 只控制内容填充样式；恢复尺寸时已置位但不应锁死位置，故用独立标志。
    dlg.dataset.kuFixed = '1'
    if (!dlg.dataset.kuPosFixed) {
      dlg.dataset.kuPosFixed = '1'
      dlg.style.position = 'absolute'
      dlg.style.margin = '0'
      dlg.style.left = `${Math.max(0, rect.left)}px`
      dlg.style.top = `${Math.max(0, rect.top)}px`
    }
    // 小表单弹窗（dlg-fit）：记录自然内容高度作为拉伸上限，避免往下拉出现大片空白。
    if (dlg.classList.contains('dlg-fit') && !dlg.dataset.kuNatural) {
      dlg.dataset.kuNatural = String(Math.round(rect.height))
    }

    direction = nextDirection
    startX = point.x
    startY = point.y
    startW = rect.width
    startH = rect.height
    startLeft = Math.max(0, rect.left)
    startTop = Math.max(0, rect.top)
    dragging = true

    document.body.classList.add('ku-resizing')
    document.body.style.setProperty('--ku-resize-cursor', CURSORS[direction])
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    window.addEventListener('touchmove', onMove, { passive: false })
    window.addEventListener('touchend', onUp)
    window.addEventListener('touchcancel', onUp)
    event.stopPropagation()
    event.preventDefault && event.preventDefault()
  }

  function resetSize(event) {
    if (dragging) onUp()
    dlg.style.width = ''
    dlg.style.height = ''
    dlg.style.position = ''
    dlg.style.margin = ''
    dlg.style.left = ''
    dlg.style.top = ''
    delete dlg.dataset.kuFixed
    delete dlg.dataset.kuPosFixed
    delete dlg.dataset.kuNatural
    forgetSize(key)
    event.stopPropagation()
    window.dispatchEvent(new Event('resize'))
  }

  DIRECTIONS.forEach((handleDirection) => {
    const handle = document.createElement('div')
    handle.className = `ku-resize-handle ku-resize-${handleDirection}`
    if (handleDirection === 'se') handle.classList.add('ku-resizer')
    handle.dataset.direction = handleDirection
    handle.title = '拖动改变窗口大小（双击恢复默认）'
    handle.setAttribute('aria-hidden', 'true')
    handle.addEventListener('mousedown', (event) => onDown(event, handleDirection))
    handle.addEventListener('touchstart', (event) => onDown(event, handleDirection), { passive: false })
    handle.addEventListener('dblclick', resetSize)
    dlg.appendChild(handle)
  })
}

let _inited = false

/** 初始化全局弹窗调整大小能力，仅执行一次。 */
export function initDialogResize() {
  if (_inited) return
  _inited = true

  const scan = () => {
    document.querySelectorAll('.el-dialog:not([data-ku-resized])').forEach(setup)
  }

  scan()
  const observer = new MutationObserver(scan)
  observer.observe(document.body, { childList: true, subtree: true })
}
