import { NextRequest, NextResponse } from 'next/server'

function backendBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'
}

async function proxyJson(url: string, authorization: string | null) {
  const response = await fetch(url, {
    method: 'GET',
    headers: authorization ? { Authorization: authorization } : {},
    cache: 'no-store',
  })
  const body = await response.text()
  const contentType = response.headers.get('content-type') || 'application/json'
  return new NextResponse(body, {
    status: response.status,
    headers: { 'content-type': contentType },
  })
}

export async function GET(request: NextRequest) {
  const authorization = request.headers.get('authorization')
  const url = new URL('/v1/workflows/', backendBaseUrl())
  url.search = request.nextUrl.search
  return proxyJson(url.toString(), authorization)
}
