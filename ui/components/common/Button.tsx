"use client"

import React from 'react'
import { tokens } from '../../lib/design-tokens'

export default function Button({ children, onClick, variant = 'default' }: { children: React.ReactNode; onClick?: () => void; variant?: 'default' | 'primary' }) {
  const base = 'px-3 py-1 rounded focus:outline-none focus:ring-2'
  const cls = variant === 'primary' ? `${base} bg-primary text-white` : `${base} border bg-white dark:bg-gray-800`
  return (
    <button className={cls} onClick={onClick}>
      {children}
    </button>
  )
}
