/** 界面主题：white 白色 / green 绿色 / blue 蓝青(默认，原版配色) */
const KEY = 'wms_theme'
export const THEMES = [
  { key: 'white', label: '蓝色主题', sw: 'linear-gradient(135deg,#eff5fe,#2f6fd0)' },
  { key: 'green', label: '绿色主题', sw: 'linear-gradient(135deg,#d9f0e0,#2e8f5e)' },
  { key: 'blue',  label: '蓝青主题', sw: 'linear-gradient(135deg,#cfe9f2,#2e8ba0)' },
]

export function currentTheme() {
  const t = localStorage.getItem(KEY)
  return THEMES.some(x => x.key === t) ? t : 'blue'
}

export function applyTheme(t) {
  if (!THEMES.some(x => x.key === t)) t = 'blue'
  document.documentElement.dataset.theme = t
  localStorage.setItem(KEY, t)
}

export function initTheme() {
  applyTheme(currentTheme())
}
