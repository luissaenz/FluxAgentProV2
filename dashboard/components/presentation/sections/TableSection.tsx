'use client'

import type { TableSection as TableSectionType } from '@/lib/presentation/types'
import { resolvePath } from '@/lib/presentation/resolve'
import { formatValue } from '@/lib/presentation/format'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

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
        <h4 className="mb-2 text-sm font-semibold text-muted-foreground">
          {section.title}
        </h4>
      )}
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {section.columns.map((col, i) => (
                <TableHead key={i}>
                  {col.label || col.from.replace(/^\$\./, '')}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, ri) => {
              let highlight = false
              if (section.highlight_where) {
                const match = section.highlight_where.match(/^\$\.(\w+)\s*==\s*(.+)$/)
                if (match) {
                  const [, field, expected] = match
                  const actual = (row as Record<string, unknown>)[field]
                  highlight = String(actual) === expected.trim()
                }
              }

              return (
                <TableRow
                  key={ri}
                  className={highlight ? 'bg-blue-50 font-medium dark:bg-blue-900/20' : ''}
                >
                  {section.columns.map((col, ci) => {
                    const val = resolvePath(col.from, row)
                    return (
                      <TableCell key={ci}>
                        {formatValue(val, col.format)}
                      </TableCell>
                    )
                  })}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
