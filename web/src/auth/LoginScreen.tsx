import { useState } from 'react'
import { Button } from '../ui/Button'
import { Field, TextInput } from '../ui/Field'
import { useAuth } from './AuthContext'
import logoUrl from '../assets/general-title-logo.png'
import styles from './LoginScreen.module.css'

export function LoginScreen() {
  const { login } = useAuth()
  const [loginValue, setLoginValue] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(loginValue.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось войти')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.screen}>
      <form className={styles.card} onSubmit={submit}>
        <div className={styles.brand}>
          <div className={styles.brandRow}>
            <img src={logoUrl} alt="" className={styles.brandLogo} />
            <span className={styles.logo}>NufNaf</span>
          </div>
          <span className={styles.sub}>Панель администратора</span>
        </div>

        <Field label="Логин">
          <TextInput
            value={loginValue}
            onChange={(e) => setLoginValue(e.target.value)}
            autoComplete="username"
            autoFocus
          />
        </Field>
        <Field label="Пароль">
          <TextInput
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </Field>

        {error && <div className={styles.error}>{error}</div>}

        <Button type="submit" variant="primary" loading={busy} disabled={!loginValue || !password}>
          Войти
        </Button>
        <p className={styles.note}>
          Доступ только для пользователей с правами администратора.
        </p>
      </form>
    </div>
  )
}
