"use client"

import React from 'react'
import LoadingSpinner from '../common/LoadingSpinner'

export default function WorkflowSummary({ loading = false }: { loading?: boolean }) {
  if (loading) {
    return (
      <div className="p-4 border rounded"><LoadingSpinner /></div>
    )
  }

  return (
    <div className="p-4 border rounded">
      <div className="text-sm text-gray-600">No recent workflow runs</div>
    </div>
  )
}
