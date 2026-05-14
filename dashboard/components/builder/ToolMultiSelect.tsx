'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Search, X, ChevronDown } from 'lucide-react'

interface ToolOption {
  value: string
  label: string
  source: string
}

interface ToolMultiSelectProps {
  options: ToolOption[]
  values: string[]
  onChange: (v: string[]) => void
  placeholder?: string
  disabled?: boolean
}

export function ToolMultiSelect({
  options,
  values,
  onChange,
  placeholder = 'Search tools...',
  disabled = false,
}: ToolMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filtered = useMemo(() => {
    if (!search.trim()) return options
    const q = search.toLowerCase()
    return options.filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q)
    )
  }, [options, search])

  const grouped = useMemo(() => {
    const map: Record<string, ToolOption[]> = {}
    for (const o of filtered) {
      if (!map[o.source]) map[o.source] = []
      map[o.source].push(o)
    }
    return map
  }, [filtered])

  const selectedOptions = options.filter((o) => values.includes(o.value))

  function toggle(value: string) {
    if (values.includes(value)) {
      onChange(values.filter((v) => v !== value))
    } else {
      onChange([...values, value])
    }
  }

  function remove(value: string) {
    onChange(values.filter((v) => v !== value))
  }

  return (
    <div ref={containerRef} className="relative">
      <div
        className={`flex min-h-9 w-full flex-wrap items-center gap-1 rounded-md border border-input bg-transparent px-3 py-1.5 text-sm ${
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
        }`}
        onClick={() => !disabled && setOpen(!open)}
      >
        {selectedOptions.length === 0 ? (
          <span className="text-muted-foreground">Select tools...</span>
        ) : (
          selectedOptions.map((o) => (
            <Badge key={o.value} variant="secondary" className="gap-1 pr-0.5">
              {o.label}
              <button
                type="button"
                className="ml-1 rounded-full p-0.5 hover:bg-muted"
                onClick={(e) => {
                  e.stopPropagation()
                  remove(o.value)
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))
        )}
        <ChevronDown className="ml-auto h-4 w-4 shrink-0 opacity-50" />
      </div>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md">
          <div className="flex items-center border-b px-3 py-2">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <input
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              placeholder={placeholder}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div className="max-h-60 overflow-y-auto p-1">
            {Object.keys(grouped).length === 0 ? (
              <p className="px-2 py-4 text-center text-sm text-muted-foreground">
                No tools found
              </p>
            ) : (
              Object.entries(grouped).map(([source, items]) => (
                <div key={source}>
                  <div className="px-2 py-1 text-xs font-semibold uppercase text-muted-foreground">
                    {source}
                  </div>
                  {items.map((option) => {
                    const checked = values.includes(option.value)
                    return (
                      <label
                        key={option.value}
                        className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-input accent-primary"
                          checked={checked}
                          onChange={() => toggle(option.value)}
                        />
                        <span className={checked ? 'font-medium' : ''}>
                          {option.label}
                        </span>
                      </label>
                    )
                  })}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
