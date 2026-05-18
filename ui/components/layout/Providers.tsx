"use client"

import React from 'react'
import AuthProvider from '../../hooks/useAuth'
import { ThemeProvider } from '../../hooks/useTheme'
import { UIProvider } from '../../hooks/useUI'
import SkipLink from '../common/SkipLink'

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ThemeProvider>
        <UIProvider>
          <SkipLink />
          {children}
        </UIProvider>
      </ThemeProvider>
    </AuthProvider>
  )
}
