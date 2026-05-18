"use client"

import React from "react"
import LoadingSpinner from "../common/LoadingSpinner"
import { useWorkflowDetail } from "../../hooks/useWorkflows"
import WorkflowTimeline from "./WorkflowTimeline"
import AgentTraces from "./AgentTraces"

export default function WorkflowDetail({ id }: { id: string }) {
  const { detail, loading, error } = useWorkflowDetail(id)
  if (loading) return <div className="p-6"><LoadingSpinner /></div>
  if (error) return <div role="alert">Error: {error}</div>
  if (!detail) return <div className="p-6 text-gray-600">No detail found.</div>

  const meta = detail.metadata || {}

  return (
    <div className="space-y-6">
      <section className="p-4 border rounded">
        <h2 className="text-lg font-medium mb-2">Metadata</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <dt className="font-semibold">ID</dt>
            <dd>{meta.workflow_run_id}</dd>
          </div>
          <div>
            <dt className="font-semibold">Status</dt>
            <dd>{String(meta.status)}</dd>
          </div>
          <div>
            <dt className="font-semibold">Type</dt>
            <dd>{meta.workflow_type}</dd>
          </div>
          <div>
            <dt className="font-semibold">Trace</dt>
            <dd>{meta.trace_id || '-'}</dd>
          </div>
          <div>
            <dt className="font-semibold">Created</dt>
            <dd>{meta.created_at || '-'}</dd>
          </div>
          <div>
            <dt className="font-semibold">Duration (ms)</dt>
            <dd>{meta.duration ?? '-'}</dd>
          </div>
        </dl>
      </section>

      <section className="p-4 border rounded">
        <h3 className="font-medium mb-2">Timeline</h3>
        <WorkflowTimeline timeline={detail.timeline || []} />
      </section>

      <section className="p-4 border rounded">
        <h3 className="font-medium mb-2">Agent traces</h3>
        <AgentTraces toolCalls={detail.tool_calls || []} />
      </section>
    </div>
  )
}
