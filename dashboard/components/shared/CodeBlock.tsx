'use client'

interface CodeBlockProps {
  code: unknown
  title?: string
  className?: string
}

export function CodeBlock({ code, title, className }: CodeBlockProps) {
  return (
    <div className={className}>
      {title && (
        <h4 className="mb-2 text-sm font-medium">{title}</h4>
      )}
      <pre className="overflow-x-auto rounded-md bg-muted p-4 text-xs text-muted-foreground">
        {JSON.stringify(code, null, 2)}
      </pre>
    </div>
  )
}
