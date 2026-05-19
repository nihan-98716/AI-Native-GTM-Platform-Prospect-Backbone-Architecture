"use client"

import React from 'react'
import Sidebar from './Sidebar'
import TopNav from './TopNav'

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
  const safeChildren = React.Children.map(children, (c) => sanitizeNode(c))

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 md:flex">
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <TopNav />
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1440px] flex-1 px-3 py-4 md:px-6 md:py-6">
          {safeChildren}
        </main>
      </div>
    </div>
  )
}
