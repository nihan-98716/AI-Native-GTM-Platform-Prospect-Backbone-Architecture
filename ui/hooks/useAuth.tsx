"use client"

import React from 'react'
import * as auth from '../lib/auth'

type Claims = { sub?: string; tenant_id?: string; roles?: string[]; permissions?: string[]; exp?: number }

const AuthContext = React.createContext<any>(null)

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = React.useState<string | null>(() => (typeof window !== 'undefined' ? auth.getToken() : null))
  const [claims, setClaims] = React.useState<Claims | null>(() => (token ? auth.getClaims(token) : null))

  React.useEffect(() => {
    // check token expiration on mount
    if (!token) return
    if (auth.isTokenExpired(token)) {
      // invalid token, clear
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
  }, [token])

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

  const value = { token, claims, login, logout, isAuthenticated, hasPermission, hasRole }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = React.useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
