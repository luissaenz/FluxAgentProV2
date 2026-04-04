'use client'

import type { PresentationConfig } from '@/lib/presentation/types'
import { ResultKeyValueTable } from './ResultKeyValueTable'
import { SectionRenderer } from './SectionRenderer'

interface PresentedTaskDetailProps {
  result: Record<string, unknown> | null
  config?: PresentationConfig | null
}

/**
 * Renders task result using presentation_config sections if available,
 * otherwise falls back to the generic ResultKeyValueTable.
 */
export function PresentedTaskDetail({ result, config }: PresentedTaskDetailProps) {
  if (!result) {
    return <p className="text-sm text-gray-400 dark:text-gray-500">Sin resultado</p>
  }

  // If config has detail sections, render them
  if (config?.detail?.sections && config.detail.sections.length > 0) {
    return (
      <div className="space-y-4">
        {config.detail.sections.map((section, i) => (
          <SectionRenderer key={i} section={section} data={result} />
        ))}
      </div>
    )
  }

  // Fallback: generic key-value table
  return <ResultKeyValueTable data={result} />
}
