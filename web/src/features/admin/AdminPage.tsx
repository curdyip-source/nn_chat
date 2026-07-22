import { useState } from 'react'
import { saveAppSettings } from '../../api/endpoints'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { Field, TextInput } from '../../ui/Field'
import styles from './AdminPage.module.css'

export function AdminPage() {
  const ref = useReference()
  const current = ref.min_supported_ios_build ?? 0
  const [value, setValue] = useState(String(current))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const parsed = Number.parseInt(value, 10)
  const valid = Number.isFinite(parsed) && parsed >= 0 && parsed <= 100000
  const dirty = valid && parsed !== current

  const save = async () => {
    if (!valid) return
    setError('')
    setSaved(false)
    setBusy(true)
    try {
      await saveAppSettings({ min_supported_ios_build: parsed })
      ref.reload()
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Админка</h1>
      </header>

      <div className={styles.scroll}>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Минимальный билд iOS-приложения</h2>
          <p className={styles.hint}>
            Приложение с билдом ниже указанного будет заблокировано экраном «Обновите
            приложение», пока пользователь не обновится. <b>0</b> — гейт выключен (пускаем всех).
            <br />
            Работает только для билдов, где гейт уже встроен (34 и новее). Веб это не затрагивает.
          </p>

          <div className={styles.row}>
            <div className={styles.field}>
              <Field label="Минимальный билд">
                <TextInput
                  type="number"
                  inputMode="numeric"
                  min={0}
                  value={value}
                  onChange={(e) => {
                    setValue(e.target.value)
                    setSaved(false)
                  }}
                  placeholder="0"
                />
              </Field>
            </div>
            <Button variant="primary" loading={busy} disabled={!dirty} onClick={save}>
              Сохранить
            </Button>
          </div>

          <div className={styles.current}>
            Сейчас действует: <b>{current === 0 ? 'выключено (0)' : `билд ≥ ${current}`}</b>
          </div>
          {!valid && <div className={styles.error}>Введите целое число от 0 до 100000</div>}
          {error && <div className={styles.error}>{error}</div>}
          {saved && <div className={styles.ok}>Сохранено ✓</div>}
        </div>
      </div>
    </div>
  )
}
