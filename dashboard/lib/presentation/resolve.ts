/**
 * Resolve a JSONPath-like expression against a data object.
 * Supports: "$.field", "$.nested.field", "$.array[0].field"
 */
export function resolvePath(path: string, data: unknown): unknown {
  if (!path || !data) return undefined

  // Strip leading "$."
  const segments = path.replace(/^\$\.?/, '').split('.')
  let current: unknown = data

  for (const segment of segments) {
    if (current === null || current === undefined) return undefined

    // Handle array index: "items[0]"
    const arrayMatch = segment.match(/^(\w+)\[(\d+)\]$/)
    if (arrayMatch) {
      const [, key, idx] = arrayMatch
      current = (current as Record<string, unknown>)[key]
      if (Array.isArray(current)) {
        current = current[Number(idx)]
      } else {
        return undefined
      }
    } else {
      current = (current as Record<string, unknown>)[segment]
    }
  }

  return current
}
