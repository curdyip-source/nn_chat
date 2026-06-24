// Порт BusinessDocumentColors.statusColor из iOS-приложения, чтобы веб и приложение
// рисовали один и тот же статус одинаково. Поддержка именованных цветов + #hex,
// fallback — оранжевый.

const FALLBACK = '#f5703f' // Color(red: 0.96, green: 0.44, blue: 0.27)

const NAMED: Record<string, string> = {
  green: '#34c759',
  orange: '#f5703f',
  blue: '#3b82f6',
  red: '#ff453a',
  gray: '#8e8e93',
  grey: '#8e8e93',
}

export function statusColor(raw: string | null | undefined): string {
  if (!raw) return FALLBACK
  const v = raw.trim().toLowerCase()
  if (v in NAMED) return NAMED[v]
  if (/^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(v)) return v
  return FALLBACK
}
