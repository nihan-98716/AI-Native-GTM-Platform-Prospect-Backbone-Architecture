"use client"

import React from 'react'
import { useAuth } from '../../hooks/useAuth'

export default function Protected({ children, requiredPermission, requiredRole, fallback }: { children: React.ReactNode; requiredPermission?: string; requiredRole?: string; fallback?: React.ReactNode }) {
  const { isAuthenticated, hasPermission, hasRole, ready } = useAuth()
  if (!ready) return <div aria-hidden className="min-h-20" />
  if (!isAuthenticated) return <div role="alert">Not authenticated</div>
  if (requiredPermission && !hasPermission(requiredPermission)) return <>{fallback || <div role="alert">Unauthorized</div>}</>
  if (requiredRole && !hasRole(requiredRole)) return <>{fallback || <div role="alert">Forbidden</div>}</>
  return <>{children}</>
}
