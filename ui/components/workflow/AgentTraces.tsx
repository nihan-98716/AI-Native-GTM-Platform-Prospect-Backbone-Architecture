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

export default function AgentTraces({ toolCalls }: { toolCalls: any[] }) {
  if (!toolCalls || toolCalls.length === 0) return <div className="p-4 text-gray-600">No tool calls</div>
  return (
    <div className="space-y-3">
      {toolCalls.map((call: any) => (
        <div key={call.tool_call_id || call.tool_name} className="p-3 border rounded">
          <div className="flex justify-between items-start">
            <div>
              <div className="font-medium">{call.tool_name}</div>
              <div className="text-sm text-gray-500">{call.status} · trace {call.trace_id || '-'}</div>
            </div>
            <div className="text-xs text-gray-400">{call.correlation_id || ''}</div>
          </div>
          <details className="mt-2">
            <summary className="cursor-pointer">Inputs / outputs (redacted)</summary>
            <pre className="mt-2 text-xs overflow-auto">{JSON.stringify(redact({ input: call.input, output: call.output }), null, 2)}</pre>
          </details>
        </div>
      ))}
    </div>
  )
}
