'use client'

import { useState } from 'react'
import type { AccordionSection as AccordionSectionType } from '@/lib/presentation/types'
import { resolvePath } from '@/lib/presentation/resolve'
import { snakeCaseToTitle } from '@/lib/presentation/fallback'
import { ChevronRight } from 'lucide-react'

interface AccordionSectionProps {
  section: AccordionSectionType
  data: Record<string, unknown>
}

export function AccordionSection({ section, data }: AccordionSectionProps) {
  const [open, setOpen] = useState(section.default !== 'collapsed')
  const content = resolvePath(section.from, data)

  if (content === null || content === undefined) return null

  return (
    <div className="rounded border dark:border-gray-700">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800"
      >
        {section.title || 'Detalle'}
        <ChevronRight
          className={`h-4 w-4 transition-transform ${open ? 'rotate-90' : ''}`}
        />
      </button>
      {open && (
        <div className="border-t px-3 py-2 dark:border-gray-700">
          {typeof content === 'object' && !Array.isArray(content) ? (
            <dl className="space-y-1">
              {Object.entries(content as Record<string, unknown>).map(
                ([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <dt className="text-xs text-gray-500 dark:text-gray-400">
                      {snakeCaseToTitle(k)}
                    </dt>
                    <dd className="text-sm text-gray-900 dark:text-gray-100">
                      {v === null || v === undefined
                        ? '\u2014'
                        : String(v)}
                    </dd>
                  </div>
                )
              )}
            </dl>
          ) : (
            <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
              {String(content)}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
