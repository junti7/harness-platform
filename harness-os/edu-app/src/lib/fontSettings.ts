export const FONT_SCALE_STORAGE_KEY = 'vp_font_scale'

export const DEFAULT_FONT_SCALE = 1
export const MIN_FONT_SCALE = 1
export const MAX_FONT_SCALE = 1.4
export const FONT_SCALE_STEP = 0.05

export function normalizeFontScale(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n)) return DEFAULT_FONT_SCALE
  return Math.min(MAX_FONT_SCALE, Math.max(MIN_FONT_SCALE, Math.round(n / FONT_SCALE_STEP) * FONT_SCALE_STEP))
}

export function loadFontScale(): number {
  try {
    return normalizeFontScale(localStorage.getItem(FONT_SCALE_STORAGE_KEY))
  } catch {
    return DEFAULT_FONT_SCALE
  }
}

export function saveFontScale(scale: number): number {
  const next = normalizeFontScale(scale)
  try {
    localStorage.setItem(FONT_SCALE_STORAGE_KEY, String(next))
  } catch {
    /* ignore */
  }
  applyFontScale(next)
  return next
}

export function applyFontScale(scale: number): number {
  const next = normalizeFontScale(scale)
  const root = document.documentElement
  root.style.setProperty('--edu-font-scale', String(next))
  root.style.fontSize = `${16 * next}px`
  root.dataset.fontScale = String(next)
  return next
}

export function fontScaleLabel(scale: number): string {
  return `${Math.round(normalizeFontScale(scale) * 100)}%`
}
