"use client"

import React from 'react'

import AccountsTable from '../../components/tables/AccountsTable'
import Protected from '../../components/common/Protected'

export default function AccountsPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Accounts</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Review account records with tenant-safe filtering and pagination.</p>
      </header>
      <div>
        <Protected requiredPermission="accounts:read">
          <AccountsTable />
        </Protected>
      </div>
    </div>
  )
}
