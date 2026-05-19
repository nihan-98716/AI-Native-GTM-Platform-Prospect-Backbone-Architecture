"use client"

import React from "react"

function redact(obj: any): any {
  const blacklist = ["api_key", "apikey", "apiKey", "token", "access_token", "refresh_token", "secret", "authorization", "auth", "credentials"]
  if (obj === null || obj === undefined) return obj
  if (typeof obj === "string") {
    if (obj.length > 200) return "[REDACTED]"
    const lowered = obj.toLowerCase()
    for (const k of ["api_key", "token", "secret", "authorization"]) if (lowered.includes(k)) return "[REDACTED]"
    return obj
  }
  if (typeof obj !== "object") return obj
  if (Array.isArray(obj)) return obj.map(redact)
  const out: any = {}
  for (const [k, v] of Object.entries(obj)) {
    if (blacklist.some((b) => k.toLowerCase().includes(b))) out[k] = "[REDACTED]"
    else out[k] = redact(v)
  }
  return out
}

function statusClass(status: string) {
  const value = String(status).toLowerCase()
  if (value.includes("complete")) return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
  if (value.includes("fail")) return "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
  if (value.includes("queue") || value.includes("wait")) return "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
  return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
}

export default function AgentTraces({ toolCalls }: { toolCalls: any[] }) {
  if (!toolCalls || toolCalls.length === 0) return <div className="text-sm text-slate-600 dark:text-slate-300">No tool calls</div>
  return (
    <div className="grid gap-3">
      {toolCalls.map((call: any) => (
        <article key={call.tool_call_id || call.tool_name} className="rounded-lg border p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="font-medium">{call.tool_name}</div>
              <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">Trace {call.trace_id || '-'} · Correlation {call.correlation_id || '-'}</div>
            </div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClass(call.status)}`}>{call.status}</span>
          </div>
          <details className="mt-3 rounded-md border p-3">
            <summary className="cursor-pointer text-sm font-medium">Inputs / outputs (redacted)</summary>
            <pre className="mt-3 overflow-auto text-xs">{JSON.stringify(redact({ input: call.input, output: call.output }), null, 2)}</pre>
          </details>
        </article>
      ))}
    </div>
  )
}
