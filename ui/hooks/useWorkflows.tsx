"use client"

import React, { useState, useEffect } from "react"
import { useFetch } from "./useFetch"

export type WorkflowSummary = {
  workflow_id: string
  workflow_type: string
  workflow_status: string
  created_at?: string
  updated_at?: string
  duration?: number
  tenant_id?: string
  trace_id?: string
}

export type WorkflowDetail = {
  metadata: any
  timeline: any[]
  tool_calls: any[]
  audit_references: string[]
}

export function useWorkflowList(limit = 50, offset = 0) {
  const { fetchWithAuth } = useFetch()
  const [items, setItems] = useState<WorkflowSummary[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    fetchWithAuth(`/v1/workflows?limit=${limit}&offset=${offset}`)
      .then((resp: any) => {
        const data = resp?.data || resp
        setItems(data?.items || [])
        setCount(data?.count || 0)
      })
      .catch((e: any) => setError(String(e)))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [limit, offset, fetchWithAuth])

  return { items, count, loading, error }
}

export function useWorkflowDetail(id: string | null) {
  const { fetchWithAuth } = useFetch()
  const [detail, setDetail] = useState<WorkflowDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let mounted = true
    setLoading(true)
    fetchWithAuth(`/v1/workflows/${id}`)
      .then((resp: any) => {
        const data = resp?.data || resp
        if (mounted) setDetail(data)
      })
      .catch((e: any) => setError(String(e)))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [id, fetchWithAuth])

  return { detail, loading, error }
}
