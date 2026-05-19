"use client"

import React from 'react'
import { useAuth } from './useAuth'
import { buildUrl } from '../services/api'

export function useFetch() {
  const { token } = useAuth()

  const fetchWithAuth = React.useCallback(
    async (input: RequestInfo | string, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input
      const normalizedPath =
        typeof path === 'string' && path.startsWith('/') && !path.startsWith('/v1/') && !path.startsWith('/api/') && path !== '/healthz'
          ? `/v1${path}`
          : path
      const url = typeof normalizedPath === 'string' ? buildUrl(normalizedPath) : normalizedPath
      const headers = new Headers((init && init.headers) as HeadersInit)
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(url as RequestInfo, { ...init, headers })
      if (!res.ok) throw new Error(`Fetch error ${res.status}`)
      return res.json()
    },
    [token]
  )

  return { fetchWithAuth }
}
