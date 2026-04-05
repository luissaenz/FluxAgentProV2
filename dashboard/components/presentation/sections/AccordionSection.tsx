'use client'

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import type { AccordionSection as AccordionSectionType } from '@/lib/presentation/types'
import { resolvePath } from '@/lib/presentation/resolve'
import { snakeCaseToTitle } from '@/lib/presentation/fallback'

interface AccordionSectionProps {
  section: AccordionSectionType
  data: Record<string, unknown>
}

export function AccordionSection({ section, data }: AccordionSectionProps) {
  const content = resolvePath(section.from, data)

  if (content === null || content === undefined) return null

  return (
    <Accordion
      type="single"
      collapsible
      defaultValue={section.default !== 'collapsed' ? 'item' : undefined}
    >
      <AccordionItem value="item" className="border-x-0">
        <AccordionTrigger className="text-sm font-semibold">
          {section.title || 'Detalle'}
        </AccordionTrigger>
        <AccordionContent>
          {typeof content === 'object' && !Array.isArray(content) ? (
            <dl className="space-y-1">
              {Object.entries(content as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-xs text-muted-foreground">{snakeCaseToTitle(k)}</dt>
                  <dd className="text-sm">{v === null || v === undefined ? '\u2014' : String(v)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="whitespace-pre-wrap text-sm">{String(content)}</p>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
