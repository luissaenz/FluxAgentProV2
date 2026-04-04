/** Format types available for value display */
export type FormatType =
  | 'currency_ars'
  | 'currency_usd'
  | 'pct'
  | 'date'
  | 'datetime_short'
  | 'boolean_yn'

/** A reference to a field inside tasks.result via JSONPath-like syntax */
export interface FieldRef {
  from: string
  label?: string
  format?: FormatType
}

/** Icon mapping from a field value to emoji/icon */
export interface IconMap {
  from: string
  map: Record<string, string>
}

/** Card view config */
export interface CardConfig {
  icon?: IconMap
  title?: FieldRef
  amount?: FieldRef
}

/** Detail section: fields (key-value pairs) */
export interface FieldsSection {
  type: 'fields'
  title?: string
  fields: FieldRef[]
}

/** Detail section: table with columns */
export interface TableSection {
  type: 'table'
  title?: string
  from: string
  columns: FieldRef[]
  highlight_where?: string
}

/** Detail section: collapsible accordion */
export interface AccordionSection {
  type: 'accordion'
  title?: string
  default?: 'collapsed' | 'expanded'
  from: string
  render_as?: 'key_value_list'
}

/** Detail section: simple key-value list */
export interface KeyValueListSection {
  type: 'key_value_list'
  title?: string
  from: string
}

export type DetailSection =
  | FieldsSection
  | TableSection
  | AccordionSection
  | KeyValueListSection

/** Detail view config */
export interface DetailConfig {
  sections: DetailSection[]
}

/** Root presentation_config shape */
export interface PresentationConfig {
  card?: CardConfig
  detail?: DetailConfig
}

/** Row from flow_presentations table */
export interface FlowPresentation {
  id: string
  org_id: string
  flow_type: string
  presentation_config: PresentationConfig
  created_at: string
  updated_at: string
}
