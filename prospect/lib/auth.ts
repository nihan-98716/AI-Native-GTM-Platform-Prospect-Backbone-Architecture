type Claims = { sub?: string; tenant_id?: string; roles?: string[]; permissions?: string[]; exp?: number }

function base64UrlDecode(input: string) {
  // base64url -> base64
  input = input.replace(/-/g, '+').replace(/_/g, '/')
  while (input.length % 4 !== 0) {
    input += '='
  }
  try {
    return decodeURIComponent(
      atob(input)
        .split('')
        .map(function (c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
        })
        .join('')
    )
  } catch (e) {
    return null
  }
}

export function decodeJwt(token: string): Claims | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const payload = parts[1]
    const decoded = base64UrlDecode(payload)
    if (!decoded) return null
    return JSON.parse(decoded)
  } catch (e) {
    return null
  }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

export function getBootstrapToken(): string | null {
  return process.env.NEXT_PUBLIC_BOOTSTRAP_TOKEN || null
}

export function setToken(token: string | null): void {
  if (typeof window === 'undefined') return
  if (token) localStorage.setItem('token', token)
  else localStorage.removeItem('token')
}

export function isTokenExpired(token: string | null): boolean {
  if (!token) return true
  const claims = decodeJwt(token)
  if (!claims) return true
  if (!claims.exp) return true
  const now = Math.floor(Date.now() / 1000)
  return claims.exp <= now
}

export function getClaims(token?: string | null): Claims | null {
  const t = token ?? getToken()
  if (!t) return null
  return decodeJwt(t)
}

export function hasPermission(claims: Claims | null, permission: string): boolean {
  if (!claims) return false
  if (!claims.permissions) return false
  return claims.permissions.includes(permission)
}

export function hasRole(claims: Claims | null, role: string): boolean {
  if (!claims) return false
  if (!claims.roles) return false
  return claims.roles.includes(role)
}
