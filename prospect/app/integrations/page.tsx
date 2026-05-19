import React from 'react'

export default function IntegrationsPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Integrations</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Provider connectivity and sync status for the current tenant.</p>
      </header>

      <section className="rounded-lg border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-base font-semibold">Connected providers</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <article className="rounded-md border p-4">
            <div className="text-sm font-medium">Apollo</div>
            <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">Available for prospect enrichment and sync workflows.</div>
          </article>
          <article className="rounded-md border p-4">
            <div className="text-sm font-medium">Status</div>
            <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">Configured through the backend provider registry.</div>
          </article>
          <article className="rounded-md border p-4">
            <div className="text-sm font-medium">Sync health</div>
            <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">View tenant-scoped integration readiness from the shell.</div>
          </article>
        </div>
      </section>
    </div>
  )
}
