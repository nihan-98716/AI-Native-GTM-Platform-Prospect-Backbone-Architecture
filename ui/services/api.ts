export const BASE_API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || ''

export function buildUrl(path: string, params?: Record<string, string | number | undefined>) {
  const url = new URL((BASE_API_URL || '') + path, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
  if (params) {
    Object.keys(params).forEach((k) => {
      const v = params[k]
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    })
  }
  return url.toString()
}
