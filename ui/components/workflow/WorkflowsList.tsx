"use client"

import React, { useMemo, useState } from "react"
import Link from "next/link"
import LoadingSpinner from "../common/LoadingSpinner"
import { useWorkflowList } from "../../hooks/useWorkflows"

export default function WorkflowsList() {
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState("")
  const [sortKey, setSortKey] = useState<"created_at" | "duration" | "workflow_status">("created_at")

  const { items, count, loading, error } = useWorkflowList(limit, offset)

  const filtered = useMemo(() => {
    return items.filter((i) => {
      const q = query.toLowerCase()
      return (
        (i.workflow_type || "").toLowerCase().includes(q) ||
        (i.trace_id || "").toLowerCase().includes(q) ||
        (i.tenant_id || "").toLowerCase().includes(q)
      )
    })
  }, [items, query])

  const sorted = useMemo(() => {
    const s = [...filtered]
    s.sort((a, b) => {
      if (sortKey === "duration") return (b.duration || 0) - (a.duration || 0)
      if (sortKey === "workflow_status") return (a.workflow_status || "").localeCompare(b.workflow_status || "")
      // created_at descending
      return String(b.created_at || "").localeCompare(String(a.created_at || ""))
    })
    return s
  }, [filtered, sortKey])

  if (loading) return <div className="p-6"><LoadingSpinner /></div>
  if (error) return <div role="alert">Error: {error}</div>
  if (!items || items.length === 0) return <div className="p-6 text-gray-600">No workflows found.</div>

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <input aria-label="Search workflows" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by type, trace or tenant" className="border rounded p-2 flex-1" />
        <select value={sortKey} onChange={(e) => setSortKey(e.target.value as any)} className="border rounded p-2">
          <option value="created_at">Newest</option>
          <option value="duration">Duration</option>
          <option value="workflow_status">Status</option>
        </select>
      </div>

      <table className="min-w-full table-auto">
        <thead>
          <tr className="text-left text-sm text-gray-500">
            <th className="p-2">ID</th>
            <th className="p-2">Type</th>
            <th className="p-2">Status</th>
            <th className="p-2">Tenant</th>
            <th className="p-2">Created</th>
            <th className="p-2">Updated</th>
            <th className="p-2">Duration</th>
            <th className="p-2">Trace</th>
            <th className="p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((w) => (
            <tr key={w.workflow_id} tabIndex={0} className="border-t hover:bg-gray-50 focus:bg-gray-100">
              <td className="p-2">
                <Link href={`/workflows/${w.workflow_id}`}>{w.workflow_id}</Link>
              </td>
              <td className="p-2">{w.workflow_type}</td>
              <td className="p-2">{String(w.workflow_status)}</td>
              <td className="p-2">{w.tenant_id}</td>
              <td className="p-2">{w.created_at ?? '-'}</td>
              <td className="p-2">{w.updated_at ?? '-'}</td>
              <td className="p-2">{w.duration ?? '-'}</td>
              <td className="p-2">{w.trace_id ?? '-'}</td>
              <td className="p-2"><Link href={`/workflows/${w.workflow_id}`} className="text-primary">Open</Link></td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-4 flex items-center gap-2">
        <button className="px-3 py-1 border rounded" onClick={() => setOffset(Math.max(0, offset - limit))} aria-label="Previous page">Prev</button>
        <div className="text-sm text-muted">Page {Math.floor(offset / limit) + 1} of {Math.max(1, Math.ceil(count / limit))}</div>
        <button className="px-3 py-1 border rounded" onClick={() => setOffset(offset + limit)} aria-label="Next page">Next</button>
      </div>
    </div>
  )
}
