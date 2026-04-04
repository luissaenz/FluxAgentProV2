'use client'

import type { DetailSection } from '@/lib/presentation/types'
import { FieldsSection } from './sections/FieldsSection'
import { TableSection } from './sections/TableSection'
import { AccordionSection } from './sections/AccordionSection'
import { KeyValueListSection } from './sections/KeyValueListSection'

interface SectionRendererProps {
  section: DetailSection
  data: Record<string, unknown>
}

export function SectionRenderer({ section, data }: SectionRendererProps) {
  switch (section.type) {
    case 'fields':
      return <FieldsSection section={section} data={data} />
    case 'table':
      return <TableSection section={section} data={data} />
    case 'accordion':
      return <AccordionSection section={section} data={data} />
    case 'key_value_list':
      return <KeyValueListSection section={section} data={data} />
    default:
      return null
  }
}
