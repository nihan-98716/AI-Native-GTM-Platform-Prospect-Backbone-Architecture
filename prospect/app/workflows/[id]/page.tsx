
import Protected from '../../../components/common/Protected'
import WorkflowDetail from '../../../components/workflow/WorkflowDetail'

export default function WorkflowDetailPage({ params }: { params: { id: string } }) {
  const { id } = params
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Workflow</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Inspect timeline steps, trace calls, and persisted metadata.</p>
      </header>
      <div>
        <Protected requiredPermission="prospect:read">
          <WorkflowDetail id={id} />
        </Protected>
      </div>
    </div>
  )
}
