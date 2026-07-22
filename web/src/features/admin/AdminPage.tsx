import { useState } from 'react'
import { saveAppSettings } from '../../api/endpoints'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { Field, TextInput } from '../../ui/Field'
import styles from '../reference/ReferencePage.module.css'

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
        <div>
          <h1 className={styles.title}>Админка</h1>
        </div>
      </header>

      <div className={styles.scroll}>
        <div className={styles.group}>
          <div className={styles.groupTitle}>Форс-апдейт iOS</div>
          <div className={styles.form}>
            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.45, maxWidth: 560, color: 'var(--text-dim)' }}>
              Приложение с билдом ниже указанного блокируется экраном «Обновите приложение», пока
              пользователь не обновится. <b style={{ color: 'var(--text)' }}>0</b> — гейт выключен.
              Работает начиная с билдов, где гейт встроен (34+); веб не затрагивает.
            </p>

            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, maxWidth: 520 }}>
              <div style={{ flex: 1 }}>
                <Field label="Минимальный билд iOS">
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

            <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              Сейчас действует:{' '}
              <b style={{ color: 'var(--text)' }}>
                {current === 0 ? 'выключено (0)' : `билд ≥ ${current}`}
              </b>
            </div>

            {!valid && <div className={styles.error}>Введите целое число от 0 до 100000</div>}
            {error && <div className={styles.error}>{error}</div>}
            {saved && <div style={{ fontSize: 13, color: '#16a34a' }}>Сохранено ✓</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
