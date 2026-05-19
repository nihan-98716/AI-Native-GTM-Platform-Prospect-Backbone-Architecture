"use client"

import React from 'react'

export default function KpiCard({
  title,
  value,
  trend,
}: {
  title: string
  value: string | number
  trend?: string
}) {
  return (
    <article className="rounded-lg border bg-white p-4 shadow-sm transition-colors dark:border-slate-800 dark:bg-slate-900">
      <div className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</div>
      <div className="mt-2 text-3xl font-semibold tracking-tight">{value}</div>
      {trend ? <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">{trend}</div> : null}
      <div className="mt-4 h-1 rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-1 w-2/3 rounded-full bg-slate-900 dark:bg-slate-100" aria-hidden />
      </div>
    </article>
  )
}
