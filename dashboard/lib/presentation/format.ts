import type { FormatType } from './types'

/** Format a value according to the specified format type */
export function formatValue(value: unknown, format?: FormatType): string {
  if (value === null || value === undefined) return '\u2014'

  if (!format) return String(value)

  switch (format) {
    case 'currency_ars': {
      const num = typeof value === 'number' ? value : Number(value)
      if (isNaN(num)) return String(value)
      return `$${num.toLocaleString('es-AR')}`
    }
    case 'currency_usd': {
      const num = typeof value === 'number' ? value : Number(value)
      if (isNaN(num)) return String(value)
      return `USD ${num.toLocaleString('es-AR')}`
    }
    case 'pct': {
      const num = typeof value === 'number' ? value : Number(value)
      if (isNaN(num)) return String(value)
      // If value is between 0 and 1 (exclusive), treat as decimal percentage
      const pct = num > 0 && num < 1 ? Math.round(num * 100) : num
      return `${pct}%`
    }
    case 'date': {
      if (typeof value !== 'string') return String(value)
      const d = new Date(value)
      if (isNaN(d.getTime())) return String(value)
      return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
    }
    case 'datetime_short': {
      if (typeof value !== 'string') return String(value)
      const d = new Date(value)
      if (isNaN(d.getTime())) return String(value)
      return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' }) +
        ' ' +
        d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    }
    case 'boolean_yn':
      return value ? 'S\u00ed' : 'No'
    default:
      return String(value)
  }
}
