"use client"

import React from 'react'
import * as auth from '../lib/auth'

type Claims = { sub?: string; tenant_id?: string; roles?: string[]; permissions?: string[]; exp?: number }
type BootstrapSession = {
  token: string | null
  tenantDisplayName: string | null
  profileDisplayName: string | null
}

const AuthContext = React.createContext<any>(null)

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = React.useState(false)
  const [tenantDisplayName, setTenantDisplayName] = React.useState<string | null>(null)
  const [profileDisplayName, setProfileDisplayName] = React.useState<string | null>(null)
  const [token, setTokenState] = React.useState<string | null>(() => {
    if (typeof window === 'undefined') return null
    return auth.getToken() || auth.getBootstrapToken()
  })
  const [claims, setClaims] = React.useState<Claims | null>(() => {
    if (!token) return null
    return auth.getClaims(token)
  })

  React.useEffect(() => {
    let mounted = true
    const hydrate = async () => {
      const persistedToken = auth.getToken()
      const bootstrapEnvToken = auth.getBootstrapToken()
      const currentToken = [persistedToken, bootstrapEnvToken].find((candidate) => candidate && !auth.isTokenExpired(candidate)) || null
      if (currentToken) {
        if (mounted) {
          setTokenState(currentToken)
          setClaims(auth.getClaims(currentToken))
        }
      }
      const response = await fetch('/api/bootstrap', { cache: 'no-store' })
      if (!response.ok && response.status !== 204) {
        if (mounted) setReady(true)
        return
      }

      const payload = (await response.json().catch(() => null)) as BootstrapSession | null
      const bootstrapToken = payload?.token || null
      if (bootstrapToken && !auth.isTokenExpired(bootstrapToken)) {
        auth.setToken(bootstrapToken)
        if (mounted && !currentToken) {
          setTokenState(bootstrapToken)
          setClaims(auth.getClaims(bootstrapToken))
        }
      }
      if (mounted) {
        setTenantDisplayName(payload?.tenantDisplayName || null)
        setProfileDisplayName(payload?.profileDisplayName || null)
        setReady(true)
      }
    }

    hydrate()
    return () => {
      mounted = false
    }
  }, [])

  React.useEffect(() => {
    if (!ready || !token) return
    if (auth.isTokenExpired(token)) {
      auth.setToken(null)
      setTokenState(null)
      setClaims(null)
      return
    }
    setClaims(auth.getClaims(token))
    const interval = setInterval(() => {
      const t = auth.getToken()
      if (!t || auth.isTokenExpired(t)) {
        auth.setToken(null)
        setTokenState(null)
        setClaims(null)
      }
    }, 1000 * 60)
    return () => clearInterval(interval)
  }, [ready, token])

  const login = (newToken: string) => {
    auth.setToken(newToken)
    setTokenState(newToken)
    setClaims(auth.getClaims(newToken))
  }

  const logout = () => {
    auth.setToken(null)
    setTokenState(null)
    setClaims(null)
  }

  const isAuthenticated = React.useMemo(() => {
    return !!token && !auth.isTokenExpired(token)
  }, [token])

  const hasPermission = (permission: string) => auth.hasPermission(claims, permission)
  const hasRole = (role: string) => auth.hasRole(claims, role)

  const value = {
    token,
    claims,
    ready,
    tenantDisplayName,
    profileDisplayName,
    login,
    logout,
    isAuthenticated,
    hasPermission,
    hasRole,
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = React.useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
