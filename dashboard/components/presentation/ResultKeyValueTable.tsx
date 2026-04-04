'use client'

import { snakeCaseToTitle } from '@/lib/presentation/fallback'

interface ResultKeyValueTableProps {
  data: Record<string, unknown> | null
  className?: string
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '\u2014'
  if (typeof value === 'boolean') return value ? 'S\u00ed' : 'No'
  if (typeof value === 'number') {
    // Heuristic: large numbers likely currency
    if (value > 10000) return `$${value.toLocaleString('es-AR')}`
    return String(value)
  }
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    if (value.length === 0) return '\u2014'
    // Array of primitives: comma-separated
    if (value.every((v) => typeof v !== 'object')) return value.join(', ')
    return `${value.length} items`
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function isNestedObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function ResultKeyValueTable({ data, className }: ResultKeyValueTableProps) {
  if (!data || Object.keys(data).length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500">Sin resultado</p>
  }

  const entries = Object.entries(data)

  return (
    <div className={className}>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {entries.map(([key, value]) => {
            if (isNestedObject(value)) {
              return (
                <tr key={key}>
                  <td
                    colSpan={2}
                    className="pb-1 pt-3 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
                  >
                    {snakeCaseToTitle(key)}
                  </td>
                </tr>
              )
            }
            return null
          })}
          {entries.map(([key, value]) => {
            if (isNestedObject(value)) {
              // Render nested object as sub-rows
              return Object.entries(value).map(([subKey, subVal]) => (
                <tr key={`${key}.${subKey}`}>
                  <td className="w-2/5 py-1.5 pr-3 text-xs font-medium text-gray-500 dark:text-gray-400 align-top">
                    {snakeCaseToTitle(subKey)}
                  </td>
                  <td className="py-1.5 text-sm text-gray-900 dark:text-gray-100 break-words">
                    {formatValue(subVal)}
                  </td>
                </tr>
              ))
            }
            return (
              <tr key={key}>
                <td className="w-2/5 py-1.5 pr-3 text-xs font-medium text-gray-500 dark:text-gray-400 align-top">
                  {snakeCaseToTitle(key)}
                </td>
                <td className="py-1.5 text-sm text-gray-900 dark:text-gray-100 break-words">
                  {formatValue(value)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
