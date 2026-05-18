import Protected from '../../components/common/Protected'
import WorkflowsList from '../../components/workflow/WorkflowsList'

export default function WorkflowsPage() {
  return (
    <>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Workflows</h1>
        <Protected requiredPermission="prospect:read">
          <WorkflowsList />
        </Protected>
      </div>
    </>
  )
}
