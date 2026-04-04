'use client'

import type { KeyValueListSection as KVSectionType } from '@/lib/presentation/types'
import { resolvePath } from '@/lib/presentation/resolve'
import { snakeCaseToTitle } from '@/lib/presentation/fallback'

interface KeyValueListSectionProps {
  section: KVSectionType
  data: Record<string, unknown>
}

export function KeyValueListSection({ section, data }: KeyValueListSectionProps) {
  const content = resolvePath(section.from, data)

  if (!content || typeof content !== 'object') return null

  // Handle both object and array of strings
  if (Array.isArray(content)) {
    return (
      <div>
        {section.title && (
          <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
            {section.title}
          </h4>
        )}
        <ul className="space-y-1">
          {content.map((item, i) => (
            <li key={i} className="text-sm text-gray-900 dark:text-gray-100">
              {String(item)}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  const entries = Object.entries(content as Record<string, unknown>)
  if (entries.length === 0) return null

  return (
    <div>
      {section.title && (
        <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {section.title}
        </h4>
      )}
      <dl className="space-y-1">
        {entries.map(([k, v]) => (
          <div key={k} className="flex justify-between">
            <dt className="text-xs text-gray-500 dark:text-gray-400">
              {snakeCaseToTitle(k)}
            </dt>
            <dd className="text-sm text-gray-900 dark:text-gray-100">
              {v === null || v === undefined ? '\u2014' : String(v)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
