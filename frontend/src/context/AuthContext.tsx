import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { authService, tokenStorage, parseJwt, type JwtPayload } from '../services/auth'

interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  user: Pick<JwtPayload, 'sub' | 'role'> | null
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const REFRESH_BUFFER_MS = 2 * 60 * 1000 // refresh 2 min before expiry

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
  })
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function scheduleRefresh(accessToken: string) {
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    try {
      const { exp } = parseJwt(accessToken)
      const msUntilExpiry = exp * 1000 - Date.now()
      const delay = Math.max(0, msUntilExpiry - REFRESH_BUFFER_MS)

      refreshTimer.current = setTimeout(async () => {
        const refreshToken = tokenStorage.getRefresh()
        if (!refreshToken) return
        try {
          const pair = await authService.refresh(refreshToken)
          tokenStorage.set(pair)
          const payload = parseJwt(pair.access_token)
          setState((s) => ({ ...s, user: { sub: payload.sub, role: payload.role } }))
          scheduleRefresh(pair.access_token)
        } catch {
          tokenStorage.clear()
          setState({ isAuthenticated: false, isLoading: false, user: null })
        }
      }, delay)
    } catch {
      // invalid token — ignore
    }
  }

  // Restore session from stored refresh token on mount
  useEffect(() => {
    async function restoreSession() {
      const access = tokenStorage.getAccess()
      const refresh = tokenStorage.getRefresh()

      if (!refresh) {
        setState({ isAuthenticated: false, isLoading: false, user: null })
        return
      }

      try {
        // If access token still valid, use it; otherwise refresh
        if (access) {
          const payload = parseJwt(access)
          if (payload.exp * 1000 > Date.now() + 10_000) {
            setState({ isAuthenticated: true, isLoading: false, user: { sub: payload.sub, role: payload.role } })
            scheduleRefresh(access)
            return
          }
        }

        const pair = await authService.refresh(refresh)
        tokenStorage.set(pair)
        const payload = parseJwt(pair.access_token)
        setState({ isAuthenticated: true, isLoading: false, user: { sub: payload.sub, role: payload.role } })
        scheduleRefresh(pair.access_token)
      } catch {
        tokenStorage.clear()
        setState({ isAuthenticated: false, isLoading: false, user: null })
      }
    }

    restoreSession()

    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const pair = await authService.login(username, password)
    tokenStorage.set(pair)
    const payload = parseJwt(pair.access_token)
    setState({ isAuthenticated: true, isLoading: false, user: { sub: payload.sub, role: payload.role } })
    scheduleRefresh(pair.access_token)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh()
    if (refresh) await authService.logout(refresh)
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    tokenStorage.clear()
    setState({ isAuthenticated: false, isLoading: false, user: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
