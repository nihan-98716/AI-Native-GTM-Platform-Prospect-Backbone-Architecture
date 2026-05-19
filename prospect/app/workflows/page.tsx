import Protected from '../../components/common/Protected'
import WorkflowsList from '../../components/workflow/WorkflowsList'

export default function WorkflowsPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Workflows</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Track workflow runs, states, and trace context.</p>
      </header>
      <div>
        <Protected requiredPermission="prospect:read">
          <WorkflowsList />
        </Protected>
      </div>
    </div>
  )
}
