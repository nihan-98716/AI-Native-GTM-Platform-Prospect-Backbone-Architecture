"use client"

import React from "react"
import LoadingSpinner from "../common/LoadingSpinner"
import { useWorkflowDetail } from "../../hooks/useWorkflows"
import WorkflowTimeline from "./WorkflowTimeline"
import AgentTraces from "./AgentTraces"

function badgeClass(status: string) {
  const value = String(status).toLowerCase()
  if (value.includes("complete")) return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
  if (value.includes("fail")) return "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
  if (value.includes("queue") || value.includes("wait")) return "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
  return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
}

export default function WorkflowDetail({ id }: { id: string }) {
  const { detail, loading, error } = useWorkflowDetail(id)
  if (loading) return <div className="rounded-lg border bg-white p-6 dark:border-slate-800 dark:bg-slate-900"><LoadingSpinner /></div>
  if (error) return <div role="alert">Error: {error}</div>
  if (!detail) return <div className="rounded-lg border border-dashed bg-white p-6 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">No detail found.</div>

  const meta = detail.metadata || {}

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Run metadata</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Traceable workflow state and runtime evidence.</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${badgeClass(meta.status)}`}>{String(meta.status || 'unknown')}</span>
        </div>
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[
            ['ID', meta.workflow_run_id],
            ['Type', meta.workflow_type],
            ['Trace', meta.trace_id || '—'],
            ['Created', meta.created_at || '—'],
            ['Duration (ms)', meta.duration ?? '—'],
            ['Tenant', meta.tenant_id || '—'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-md border p-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</dt>
              <dd className="mt-1 break-all text-sm font-medium">{String(value)}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="rounded-lg border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Timeline</h3>
          <span className="text-sm text-slate-600 dark:text-slate-300">{(detail.timeline || []).length} steps</span>
        </div>
        <div className="mt-4">
          <WorkflowTimeline timeline={detail.timeline || []} />
        </div>
      </section>

      <section className="rounded-lg border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Agent traces</h3>
          <span className="text-sm text-slate-600 dark:text-slate-300">{(detail.tool_calls || []).length} calls</span>
        </div>
        <div className="mt-4">
          <AgentTraces toolCalls={detail.tool_calls || []} />
        </div>
      </section>
    </div>
  )
}
