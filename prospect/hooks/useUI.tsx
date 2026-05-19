"use client"

import React from 'react'

const UIContext = React.createContext<any>(null)

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem('ui:sidebar-collapsed') === '1'
  })

  React.useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [sidebarOpen])

  React.useEffect(() => {
    try {
      localStorage.setItem('ui:sidebar-collapsed', sidebarCollapsed ? '1' : '0')
    } catch {}
  }, [sidebarCollapsed])

  const openSidebar = () => setSidebarOpen(true)
  const closeSidebar = () => setSidebarOpen(false)
  const toggleSidebar = () => setSidebarOpen((s: boolean) => !s)
  const toggleSidebarCollapsed = () => setSidebarCollapsed((s: boolean) => !s)

  return (
    <UIContext.Provider
      value={{
        sidebarOpen,
        sidebarCollapsed,
        openSidebar,
        closeSidebar,
        toggleSidebar,
        toggleSidebarCollapsed,
      }}
    >
      {children}
    </UIContext.Provider>
  )
}

export function useUI() {
  const ctx = React.useContext(UIContext)
  if (!ctx) throw new Error('useUI must be used within UIProvider')
  return ctx
}
