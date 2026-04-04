'use client'

import type { FieldsSection as FieldsSectionType } from '@/lib/presentation/types'
import { resolvePath } from '@/lib/presentation/resolve'
import { formatValue } from '@/lib/presentation/format'

interface FieldsSectionProps {
  section: FieldsSectionType
  data: Record<string, unknown>
}

export function FieldsSection({ section, data }: FieldsSectionProps) {
  return (
    <div>
      {section.title && (
        <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {section.title}
        </h4>
      )}
      <dl className="divide-y divide-gray-100 dark:divide-gray-800">
        {section.fields.map((field, i) => {
          const raw = resolvePath(field.from, data)
          return (
            <div key={i} className="flex justify-between py-1.5">
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                {field.label || field.from.replace(/^\$\./, '')}
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100">
                {formatValue(raw, field.format)}
              </dd>
            </div>
          )
        })}
      </dl>
    </div>
  )
}
