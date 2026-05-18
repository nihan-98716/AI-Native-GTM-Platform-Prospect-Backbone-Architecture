"use client"

import React from 'react'
import { useRouter } from 'next/navigation'

import KpiCard from '../components/cards/KpiCard'
import WorkflowSummary from '../components/workflow/WorkflowSummary'
import LoadingSpinner from '../components/common/LoadingSpinner'

export default function Page() {
  const router = useRouter()
  const [loading, setLoading] = React.useState(true)
  const [showStartDialog, setShowStartDialog] = React.useState(false)
  const [selectedIcp, setSelectedIcp] = React.useState('test-icp-1')
  const [selectedAccount, setSelectedAccount] = React.useState('test-account-1')

  React.useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600)
    return () => clearTimeout(t)
  }, [])

  React.useEffect(() => {
    if (!showStartDialog) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowStartDialog(false)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [showStartDialog])

  const startWorkflow = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const workflowId = `${selectedIcp}-${selectedAccount}`
    setShowStartDialog(false)
    router.push(`/workflows/${workflowId}`)
  }

  return (
    <>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Dashboard</h1>
        <div className="mb-4">
          <button type="button" className="px-3 py-2 border rounded" onClick={() => setShowStartDialog(true)}>
            Start Workflow
          </button>
        </div>
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
      {showStartDialog ? (
        <dialog
          open
          className="p-6 rounded border"
          aria-label="Start workflow"
          onCancel={() => setShowStartDialog(false)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setShowStartDialog(false)
          }}
        >
          <form onSubmit={startWorkflow} className="space-y-3">
            <h2 className="text-lg font-medium">Start Workflow</h2>
            <div>
              <label htmlFor="icp-id">ICP</label>
              <select
                id="icp-id"
                name="icp_id"
                value={selectedIcp}
                onChange={(e) => setSelectedIcp(e.target.value)}
                className="block border rounded p-2 w-full"
              >
                <option value="test-icp-1">test-icp-1</option>
              </select>
            </div>
            <div>
              <label htmlFor="account-id">Account</label>
              <select
                id="account-id"
                name="account_id"
                value={selectedAccount}
                onChange={(e) => setSelectedAccount(e.target.value)}
                className="block border rounded p-2 w-full"
              >
                <option value="test-account-1">test-account-1</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <button type="submit" className="px-3 py-2 border rounded">Start</button>
              <button type="button" className="px-3 py-2 border rounded" onClick={() => setShowStartDialog(false)}>
                Cancel
              </button>
            </div>
          </form>
        </dialog>
      ) : null}
    </>
  )
}
