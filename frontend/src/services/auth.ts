import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Separate instance — sem interceptors para evitar loop infinito no refresh
const authHttp = axios.create({ baseURL: BASE, timeout: 10_000 })

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface JwtPayload {
  sub: string
  role: string
  exp: number
  jti: string
}

export function parseJwt(token: string): JwtPayload {
  const [, payload] = token.split('.')
  return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as JwtPayload
}

export const authService = {
  login: (username: string, password: string) =>
    authHttp.post<TokenPair>('/auth/login', { username, password }).then((r) => r.data),

  refresh: (refreshToken: string) =>
    authHttp
      .post<TokenPair>('/auth/refresh', { refresh_token: refreshToken })
      .then((r) => r.data),

  logout: (refreshToken: string) =>
    authHttp.post('/auth/logout', { refresh_token: refreshToken }).catch(() => {}),
}

// Token storage helpers
const KEYS = { access: 'access_token', refresh: 'refresh_token' } as const

export const tokenStorage = {
  getAccess: () => localStorage.getItem(KEYS.access),
  getRefresh: () => localStorage.getItem(KEYS.refresh),
  set: (pair: TokenPair) => {
    localStorage.setItem(KEYS.access, pair.access_token)
    localStorage.setItem(KEYS.refresh, pair.refresh_token)
  },
  clear: () => {
    localStorage.removeItem(KEYS.access)
    localStorage.removeItem(KEYS.refresh)
  },
}
