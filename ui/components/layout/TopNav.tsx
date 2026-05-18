"use client"

import React from 'react'
import { useRouter } from 'next/navigation'
import { useUI } from '../../hooks/useUI'
import { useTheme } from '../../hooks/useTheme'
import { useAuth } from '../../hooks/useAuth'

export default function TopNav() {
  const router = useRouter()
  const { openSidebar } = useUI()
  const { preference, toggle } = useTheme()
  const { claims, logout } = useAuth()

  const onLogout = React.useCallback(() => {
    logout()
    router.push('/login')
  }, [logout, router])

  return (
    <header className="flex items-center justify-between px-4 py-3 border-b bg-white dark:bg-gray-900">
      <div className="flex items-center gap-4">
        <button aria-label="Open sidebar" onClick={openSidebar} className="md:hidden">☰</button>
        <div className="text-sm text-gray-600">Workflow status: <strong>idle</strong></div>
      </div>
      <div className="flex items-center gap-4">
        <button onClick={toggle} aria-label="Toggle theme" className="px-2 py-1 border rounded">{preference === 'dark' ? '🌙' : '☀️'}</button>
        <button onClick={onLogout} aria-label="Logout" className="px-2 py-1 border rounded">Logout</button>
        <div className="text-sm text-gray-600">{claims?.sub || 'User'}</div>
      </div>
    </header>
  )
}
