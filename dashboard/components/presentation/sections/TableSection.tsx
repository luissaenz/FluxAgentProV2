'use client'

import type { TableSection as TableSectionType } from '@/lib/presentation/types'
import { resolvePath } from '@/lib/presentation/resolve'
import { formatValue } from '@/lib/presentation/format'

interface TableSectionProps {
  section: TableSectionType
  data: Record<string, unknown>
}

export function TableSection({ section, data }: TableSectionProps) {
  const rows = resolvePath(section.from, data)
  if (!Array.isArray(rows) || rows.length === 0) return null

  return (
    <div>
      {section.title && (
        <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {section.title}
        </h4>
      )}
      <div className="overflow-x-auto rounded border dark:border-gray-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800">
              {section.columns.map((col, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
                >
                  {col.label || col.from.replace(/^\$\./, '')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {rows.map((row, ri) => {
              // Check highlight condition
              let highlight = false
              if (section.highlight_where) {
                // Simple check: "$.field == value"
                const match = section.highlight_where.match(/^\$\.(\w+)\s*==\s*(.+)$/)
                if (match) {
                  const [, field, expected] = match
                  const actual = (row as Record<string, unknown>)[field]
                  highlight = String(actual) === expected.trim()
                }
              }

              return (
                <tr
                  key={ri}
                  className={
                    highlight
                      ? 'bg-blue-50 font-medium dark:bg-blue-900/20'
                      : ''
                  }
                >
                  {section.columns.map((col, ci) => {
                    const val = resolvePath(col.from, row)
                    return (
                      <td
                        key={ci}
                        className="px-3 py-2 text-gray-900 dark:text-gray-100"
                      >
                        {formatValue(val, col.format)}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
