"use client"

import React from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Sidebar from './Sidebar'
import TopNav from './TopNav'
import { useAuth } from '../../hooks/useAuth'

function sanitizeNode(node: React.ReactNode): React.ReactNode {
  if (node === null || node === undefined || typeof node === 'boolean') return null
  if (typeof node === 'string' || typeof node === 'number') return node
  if (Array.isArray(node)) return node.map((n) => sanitizeNode(n))
  if (!React.isValidElement(node)) return node

  const element = node as React.ReactElement<any>
  const type = element.type
  const props = element.props as { children?: React.ReactNode; [k: string]: any }
  const children = React.Children.map(props.children, (c) => sanitizeNode(c))

  if (typeof type === 'string' && type.toLowerCase() === 'main') {
    // Replace nested <main> with <section> and remove any id to avoid duplicate landmarks
    const newProps = { ...props }
    if (newProps.id) delete newProps.id
    // Use a section element to preserve semantics
    return React.createElement('section', newProps, children)
  }

  return React.cloneElement(element, { ...props }, children)
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const safeChildren = React.Children.map(children, (c) => sanitizeNode(c))
  const isLoginPage = pathname === '/login'

  React.useEffect(() => {
    if (isLoginPage) return
    if (!isAuthenticated) router.replace('/login')
  }, [isAuthenticated, isLoginPage, router])

  if (isLoginPage) {
    return (
      <div className="min-h-screen bg-surface text-text">
        <main id="main" tabIndex={-1} className="p-4 md:p-6">{safeChildren}</main>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <div className="min-h-screen" />
  }

  return (
    <div className="min-h-screen flex bg-surface text-text">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopNav />
        <main id="main" tabIndex={-1} className="p-4 md:p-6">{safeChildren}</main>
      </div>
    </div>
  )
}
