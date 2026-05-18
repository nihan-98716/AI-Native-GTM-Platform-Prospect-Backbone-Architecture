"use client"

import React from 'react'

type ThemePreference = 'system' | 'light' | 'dark'

const ThemeContext = React.createContext<any>(null)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreference] = React.useState<ThemePreference>(() => {
    try {
      const stored = localStorage.getItem('theme') as ThemePreference | null
      return (stored as ThemePreference) || 'system'
    } catch (e) {
      return 'system'
    }
  })

  React.useEffect(() => {
    const apply = (pref: ThemePreference) => {
      const isDark = pref === 'dark' || (pref === 'system' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      if (isDark) document.documentElement.classList.add('dark')
      else document.documentElement.classList.remove('dark')
    }
    apply(preference)
    try { localStorage.setItem('theme', preference) } catch (e) {}

    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => preference === 'system' && apply('system')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [preference])

  const setTheme = (t: ThemePreference) => setPreference(t)
  const toggle = () => setPreference((p) => (p === 'dark' ? 'light' : 'dark'))

  return <ThemeContext.Provider value={{ preference, setTheme, toggle }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = React.useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
