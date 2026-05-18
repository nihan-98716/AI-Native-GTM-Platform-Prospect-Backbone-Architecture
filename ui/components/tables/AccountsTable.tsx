"use client"

import React from 'react'
import { Account } from '../../types'
import LoadingSpinner from '../common/LoadingSpinner'
import { useFetch } from '../../hooks/useFetch'

export default function AccountsTable() {
  const { fetchWithAuth } = useFetch()
  const [loading, setLoading] = React.useState(true)
  const [accounts, setAccounts] = React.useState<Account[]>([])
  const [limit, setLimit] = React.useState(20)
  const [offset, setOffset] = React.useState(0)
  const [query, setQuery] = React.useState('')
  const [sortKey, setSortKey] = React.useState<'name' | 'domain'>('name')

  React.useEffect(() => {
    let mounted = true
    setLoading(true)
    fetchWithAuth(`/accounts?limit=${limit}&offset=${offset}`)
      .then((data) => {
        if (!mounted) return
        setAccounts(data.items || [])
      })
      .catch(() => setAccounts([]))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [limit, offset, fetchWithAuth])

  const filtered = accounts.filter((a) => a.name.toLowerCase().includes(query.toLowerCase()) || (a.domain || '').toLowerCase().includes(query.toLowerCase()))
  const sorted = filtered.sort((x, y) => (x[sortKey] || '').localeCompare(y[sortKey] || ''))

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <input aria-label="Search accounts" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search" className="border rounded p-2 flex-1" />
        <select value={sortKey} onChange={(e) => setSortKey(e.target.value as any)} className="border rounded p-2">
          <option value="name">Name</option>
          <option value="domain">Domain</option>
        </select>
      </div>

      {loading ? (
        <div className="p-6 border rounded"><LoadingSpinner /></div>
      ) : sorted.length === 0 ? (
        <div className="p-6 border rounded text-gray-600">No accounts found.</div>
      ) : (
        <table className="min-w-full table-auto"> 
          <thead>
            <tr className="text-left text-sm text-gray-500">
              <th className="p-2">Name</th>
              <th className="p-2">Domain</th>
              <th className="p-2">Lifecycle</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((a) => (
              <tr key={a.id} tabIndex={0} className="border-t hover:bg-gray-50 focus:bg-gray-100">
                <td className="p-2">{a.name}</td>
                <td className="p-2">{a.domain || '-'}</td>
                <td className="p-2">{a.lifecycle_stage || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="mt-4 flex items-center gap-2">
        <button className="px-3 py-1 border rounded" onClick={() => setOffset(Math.max(0, offset - limit))} aria-label="Previous page">Prev</button>
        <button className="px-3 py-1 border rounded" onClick={() => setOffset(offset + limit)} aria-label="Next page">Next</button>
      </div>
    </div>
  )
}
