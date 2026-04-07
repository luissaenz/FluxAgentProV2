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
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API error: ${response.status}`)
  }

  return response.json()
}

export const api = {
  get: (path: string) => fapFetch(path, { method: 'GET' }),
  post: (path: string, body?: unknown) =>
    fapFetch(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path: string, body?: unknown) =>
    fapFetch(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: (path: string, body?: unknown) =>
    fapFetch(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path: string) => fapFetch(path, { method: 'DELETE' }),
}
