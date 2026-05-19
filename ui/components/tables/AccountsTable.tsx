"use client"

import React from 'react'
import { Account } from '../../types'
import LoadingSpinner from '../common/LoadingSpinner'
import { useFetch } from '../../hooks/useFetch'

type SortKey = 'name' | 'domain' | 'lifecycle_stage'

function sortIndicator(key: SortKey, sortKey: SortKey) {
  if (key !== sortKey) return '↕'
  return '↕'
}

export default function AccountsTable() {
  const { fetchWithAuth } = useFetch()
  const [loading, setLoading] = React.useState(true)
  const [accounts, setAccounts] = React.useState<Account[]>([])
  const [limit, setLimit] = React.useState(20)
  const [offset, setOffset] = React.useState(0)
  const [query, setQuery] = React.useState('')
  const [sortKey, setSortKey] = React.useState<SortKey>('name')

  React.useEffect(() => {
    let mounted = true
    setLoading(true)
    fetchWithAuth(`/accounts?limit=${limit}&offset=${offset}`)
      .then((data) => {
        if (!mounted) return
        const payload = data?.data ?? data
        setAccounts(payload.items || [])
      })
      .catch(() => setAccounts([]))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [limit, offset, fetchWithAuth])

  const filtered = React.useMemo(() => {
    const q = query.toLowerCase()
    return accounts.filter(
      (account) =>
        account.name.toLowerCase().includes(q) ||
        (account.domain || '').toLowerCase().includes(q) ||
        (account.lifecycle_stage || '').toLowerCase().includes(q)
    )
  }, [accounts, query])

  const sorted = React.useMemo(() => {
    return [...filtered].sort((x, y) => {
      const left = (x[sortKey] || '').toString().toLowerCase()
      const right = (y[sortKey] || '').toString().toLowerCase()
      return left.localeCompare(right)
    })
  }, [filtered, sortKey])

  const empty = !loading && sorted.length === 0

  return (
    <section className="rounded-lg border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-base font-semibold">Accounts</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Filter and inspect tenant-owned accounts.</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <label className="flex-1">
            <span className="sr-only">Search accounts</span>
            <input
              aria-label="Search accounts"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search"
              className="min-h-11 w-full rounded-md border bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <span>Per page</span>
            <select
              value={limit}
              onChange={(e) => {
                setOffset(0)
                setLimit(Number(e.target.value))
              }}
              className="min-h-11 rounded-md border bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
            >
              {[10, 20, 50].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 rounded-md border p-6">
          <LoadingSpinner />
        </div>
      ) : empty ? (
        <div className="mt-4 rounded-md border border-dashed p-6 text-sm text-slate-600 dark:text-slate-300">
          No accounts matched the current filters.
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full table-fixed border-separate border-spacing-0">
            <caption className="sr-only">Accounts list</caption>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {[
                  ['name', 'Name'],
                  ['domain', 'Domain'],
                  ['lifecycle_stage', 'Lifecycle'],
                ].map(([key, label]) => (
                  <th key={key} scope="col" className="border-b px-3 py-3">
                    <button
                      type="button"
                      onClick={() => setSortKey(key as SortKey)}
                      className="inline-flex items-center gap-2 rounded px-1 py-0.5 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 dark:hover:bg-slate-800"
                      aria-label={`Sort by ${label}`}
                    >
                      {label}
                      <span aria-hidden>{sortIndicator(key as SortKey, sortKey)}</span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((account) => (
                <tr
                  key={account.id}
                  tabIndex={0}
                  className="cursor-default border-b border-slate-100 hover:bg-slate-50 focus-within:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-950 dark:focus-within:bg-slate-950"
                >
                  <td className="px-3 py-3 font-medium">{account.name}</td>
                  <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{account.domain || '—'}</td>
                  <td className="px-3 py-3 text-slate-600 dark:text-slate-300">{account.lifecycle_stage || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Showing {sorted.length} account{sorted.length === 1 ? '' : 's'}
        </p>
        <div className="flex items-center gap-2">
          <button
            className="min-h-11 rounded-md border px-3 text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 dark:border-slate-700 dark:hover:bg-slate-800"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            aria-label="Previous page"
            disabled={offset === 0}
          >
            Prev
          </button>
          <button
            className="min-h-11 rounded-md border px-3 text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 dark:border-slate-700 dark:hover:bg-slate-800"
            onClick={() => setOffset(offset + limit)}
            aria-label="Next page"
            disabled={sorted.length < limit}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  )
}
