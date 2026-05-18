"use client"

import React from 'react'

import KpiCard from '../components/cards/KpiCard'
import WorkflowSummary from '../components/workflow/WorkflowSummary'
import LoadingSpinner from '../components/common/LoadingSpinner'

export default function Page() {
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600)
    return () => clearTimeout(t)
  }, [])

  return (
    <>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Dashboard</h1>
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {loading ? (
            <div className="col-span-1 md:col-span-3 flex items-center justify-center p-6 border rounded"><LoadingSpinner /></div>
          ) : (
            <>
              <KpiCard title="Active Workflows" value="—" />
              <KpiCard title="Open Approvals" value="—" />
              <KpiCard title="Integration Health" value="—" />
            </>
          )}
        </section>

        <section className="mb-6">
          <h2 className="text-xl font-medium mb-2">Recent Activity</h2>
          {loading ? (
            <div className="p-6 border rounded"><LoadingSpinner /></div>
          ) : (
            <div className="p-6 border rounded text-sm text-gray-600">No recent activity</div>
          )}
        </section>

        <section>
          <h2 className="text-xl font-medium mb-2">Workflow Summary</h2>
          <WorkflowSummary loading={loading} />
        </section>
      </div>
    </>
  )
}
