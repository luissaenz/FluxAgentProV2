import { createClient } from './supabase'
import { HTTP_METHODS } from './constants'

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

  // Si el body es FormData, el navegador debe setear el Content-Type automáticamente con el boundary
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${session.access_token}`,
    'X-Org-ID': orgId,
    ...((options.headers as Record<string, string>) || {}),
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_FASTAPI_URL}${path}`,
    {
      ...options,
      headers,
    }
  )

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const detail = errorData.detail
    
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

export async function fapDownload(path: string, body: unknown, method?: string): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession()
  const orgId = typeof window !== 'undefined'
    ? localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id') || ''
    : ''

  if (!session?.access_token) {
    throw new Error('Not authenticated')
  }

  const headers: Record<string, string> = {
    'Authorization': `Bearer ${session.access_token}`,
    'X-Org-ID': orgId,
    'Content-Type': 'application/json',
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_FASTAPI_URL}${path}`,
    {
      method: method ?? HTTP_METHODS.POST,
      headers,
      body: JSON.stringify(body),
    }
  )

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const detail = errorData.detail

    let message = `API error: ${response.status}`
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object') {
      message = detail.error || detail.message || JSON.stringify(detail)
    }

    throw new Error(message)
  }

  return response
}

export const api = {
  get: (path: string, options: Partial<RequestInit> = {}) => 
    fapFetch(path, { method: HTTP_METHODS.GET, ...options }),
  post: (path: string, body?: any, options: Partial<RequestInit> = {}) =>
    fapFetch(path, { 
      method: HTTP_METHODS.POST, 
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined), 
      ...options 
    }),
  put: (path: string, body?: any, options: Partial<RequestInit> = {}) =>
    fapFetch(path, { 
      method: HTTP_METHODS.PUT, 
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined), 
      ...options 
    }),
  patch: (path: string, body?: any, options: Partial<RequestInit> = {}) =>
    fapFetch(path, { 
      method: HTTP_METHODS.PATCH, 
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined), 
      ...options 
    }),
  delete: (path: string, options: Partial<RequestInit> = {}) => 
    fapFetch(path, { method: HTTP_METHODS.DELETE, ...options }),
}
