import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import {
  getAccessToken,
  setAccessToken,
  setRefreshToken,
  setUnauthorizedHandler,
  USER_KEY,
} from '../api/client'
import { fetchMe, login as apiLogin, logout as apiLogout } from '../api/endpoints'
import type { User } from '../api/types'

type AuthState = {
  status: 'loading' | 'anonymous' | 'authenticated'
  user: User | null
  login: (login: string, password: string) => Promise<void>
  logout: () => void
}

const AuthCtx = createContext<AuthState | null>(null)

// Доступ в веб: администратор ИЛИ пользователь, которому назначена хотя бы одна
// роль на складе (= сотрудник). Обычный чат-пользователь без ролей в веб не
// заходит. Управление правами (страница «Пользователи» и пр.) остаётся под
// проверкой user_admin отдельно.
export function hasWebAccess(user: User): boolean {
  return user.user_admin || (user.user_establishment_roles?.length ?? 0) > 0
}

function readStoredUser(): User | null {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) ?? 'null')
  } catch {
    return null
  }
}

function storeUser(user: User | null) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('loading')
  const [user, setUser] = useState<User | null>(readStoredUser())

  const signOut = useCallback(() => {
    setAccessToken('')
    setRefreshToken('')
    storeUser(null)
    setUser(null)
    setStatus('anonymous')
  }, [])

  // Любой 401 в приложении -> разлогин.
  useEffect(() => {
    setUnauthorizedHandler(signOut)
    return () => setUnauthorizedHandler(null)
  }, [signOut])

  // Валидация существующего токена при старте.
  useEffect(() => {
    let cancelled = false
    if (!getAccessToken()) {
      setStatus('anonymous')
      return
    }
    fetchMe()
      .then(({ user }) => {
        if (cancelled) return
        if (!hasWebAccess(user)) {
          signOut()
          return
        }
        storeUser(user)
        setUser(user)
        setStatus('authenticated')
      })
      .catch(() => {
        if (!cancelled) signOut()
      })
    return () => {
      cancelled = true
    }
  }, [signOut])

  const login = useCallback(async (loginValue: string, password: string) => {
    const res = await apiLogin(loginValue, password)
    if (!hasWebAccess(res.user)) {
      throw new Error('Нет доступа в веб: обратитесь к администратору за назначением роли')
    }
    setAccessToken(res.access_token ?? res.token ?? '')
    setRefreshToken(res.refresh_token ?? '')
    storeUser(res.user)
    setUser(res.user)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(() => {
    void apiLogout()
    signOut()
  }, [signOut])

  const value = useMemo<AuthState>(
    () => ({ status, user, login, logout }),
    [status, user, login, logout],
  )

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('useAuth вне AuthProvider')
  return ctx
}
