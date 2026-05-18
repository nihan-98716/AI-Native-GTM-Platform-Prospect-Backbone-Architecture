"use client"

import React from 'react'

export default function KpiCard({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="p-4 border rounded bg-white dark:bg-gray-800">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  )
}
