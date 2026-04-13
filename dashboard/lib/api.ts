import { createClient } from './supabase'

const supabase = createClient()

export async function fapFetch(
  path: string,
  options: RequestInit = {}
) {
  const { data: { session } } = await supabase.auth.getSession()
  const orgId = typeof window !== 'undefined'
    ? localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id') || ''
    : ''

  if (!session?.access_token) {
    throw new Error('Not authenticated')
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_FASTAPI_URL}${path}`,
    {
      ...options,
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'X-Org-ID': orgId,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    }
  )

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const detail = errorData.detail
    
    // Si detail es un objeto, intentamos extraer los campos message o error según prioridad
    let message = `API error: ${response.status}`
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object') {
      message = detail.error || detail.message || JSON.stringify(detail)
    }
    
    throw new Error(message)
  }

  return response.json()
}

export const api = {
  get: (path: string, options: Partial<RequestInit> = {}) => 
    fapFetch(path, { method: 'GET', ...options }),
  post: (path: string, body?: unknown, options: Partial<RequestInit> = {}) =>
    fapFetch(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined, ...options }),
  put: (path: string, body?: unknown, options: Partial<RequestInit> = {}) =>
    fapFetch(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined, ...options }),
  patch: (path: string, body?: unknown, options: Partial<RequestInit> = {}) =>
    fapFetch(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined, ...options }),
  delete: (path: string, options: Partial<RequestInit> = {}) => 
    fapFetch(path, { method: 'DELETE', ...options }),
}
