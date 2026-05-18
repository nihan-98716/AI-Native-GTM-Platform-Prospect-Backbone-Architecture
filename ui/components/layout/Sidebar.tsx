"use client"

import React, { useEffect, useRef } from 'react'
import Link from 'next/link'
import { useUI } from '../../hooks/useUI'
import { useAuth } from '../../hooks/useAuth'

export default function Sidebar() {
  const { sidebarOpen, closeSidebar } = useUI()
  const { claims } = useAuth()
  const panelRef = useRef<HTMLDivElement | null>(null)

  // basic focus trap for mobile panel
  useEffect(() => {
    if (!sidebarOpen || !panelRef.current) return
    const el = panelRef.current
    const focusable = el.querySelectorAll<HTMLElement>('a,button,input,select,textarea')
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeSidebar()
      }
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last?.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first?.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    first?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [sidebarOpen, closeSidebar])

  const showWorkflows = claims ? (claims.roles?.includes('seller') ?? false) : true

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="w-64 hidden md:block bg-white dark:bg-gray-900 border-r" aria-label="Sidebar">
        <div className="p-4">
          <div className="text-lg font-bold">Prospect</div>
        </div>
        <nav className="px-2 py-4" aria-label="Main navigation">
          <ul>
            <li className="mb-2"><Link href="/">Dashboard</Link></li>
            <li className="mb-2"><Link href="/accounts">Accounts</Link></li>
            {showWorkflows && <li className="mb-2"><Link href="/workflows">Workflows</Link></li>}
            <li className="mb-2"><Link href="/integrations">Integrations</Link></li>
          </ul>
        </nav>
      </aside>

      {/* Mobile off-canvas */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
          <div className="fixed inset-0 bg-black/40" onClick={closeSidebar} aria-hidden="true"></div>
          <div ref={panelRef} className="fixed left-0 top-0 bottom-0 w-64 bg-white dark:bg-gray-900 p-4 overflow-auto focus:outline-none">
            <div className="flex items-center justify-between">
              <div className="text-lg font-bold">Prospect</div>
              <button aria-label="Close sidebar" onClick={closeSidebar}>✕</button>
            </div>
            <nav className="mt-4" aria-label="Mobile navigation">
              <ul>
                <li className="mb-2"><Link href="/">Dashboard</Link></li>
                <li className="mb-2"><Link href="/accounts">Accounts</Link></li>
                {showWorkflows && <li className="mb-2"><Link href="/workflows">Workflows</Link></li>}
                <li className="mb-2"><Link href="/integrations">Integrations</Link></li>
              </ul>
            </nav>
          </div>
        </div>
      )}
    </>
  )
}
