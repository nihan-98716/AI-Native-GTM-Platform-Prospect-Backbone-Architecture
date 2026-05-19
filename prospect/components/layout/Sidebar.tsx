"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import React, { useEffect, useMemo, useRef } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { useUI } from '../../hooks/useUI'

type NavItem = {
  label: string
  href: string
  icon: React.ReactNode
  visible?: boolean
}

const iconClass = 'h-4 w-4 shrink-0'

function navIcon(path: 'home' | 'accounts' | 'workflows' | 'integrations') {
  if (path === 'home') return <span aria-hidden className={iconClass}>⌂</span>
  if (path === 'accounts') return <span aria-hidden className={iconClass}>▦</span>
  if (path === 'workflows') return <span aria-hidden className={iconClass}>↻</span>
  return <span aria-hidden className={iconClass}>⚙</span>
}

function matchesPath(pathname: string, href: string) {
  if (href === '/') return pathname === '/'
  return pathname === href || pathname.startsWith(`${href}/`)
}

function SidebarNav({
  items,
  collapsed,
  onNavigate,
}: {
  items: NavItem[]
  collapsed: boolean
  onNavigate?: () => void
}) {
  const pathname = usePathname()
  const linksRef = useRef<Array<HTMLAnchorElement | null>>([])
  const visibleItems = items.filter((item) => item.visible !== false)

  const onKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    const currentIndex = linksRef.current.findIndex((node) => node === document.activeElement)
    if (currentIndex < 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      const next = linksRef.current[(currentIndex + 1) % linksRef.current.length]
      next?.focus()
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      const next = linksRef.current[(currentIndex - 1 + linksRef.current.length) % linksRef.current.length]
      next?.focus()
    }
  }

  return (
    <nav aria-label="Primary navigation" onKeyDown={onKeyDown}>
      <ul className="space-y-1">
        {visibleItems.map((item, index) => {
          const active = matchesPath(pathname, item.href)
          return (
            <li key={item.href}>
              <Link
                ref={(node) => {
                  linksRef.current[index] = node
                }}
                href={item.href}
                onClick={onNavigate}
                className={[
                  'group flex min-h-11 items-center gap-2 rounded-md border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
                  active
                    ? 'border-slate-400 bg-slate-100 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100'
                    : 'border-transparent text-slate-700 hover:border-slate-300 hover:bg-slate-50 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:bg-slate-800',
                ].join(' ')}
                aria-current={active ? 'page' : undefined}
                title={collapsed ? item.label : undefined}
              >
                {item.icon}
                {!collapsed ? <span className="truncate">{item.label}</span> : <span className="sr-only">{item.label}</span>}
                {active && <span aria-hidden className="ml-auto h-1.5 w-1.5 rounded-full bg-slate-700 dark:bg-slate-200" />}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export default function Sidebar() {
  const { claims } = useAuth()
  const { sidebarOpen, sidebarCollapsed, closeSidebar } = useUI()
  const panelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!sidebarOpen || !panelRef.current) return
    const node = panelRef.current
    const focusable = node.querySelectorAll<HTMLElement>('a,button')
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeSidebar()
        return
      }
      if (event.key === 'Tab') {
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    first?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [sidebarOpen, closeSidebar])

  const showWorkflows = claims ? (claims.roles?.includes('seller') ?? false) : true
  const items = useMemo<NavItem[]>(
    () => [
      { label: 'Dashboard', href: '/', icon: navIcon('home') },
      { label: 'Accounts', href: '/accounts', icon: navIcon('accounts') },
      { label: 'Workflows', href: '/workflows', icon: navIcon('workflows'), visible: showWorkflows },
      { label: 'Integrations', href: '/integrations', icon: navIcon('integrations') },
    ],
    [showWorkflows]
  )

  return (
    <>
      <aside
        className={[
          'hidden border-r bg-white/90 dark:bg-slate-950/90 md:flex md:flex-col',
          sidebarCollapsed ? 'md:w-16' : 'md:w-56',
        ].join(' ')}
        aria-label="Sidebar"
      >
        <div className="border-b px-3 py-4">
          <div className="text-sm font-semibold tracking-wide">{sidebarCollapsed ? 'P' : 'Prospect'}</div>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-2">
          <div>
            {!sidebarCollapsed ? <p className="px-2 pb-2 text-xs uppercase tracking-wide text-slate-500">Core</p> : null}
            <SidebarNav items={items.slice(0, 3)} collapsed={sidebarCollapsed} />
          </div>
          <div>
            {!sidebarCollapsed ? <p className="px-2 pb-2 text-xs uppercase tracking-wide text-slate-500">Settings</p> : null}
            <SidebarNav items={items.slice(3)} collapsed={sidebarCollapsed} />
          </div>
        </div>
      </aside>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Mobile navigation">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/45"
            onClick={closeSidebar}
            aria-label="Close navigation overlay"
          />
          <div ref={panelRef} className="absolute left-0 top-0 h-full w-72 max-w-[85vw] border-r bg-white p-3 dark:bg-slate-950">
            <div className="mb-3 flex items-center justify-between border-b pb-3">
              <div className="text-sm font-semibold tracking-wide">Prospect</div>
              <button
                type="button"
                className="min-h-11 min-w-11 rounded-md border px-3 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={closeSidebar}
                aria-label="Close sidebar"
              >
                ✕
              </button>
            </div>
            <SidebarNav items={items} collapsed={false} onNavigate={closeSidebar} />
          </div>
        </div>
      ) : null}
    </>
  )
}
