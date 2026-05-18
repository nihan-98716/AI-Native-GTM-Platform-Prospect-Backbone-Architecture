"use client"

import { useAuth } from './useAuth'

export function useFetch() {
  const { token } = useAuth()

  async function fetchWithAuth(input: RequestInfo | string, init?: RequestInit) {
    const url = typeof input === 'string' ? input : input
    const headers = new Headers((init && init.headers) as HeadersInit)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const res = await fetch(url as RequestInfo, { ...init, headers })
    if (!res.ok) throw new Error(`Fetch error ${res.status}`)
    return res.json()
  }

  return { fetchWithAuth }
}
