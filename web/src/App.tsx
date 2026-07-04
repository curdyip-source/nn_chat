import { useEffect } from 'react'
import { AppShell } from './app/AppShell'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { LoginScreen } from './auth/LoginScreen'
import { ReferenceProvider } from './data/ReferenceContext'
import { RealtimeProvider, useRealtime } from './data/RealtimeContext'
import PriceSection from './features/price/PriceSection.jsx'

// Реалтайм-права: при SSE `user_updated` про текущего пользователя перечитываем /me,
// чтобы меню/доступы применились на лету (без перезахода). Внутри RealtimeProvider.
function RealtimePermissionSync() {
  const { lastEvent } = useRealtime()
  const { user, refreshUser } = useAuth()
  useEffect(() => {
    if (lastEvent?.type === 'user_updated' && user && lastEvent.user_id === user.user_id) {
      void refreshUser()
    }
  }, [lastEvent, user, refreshUser])
  return null
}

// Встраиваемый режим (для WebView приложения): ?embed=price — только секция Прайс,
// без сайдбара и остального чата. Токен инжектит нативный WebView в localStorage.
const EMBED = new URLSearchParams(window.location.search).get('embed')

function Root() {
  const { status } = useAuth()

  if (EMBED === 'price') {
    if (status === 'loading') return <div style={{ padding: 24, color: 'var(--text-dim)' }}>Загрузка…</div>
    if (status === 'anonymous') return <div style={{ padding: 24, color: 'var(--text-dim)' }}>Требуется авторизация</div>
    return (
      <div style={{ height: '100%', overflow: 'auto' }}>
        <PriceSection />
      </div>
    )
  }

  if (status === 'loading') {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-dim)',
        }}
      >
        Загрузка…
      </div>
    )
  }

  if (status === 'anonymous') return <LoginScreen />

  return (
    <ReferenceProvider>
      <RealtimeProvider>
        <RealtimePermissionSync />
        <AppShell />
      </RealtimeProvider>
    </ReferenceProvider>
  )
}

export function App() {
  return (
    <AuthProvider>
      <Root />
    </AuthProvider>
  )
}
