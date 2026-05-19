"use client"

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import React from 'react'
import * as auth from '../../lib/auth'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { useUI } from '../../hooks/useUI'

function titleCase(value: string) {
  return value
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function useBreadcrumbs(pathname: string) {
  if (pathname === '/' || pathname === '/accounts' || pathname === '/workflows' || pathname === '/integrations') return []
  if (pathname.startsWith('/workflows/')) {
    const id = decodeURIComponent(pathname.split('/')[2] || '')
    return [{ label: 'Workflows', href: '/workflows' }, { label: id || 'Detail', href: pathname }]
  }
  if (pathname.startsWith('/accounts/')) {
    const id = decodeURIComponent(pathname.split('/')[2] || '')
    return [{ label: 'Accounts', href: '/accounts' }, { label: id || 'Detail', href: pathname }]
  }
  return []
}

export default function TopNav() {
  const pathname = usePathname()
  const router = useRouter()
  const breadcrumbs = useBreadcrumbs(pathname)
  const { claims, isAuthenticated, login, logout, ready, tenantDisplayName, profileDisplayName } = useAuth()
  const { preference, toggle } = useTheme()
  const { openSidebar, sidebarCollapsed, toggleSidebarCollapsed } = useUI()
  const [profileOpen, setProfileOpen] = React.useState(false)
  const [sessionTenantName, setSessionTenantName] = React.useState<string | null>(null)
  const [sessionProfileName, setSessionProfileName] = React.useState<string | null>(null)
  const menuRef = React.useRef<HTMLDivElement | null>(null)
  const itemRefs = React.useRef<Array<HTMLButtonElement | null>>([])
  const menuId = React.useId()

  React.useEffect(() => {
    if (!profileOpen) return
    const closeOnOutside = (event: MouseEvent) => {
      if (!menuRef.current) return
      if (!menuRef.current.contains(event.target as Node)) setProfileOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setProfileOpen(false)
    }
    document.addEventListener('mousedown', closeOnOutside)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnOutside)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [profileOpen])

  const onMenuKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const index = itemRefs.current.findIndex((node) => node === document.activeElement)
    if (index < 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      itemRefs.current[(index + 1) % itemRefs.current.length]?.focus()
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      itemRefs.current[(index - 1 + itemRefs.current.length) % itemRefs.current.length]?.focus()
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      itemRefs.current[index]?.click()
    }
  }

  const openProfileMenu = () => {
    setProfileOpen(true)
    requestAnimationFrame(() => itemRefs.current[0]?.focus())
  }

  const handleLogin = async () => {
    const bootstrapToken = auth.getBootstrapToken()
    if (bootstrapToken && !auth.isTokenExpired(bootstrapToken)) {
      login(bootstrapToken)
      router.refresh()
      return
    }

    const response = await fetch('/api/bootstrap', { cache: 'no-store' })
    if (!response.ok) return
    const payload = await response.json().catch(() => null)
    const responseToken = payload?.token || null
    if (!responseToken) return
    setSessionTenantName(payload?.tenantDisplayName || null)
    setSessionProfileName(payload?.profileDisplayName || null)
    login(responseToken)
    router.refresh()
  }

  const handleLogout = () => {
    logout()
    setProfileOpen(false)
    setSessionTenantName(null)
    setSessionProfileName(null)
    router.replace('/')
    router.refresh()
  }

  const handleProfileButtonClick = () => {
    if (!isAuthenticated) {
      void handleLogin()
      return
    }
    setProfileOpen((open) => !open)
  }

  return (
    <header className="sticky top-0 z-30 border-b bg-white/95 backdrop-blur-sm dark:bg-slate-950/95">
      <div className="flex min-h-14 items-center justify-between gap-3 px-3 py-2 md:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            aria-label="Open sidebar"
            onClick={openSidebar}
            className="min-h-11 min-w-11 rounded-md border px-3 text-sm md:hidden"
          >
            ☰
          </button>
          <button
            type="button"
            onClick={toggleSidebarCollapsed}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="hidden min-h-11 min-w-11 rounded-md border px-3 text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 md:inline-flex"
          >
            ☰
          </button>
          {breadcrumbs.length > 0 ? (
            <nav aria-label="Breadcrumb" className="min-w-0">
              <ol className="flex flex-wrap items-center gap-1 text-sm text-slate-600 dark:text-slate-300">
                {breadcrumbs.map((crumb, index) => (
                  <li key={crumb.href} className="flex items-center gap-1">
                    {index > 0 ? <span aria-hidden>/</span> : null}
                    {index === breadcrumbs.length - 1 ? (
                      <span className="truncate font-medium text-slate-900 dark:text-slate-100">{crumb.label}</span>
                    ) : (
                      <Link href={crumb.href} className="truncate rounded px-1 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800">
                        {crumb.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          {ready ? (
            <span className="hidden rounded-md border px-2 py-1 text-xs text-slate-600 dark:text-slate-300 sm:inline-flex" title={claims?.tenant_id}>
              Tenant: {sessionTenantName || tenantDisplayName || 'Tenant-01'}
            </span>
          ) : null}
          <button
            type="button"
            onClick={toggle}
            aria-label="Toggle theme"
            className="min-h-11 min-w-11 rounded-md border px-3 text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800"
          >
            {preference === 'dark' ? '🌙' : '☀️'}
          </button>
          <div ref={menuRef} className="relative" onKeyDown={onMenuKeyDown}>
            <button
              type="button"
              className="min-h-11 rounded-md border px-3 text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800"
              aria-haspopup="menu"
              aria-expanded={isAuthenticated ? profileOpen : undefined}
              aria-controls={menuId}
              aria-label={isAuthenticated ? 'Open profile menu' : 'Login'}
              onClick={handleProfileButtonClick}
              onKeyDown={(event) => {
                if (!isAuthenticated && (event.key === 'Enter' || event.key === ' ')) {
                  event.preventDefault()
                  void handleLogin()
                  return
                }
                if (isAuthenticated && (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown')) {
                  event.preventDefault()
                  openProfileMenu()
                }
                if (event.key === 'Escape') {
                  event.preventDefault()
                  setProfileOpen(false)
                }
              }}
            >
              {ready ? (isAuthenticated ? sessionProfileName || profileDisplayName || 'User-01' : 'Login') : 'Loading'}
            </button>
            {profileOpen ? (
              <div id={menuId} role="menu" aria-label="Profile menu" className="absolute right-0 mt-2 w-44 rounded-md border bg-white p-1 shadow-sm dark:bg-slate-900">
                {isAuthenticated ? (
                  <>
                    <button
                      ref={(node) => {
                        itemRefs.current[0] = node
                      }}
                      type="button"
                      role="menuitem"
                      className="flex min-h-11 w-full items-center rounded px-3 text-left text-sm hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800"
                      onClick={() => {
                        setProfileOpen(false)
                      }}
                    >
                      Profile
                    </button>
                    <button
                      ref={(node) => {
                        itemRefs.current[1] = node
                      }}
                      type="button"
                      role="menuitem"
                      className="flex min-h-11 w-full items-center rounded px-3 text-left text-sm hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800"
                      onClick={handleLogout}
                    >
                      Logout
                    </button>
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  )
}
