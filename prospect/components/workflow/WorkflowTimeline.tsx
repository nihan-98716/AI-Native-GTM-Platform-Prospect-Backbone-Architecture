"use client"

import React, { useState } from "react"

function stepBadge(status: string) {
  const value = String(status).toLowerCase()
  if (value.includes("complete")) return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
  if (value.includes("fail")) return "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
  if (value.includes("queue") || value.includes("wait")) return "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
  return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
}

export default function WorkflowTimeline({ timeline }: { timeline: any[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const toggle = (id: string) => setExpanded((s) => ({ ...s, [id]: !s[id] }))

  if (!timeline || timeline.length === 0) return <div className="text-sm text-slate-600 dark:text-slate-300">No timeline entries</div>

  return (
    <ol className="space-y-4">
      {timeline.map((step: any, idx: number) => {
        const id = step.workflow_step_id || step.step_name || String(idx)
        const isOpen = !!expanded[id]
        return (
          <li key={id} className="relative pl-5">
            <span className="absolute left-1.5 top-3 h-full w-px bg-slate-200 dark:bg-slate-800" aria-hidden />
            <div className="rounded-lg border p-4">
              <button
                type="button"
                onClick={() => toggle(id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    toggle(id)
                  }
                }}
                className="flex w-full items-start justify-between gap-3 text-left focus-visible:outline-none focus-visible:ring-2"
                aria-expanded={isOpen}
              >
                <div>
                  <div className="font-medium">{step.step_name}</div>
                  <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{step.trace_id || '-'} · {step.status}</div>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${stepBadge(step.status)}`}>{step.status}</span>
              </button>
              {isOpen ? (
                <pre className="mt-3 overflow-auto rounded-md bg-slate-50 p-3 text-xs dark:bg-slate-950" aria-live="polite">
                  {JSON.stringify(step, null, 2)}
                </pre>
              ) : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
