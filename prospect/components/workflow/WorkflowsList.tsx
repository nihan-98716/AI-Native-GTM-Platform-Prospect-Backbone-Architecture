"use client"

import React, { useMemo, useState } from 'react'
import Link from 'next/link'
import LoadingSpinner from '../common/LoadingSpinner'
import { useWorkflowList } from '../../hooks/useWorkflows'

type SortKey = 'created_at' | 'duration' | 'workflow_status'

function statusClass(status: string) {
  const value = status.toLowerCase()
  if (value.includes('complete')) return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (value.includes('fail')) return 'bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
  if (value.includes('queue') || value.includes('wait')) return 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
  return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200'
}

export default function WorkflowsList() {
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('created_at')

  const { items, count, loading, error } = useWorkflowList(limit, offset)

  const filtered = useMemo(() => {
    return items.filter((i) => {
      const q = query.toLowerCase()
      return (
        (i.workflow_type || '').toLowerCase().includes(q) ||
        (i.trace_id || '').toLowerCase().includes(q) ||
        (i.tenant_id || '').toLowerCase().includes(q) ||
        (i.workflow_status || '').toLowerCase().includes(q)
      )
    })
  }, [items, query])

  const sorted = useMemo(() => {
    const s = [...filtered]
    s.sort((a, b) => {
      if (sortKey === 'duration') return (b.duration || 0) - (a.duration || 0)
      if (sortKey === 'workflow_status') return (a.workflow_status || '').localeCompare(b.workflow_status || '')
      return String(b.created_at || '').localeCompare(String(a.created_at || ''))
    })
    return s
  }, [filtered, sortKey])

  if (loading) return <div className="rounded-lg border bg-white p-6 dark:border-slate-800 dark:bg-slate-900"><LoadingSpinner /></div>
  if (error) return <div role="alert">Error: {error}</div>
  if (!items || items.length === 0) return <div className="rounded-lg border border-dashed bg-white p-6 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">No workflows found.</div>

  return (
    <section className="rounded-lg border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-base font-semibold">Workflow runs</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Inspect execution history, trace IDs, and run state.</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            aria-label="Search workflows"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by type, trace or tenant"
            className="min-h-11 rounded-md border bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="min-h-11 rounded-md border bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="created_at">Newest</option>
            <option value="duration">Duration</option>
            <option value="workflow_status">Status</option>
          </select>
          <select
            value={limit}
            onChange={(e) => {
              setOffset(0)
              setLimit(Number(e.target.value))
            }}
            className="min-h-11 rounded-md border bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
          >
            {[10, 20, 50].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-0">
          <caption className="sr-only">Workflow runs</caption>
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
              <th scope="col" className="border-b px-3 py-3">ID</th>
              <th scope="col" className="border-b px-3 py-3">Type</th>
              <th scope="col" className="border-b px-3 py-3">Status</th>
              <th scope="col" className="border-b px-3 py-3">Tenant</th>
              <th scope="col" className="border-b px-3 py-3">Created</th>
              <th scope="col" className="border-b px-3 py-3">Duration</th>
              <th scope="col" className="border-b px-3 py-3">Trace</th>
              <th scope="col" className="border-b px-3 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((w) => (
              <tr key={w.workflow_id} tabIndex={0} className="border-b border-slate-100 hover:bg-slate-50 focus-within:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-950 dark:focus-within:bg-slate-950">
                <td className="px-3 py-3 font-medium">
                  <Link href={`/workflows/${w.workflow_id}`} className="rounded px-1 py-0.5 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800">
                    {w.workflow_id}
                  </Link>
                </td>
                <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{w.workflow_type}</td>
                <td className="px-3 py-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClass(String(w.workflow_status))}`}>{String(w.workflow_status)}</span>
                </td>
                <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{w.tenant_id}</td>
                <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{w.created_at ?? '—'}</td>
                <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{w.duration ?? '—'}</td>
                <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{w.trace_id ?? '—'}</td>
                <td className="px-3 py-3">
                  <Link href={`/workflows/${w.workflow_id}`} className="text-sm font-medium text-slate-900 underline-offset-4 hover:underline dark:text-slate-100">
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Showing {sorted.length} of {count} runs
        </p>
        <div className="flex items-center gap-2">
          <button className="min-h-11 rounded-md border px-3 text-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800" onClick={() => setOffset(Math.max(0, offset - limit))} aria-label="Previous page" disabled={offset === 0}>
            Prev
          </button>
          <button className="min-h-11 rounded-md border px-3 text-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800" onClick={() => setOffset(offset + limit)} aria-label="Next page" disabled={sorted.length < limit}>
            Next
          </button>
        </div>
      </div>
    </section>
  )
}
