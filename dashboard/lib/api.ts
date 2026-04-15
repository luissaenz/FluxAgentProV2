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

  console.log(`[fapFetch] REQ -> ${options.method || 'GET'} ${process.env.NEXT_PUBLIC_FASTAPI_URL}${path}`);
  try {
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

    console.log(`[fapFetch] RES <- ${response.status} for ${path}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const detail = errorData.detail
      
      let message = `API error: ${response.status}`
      if (typeof detail === 'string') {
        message = detail
      } else if (detail && typeof detail === 'object') {
        message = detail.error || detail.message || JSON.stringify(detail)
      }
      
      console.error(`[fapFetch] Error ${response.status} in ${path}:`, message);
      throw new Error(message)
    }

    return response.json()
  } catch (err) {
    console.error(`[fapFetch] NETWORK/FETCH ERROR in ${path}:`, err);
    throw err;
  }
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
