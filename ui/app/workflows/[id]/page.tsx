
import Protected from '../../../components/common/Protected'
import WorkflowDetail from '../../../components/workflow/WorkflowDetail'

export default function WorkflowDetailPage({ params }: { params: { id: string } }) {
  const { id } = params
  return (
    <>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Workflow</h1>
        <Protected requiredPermission="prospect:read">
          <WorkflowDetail id={id} />
        </Protected>
      </div>
    </>
  )
}
