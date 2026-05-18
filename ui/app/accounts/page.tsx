"use client"

import React from 'react'

import AccountsTable from '../../components/tables/AccountsTable'
import Protected from '../../components/common/Protected'

export default function AccountsPage() {
  return (
    <>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Accounts</h1>
        <Protected requiredPermission="accounts:read">
          <AccountsTable />
        </Protected>
      </div>
    </>
  )
}
