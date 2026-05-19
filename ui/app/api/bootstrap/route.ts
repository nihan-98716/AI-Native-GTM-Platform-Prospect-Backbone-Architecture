import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'
  const response = await fetch(new URL('/v1/auth/bootstrap', baseUrl), { cache: 'no-store' })
  const body = await response.text()
  return new NextResponse(body, {
    status: response.status,
    headers: { 'content-type': response.headers.get('content-type') || 'application/json' },
  })
}
