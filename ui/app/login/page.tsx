"use client"

import React from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '../../hooks/useAuth'

function createTestToken(email: string): string {
  const now = Math.floor(Date.now() / 1000)
  const payload = {
    sub: email,
    tenant_id: 'test-enterprise-saas',
    roles: ['seller'],
    permissions: ['prospect:read', 'prospect:write', 'accounts:read'],
    exp: now + 60 * 60,
  }
  const base64Url = (obj: object) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
  return `${base64Url({ alg: 'none', typ: 'JWT' })}.${base64Url(payload)}.signature`
}

export default function LoginPage() {
  const router = useRouter()
  const { login, isAuthenticated } = useAuth()
  const [email, setEmail] = React.useState('test-seller@test-enterprise-saas.test')
  const [password, setPassword] = React.useState('')
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (isAuthenticated) router.replace('/dashboard')
  }, [isAuthenticated, router])

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.')
      return
    }
    const token = createTestToken(email.trim())
    login(token)
    setError(null)
    router.push('/dashboard')
  }

  return (
    <section className="max-w-md mx-auto mt-20 border rounded p-6 bg-white dark:bg-gray-900">
      <h1 className="text-2xl font-semibold mb-4">Login</h1>
      <form onSubmit={onSubmit} className="space-y-4" aria-label="Login form">
        <div>
          <label htmlFor="email" className="block mb-1">Email</label>
          <input
            id="email"
            name="email"
            data-testid="email-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border rounded px-3 py-2"
            autoComplete="email"
            required
          />
        </div>
        <div>
          <label htmlFor="password" className="block mb-1">Password</label>
          <input
            id="password"
            name="password"
            data-testid="password-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border rounded px-3 py-2"
            autoComplete="current-password"
            required
          />
        </div>
        {error ? <div role="alert" className="text-sm text-red-600">{error}</div> : null}
        <button type="submit" data-testid="login-submit" className="w-full border rounded px-3 py-2">
          Sign in
        </button>
      </form>
    </section>
  )
}
