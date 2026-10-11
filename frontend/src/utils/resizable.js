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
    window.dispatchEvent(new Event('resize'))
  }

  function onDown(event, nextDirection) {
    if (event.button != null && event.button !== 0) return
    const point = getPoint(event)
    if (!point) return

    const rect = dlg.getBoundingClientRect()
    // 首次调整大小时固定当前绝对坐标，避免居中弹窗从两侧同时漂移。
    if (!dlg.dataset.kuFixed) {
      dlg.dataset.kuFixed = '1'
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
    delete dlg.dataset.kuNatural
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
