import { useState } from 'react'
import { register } from '../api/endpoints'
import { Button } from '../ui/Button'
import { Field, TextInput } from '../ui/Field'
import { Modal } from '../ui/Modal'
import styles from './LoginScreen.module.css'

export function RegisterModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [loginValue, setLoginValue] = useState('')
  const [password, setPassword] = useState('')
  const [secondName, setSecondName] = useState('') // Фамилия → user_second_name
  const [firstName, setFirstName] = useState('') // Имя → user_first_name
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  // Те же правила, что в приложении: логин ≥ 3, пароль ≥ 6, ФИО не пустые.
  const valid =
    loginValue.trim().length >= 3 && password.length >= 6 && !!secondName.trim() && !!firstName.trim()

  const close = () => {
    setLoginValue('')
    setPassword('')
    setSecondName('')
    setFirstName('')
    setError('')
    setBusy(false)
    setDone(false)
    onClose()
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid || busy) return
    setError('')
    setBusy(true)
    try {
      await register({
        user_login: loginValue.trim(),
        user_password: password,
        user_first_name: firstName.trim(),
        user_second_name: secondName.trim(),
      })
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать аккаунт')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Создание аккаунта" onClose={close} width={420}>
      {done ? (
        <div className={styles.registerForm}>
          <p className={styles.registerHint}>
            Аккаунт создан и отправлен на проверку. Администратор активирует его — после этого вы
            сможете войти.
          </p>
          <Button variant="primary" onClick={close}>
            Понятно
          </Button>
        </div>
      ) : (
        <form className={styles.registerForm} onSubmit={submit}>
          <p className={styles.registerHint}>
            Заполните данные. После регистрации аккаунт попадёт на проверку администратору.
          </p>
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
              autoComplete="new-password"
            />
          </Field>
          <Field label="Фамилия">
            <TextInput
              value={secondName}
              onChange={(e) => setSecondName(e.target.value)}
              autoComplete="family-name"
            />
          </Field>
          <Field label="Имя">
            <TextInput
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              autoComplete="given-name"
            />
          </Field>
          {error && <div className={styles.error}>{error}</div>}
          <Button type="submit" variant="primary" loading={busy} disabled={!valid}>
            Создать аккаунт
          </Button>
        </form>
      )}
    </Modal>
  )
}
