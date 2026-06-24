import { AppShell } from './app/AppShell'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { LoginScreen } from './auth/LoginScreen'
import { ReferenceProvider } from './data/ReferenceContext'

function Root() {
  const { status } = useAuth()

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
      <AppShell />
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
