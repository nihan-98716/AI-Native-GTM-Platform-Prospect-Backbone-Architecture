"use client"

import React, { useEffect, useRef } from 'react'

export default function FocusTrap({ children, onDeactivate }: { children: React.ReactNode; onDeactivate?: () => void }) {
  const ref = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const focusable = el.querySelectorAll<HTMLElement>('a,button,input,select,textarea')
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onDeactivate && onDeactivate()
      }
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault(); last?.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault(); first?.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    first?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [onDeactivate])
  return <div ref={ref}>{children}</div>
}
