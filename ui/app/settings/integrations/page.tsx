"use client"

import React from 'react'
import Protected from '../../../components/common/Protected'

const providers = [
  { name: 'Apollo', status: 'Connected', health: 'Healthy', lastSync: '5 minutes ago' },
  { name: 'HubSpot', status: 'Failed', health: 'Unhealthy', lastSync: '3 days ago' },
]

export default function IntegrationsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Integrations</h1>
      <Protected requiredPermission="prospect:read">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map((provider) => (
            <article key={provider.name} data-testid="provider-card" className="border rounded p-4">
              <h2 className="text-lg font-medium">{provider.name}</h2>
              <div data-testid="status-badge" className="mt-2">{provider.status}</div>
              <div data-testid="health-status" className="text-sm text-gray-600 mt-1">{provider.health}</div>
              <div data-testid="last-sync" className="text-sm text-gray-600 mt-1">{provider.lastSync}</div>
            </article>
          ))}
        </div>
      </Protected>
    </div>
  )
}
