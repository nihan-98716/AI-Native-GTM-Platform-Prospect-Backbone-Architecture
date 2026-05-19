"use client"

import React from 'react'

import KpiCard from '../components/cards/KpiCard'
import WorkflowSummary from '../components/workflow/WorkflowSummary'
import LoadingSpinner from '../components/common/LoadingSpinner'

export default function Page() {
  const [loading, setLoading] = React.useState(true)
  const kpis = [
    { title: 'Active Workflows', value: 12, trend: '+2 today' },
    { title: 'Open Approvals', value: 4, trend: '2 urgent' },
    { title: 'Integration Health', value: '99.2%', trend: 'All providers online' },
    { title: 'Avg Runtime', value: '1.8m', trend: '-12% this week' },
  ]

  React.useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600)
    return () => clearTimeout(t)
  }, [])

  return (
    <>
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Operational view of workflow execution, approvals, and integration reliability.
          </p>
        </header>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="KPI cards">
          {loading ? (
            <div className="col-span-1 flex min-h-28 items-center justify-center rounded-lg border bg-white p-6 md:col-span-2 xl:col-span-4 dark:bg-slate-900"><LoadingSpinner /></div>
          ) : (
            <>
              {kpis.map((kpi) => (
              <KpiCard key={kpi.title} title={kpi.title} value={kpi.value} trend={kpi.trend} />
              ))}
            </>
          )}
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <article className="rounded-lg border bg-white p-4 dark:bg-slate-900 xl:col-span-2">
            <h2 className="text-base font-semibold">Recent Activity</h2>
            {loading ? (
              <div className="mt-4 min-h-28 rounded-md border p-6"><LoadingSpinner /></div>
            ) : (
              <ol className="mt-4 space-y-3 text-sm">
                <li className="rounded-md border p-3">
                  <p className="font-medium">Prospect workflow wf_98 transitioned to running</p>
                  <p className="mt-1 text-slate-600 dark:text-slate-300">Trace tr_1f4a persisted with agent step evidence and approval context.</p>
                </li>
                <li className="rounded-md border p-3">
                  <p className="font-medium">Integration sync completed for Apollo provider</p>
                  <p className="mt-1 text-slate-600 dark:text-slate-300">234 account updates ingested without tenant isolation violations.</p>
                </li>
              </ol>
            )}
          </article>

          <article className="rounded-lg border bg-white p-4 dark:bg-slate-900">
            <h2 className="text-base font-semibold">System Health</h2>
            {loading ? (
              <div className="mt-4 min-h-28 rounded-md border p-6"><LoadingSpinner /></div>
            ) : (
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between rounded-md border p-3">
                  <dt className="text-slate-600 dark:text-slate-300">Queue latency</dt>
                  <dd className="font-medium">420ms</dd>
                </div>
                <div className="flex items-center justify-between rounded-md border p-3">
                  <dt className="text-slate-600 dark:text-slate-300">Audit write success</dt>
                  <dd className="font-medium">100%</dd>
                </div>
                <div className="flex items-center justify-between rounded-md border p-3">
                  <dt className="text-slate-600 dark:text-slate-300">Trace persistence</dt>
                  <dd className="font-medium">Healthy</dd>
                </div>
              </dl>
            )}
          </article>
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <article className="rounded-lg border bg-white p-4 dark:bg-slate-900">
            <h2 className="text-base font-semibold">Workflow Summary</h2>
            <div className="mt-3">
              <WorkflowSummary loading={loading} />
            </div>
          </article>

          <article className="rounded-lg border bg-white p-4 dark:bg-slate-900">
            <h2 className="text-base font-semibold">Audit Activity</h2>
            {loading ? (
              <div className="mt-4 min-h-24 rounded-md border p-6"><LoadingSpinner /></div>
            ) : (
              <ul className="mt-4 space-y-2 text-sm">
                <li className="rounded-md border p-3">approval.granted recorded for workflow wf_97</li>
                <li className="rounded-md border p-3">integration.sync.failed recorded with retry metadata</li>
                <li className="rounded-md border p-3">workflow.requeued event recorded from fallback state</li>
              </ul>
            )}
          </article>
        </section>
      </div>
    </>
  )
}
