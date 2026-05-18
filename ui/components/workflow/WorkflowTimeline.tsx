"use client"

import React, { useState } from "react"

export default function WorkflowTimeline({ timeline }: { timeline: any[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const toggle = (id: string) => setExpanded((s) => ({ ...s, [id]: !s[id] }))

  if (!timeline || timeline.length === 0) return <div className="p-4 text-gray-600">No timeline entries</div>

  return (
    <ol className="space-y-3">
      {timeline.map((step: any, idx: number) => {
        const id = step.workflow_step_id || step.step_name || String(idx)
        const isOpen = !!expanded[id]
        return (
          <li key={id}>
            <div
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter") toggle(id) }}
              className="p-3 border rounded flex justify-between items-start focus:outline focus:outline-2 focus:outline-primary"
              aria-expanded={isOpen}
            >
              <div>
                <div className="font-medium">{step.step_name}</div>
                <div className="text-sm text-gray-500">{step.status} · trace {step.trace_id || '-'}</div>
              </div>
              <div className="text-sm">
                <button onClick={() => toggle(id)} className="px-2 py-1 border rounded">{isOpen ? 'Hide' : 'Show'}</button>
              </div>
            </div>
            {isOpen && (
              <pre className="p-3 mt-2 bg-gray-50 rounded text-xs overflow-auto" aria-live="polite">{JSON.stringify(step, null, 2)}</pre>
            )}
          </li>
        )
      })}
    </ol>
  )
}
