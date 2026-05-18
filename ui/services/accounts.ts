import { buildUrl } from './api'

export type AccountSummary = { id: string; tenant_id: string; name: string; domain?: string; lifecycle_stage?: string }

export async function fetchAccounts({ limit = 50, offset = 0 }: { limit?: number; offset?: number }) {
  const url = buildUrl('/accounts', { limit, offset })
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API error ${res.status}`)
  const payload = await res.json()
  // payload is SuccessEnvelope { success: true, data: { items, count } }
  return payload.data
}
