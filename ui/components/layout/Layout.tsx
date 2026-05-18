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
    <div className="min-h-screen flex bg-surface text-text">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopNav />
        <main id="main" className="p-4 md:p-6">{safeChildren}</main>
      </div>
    </div>
  )
}
