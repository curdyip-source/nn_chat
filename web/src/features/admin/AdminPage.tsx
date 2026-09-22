import { useState } from 'react'
import { createSystemMessage, listUsers, saveAppSettings } from '../../api/endpoints'
import type { User } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { Checkbox } from '../../ui/Checkbox'
import { Field, TextArea, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { SearchSelect } from '../../ui/SearchSelect'
import { SegmentedControl } from '../../ui/SegmentedControl'
import { SystemMessagesHistory } from './SystemMessagesHistory'
import styles from '../reference/ReferencePage.module.css'

type TargetMode = 'all' | 'user' | 'users'

function userName(u: User) {
  return [u.user_second_name, u.user_first_name].filter(Boolean).join(' ') || u.user_login
}

export function AdminPage() {
  const ref = useReference()

  // ---------- Форс-апдейт iOS ----------
  const currentMinBuild = ref.min_supported_ios_build ?? 0
  const [minBuildValue, setMinBuildValue] = useState(String(currentMinBuild))
  const [minBuildBusy, setMinBuildBusy] = useState(false)
  const [minBuildError, setMinBuildError] = useState('')
  const [minBuildSaved, setMinBuildSaved] = useState(false)

  const parsedMinBuild = Number.parseInt(minBuildValue, 10)
  const minBuildValid = Number.isFinite(parsedMinBuild) && parsedMinBuild >= 0 && parsedMinBuild <= 100000
  const minBuildDirty = minBuildValid && parsedMinBuild !== currentMinBuild

  const saveMinBuild = async () => {
    if (!minBuildValid) return
    setMinBuildError('')
    setMinBuildSaved(false)
    setMinBuildBusy(true)
    try {
      await saveAppSettings({ min_supported_ios_build: parsedMinBuild })
      ref.reload()
      setMinBuildSaved(true)
    } catch (e) {
      setMinBuildError(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setMinBuildBusy(false)
    }
  }

  // ---------- Системные сообщения: форма отправки ----------
  const [messageText, setMessageText] = useState('')
  const [important, setImportant] = useState(false)
  const [targetMode, setTargetMode] = useState<TargetMode>('all')
  const [recipients, setRecipients] = useState<User[]>([])
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const [sendSuccess, setSendSuccess] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)

  const textValid = messageText.trim().length > 0
  const recipientsValid = targetMode === 'all' || recipients.length > 0
  const canSend = textValid && recipientsValid && !sending

  const addRecipient = (user: User) => {
    if (targetMode === 'user') {
      setRecipients([user])
      return
    }
    setRecipients((prev) => (prev.some((u) => u.user_id === user.user_id) ? prev : [...prev, user]))
  }

  const removeRecipient = (userId: number) => {
    setRecipients((prev) => prev.filter((u) => u.user_id !== userId))
  }

  const send = async () => {
    if (!canSend) return
    setSending(true)
    setSendError('')
    setSendSuccess(false)
    try {
      await createSystemMessage({
        text: messageText.trim(),
        important,
        target: targetMode,
        user_ids: recipients.map((u) => u.user_id),
      })
      setMessageText('')
      setImportant(false)
      setRecipients([])
      setSendSuccess(true)
    } catch (e) {
      setSendError(e instanceof Error ? e.message : 'Не удалось отправить')
    } finally {
      setSending(false)
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
                    value={minBuildValue}
                    onChange={(e) => {
                      setMinBuildValue(e.target.value)
                      setMinBuildSaved(false)
                    }}
                    placeholder="0"
                  />
                </Field>
              </div>
              <Button variant="primary" loading={minBuildBusy} disabled={!minBuildDirty} onClick={saveMinBuild}>
                Сохранить
              </Button>
            </div>

            <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              Сейчас действует:{' '}
              <b style={{ color: 'var(--text)' }}>
                {currentMinBuild === 0 ? 'выключено (0)' : `билд ≥ ${currentMinBuild}`}
              </b>
            </div>

            {!minBuildValid && <div className={styles.error}>Введите целое число от 0 до 100000</div>}
            {minBuildError && <div className={styles.error}>{minBuildError}</div>}
            {minBuildSaved && <div style={{ fontSize: 13, color: '#16a34a' }}>Сохранено ✓</div>}
          </div>
        </div>

        <div className={styles.group}>
          <div className={styles.groupTitle} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>Системные сообщения</span>
            <button
              type="button"
              onClick={() => setHistoryOpen(true)}
              title="История системных сообщений"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                color: 'var(--accent, #2563eb)',
                fontSize: 12,
                fontWeight: 700,
                textTransform: 'none',
                letterSpacing: 0,
                padding: 0,
              }}
            >
              🕘 История
            </button>
          </div>
          <div className={styles.form}>
            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.45, maxWidth: 560, color: 'var(--text-dim)' }}>
              Получатель увидит сообщение блокирующим окном в приложении — сразу, если оно
              открыто, иначе при следующем открытии. Закрыть мимо кнопки «Прочитано» нельзя.
            </p>

            <Field label="Текст сообщения">
              <TextArea
                rows={3}
                value={messageText}
                onChange={(e) => {
                  setMessageText(e.target.value)
                  setSendSuccess(false)
                }}
                placeholder="Например: сегодня с 14:00 до 15:00 плановые технические работы, приложение может тормозить"
                style={{ maxWidth: 560 }}
              />
            </Field>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Checkbox checked={important} onChange={setImportant} />
              <span style={{ fontSize: 14 }}>Важное системное сообщение</span>
            </div>
            {important && (
              <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.4, maxWidth: 520, color: 'var(--text-dim)' }}>
                После «Прочитано» приложение дополнительно переспросит «Вы точно ознакомились?» —
                для сообщений, которые обычно закрывают не глядя.
              </p>
            )}

            <div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 6 }}>Кому</div>
              <SegmentedControl<TargetMode>
                options={[
                  { value: 'all', label: 'Всем' },
                  { value: 'user', label: 'Одному' },
                  { value: 'users', label: 'Выбранным' },
                ]}
                value={targetMode}
                onChange={(v) => {
                  setTargetMode(v)
                  setRecipients([])
                  setSendSuccess(false)
                }}
              />
            </div>

            {targetMode !== 'all' && (
              <div style={{ maxWidth: 420 }}>
                <SearchSelect<User>
                  placeholder="Найти пользователя по имени или логину…"
                  search={(q) => listUsers({ search: q, pageSize: 10 }).then((r) => r.items)}
                  getKey={(u) => u.user_id}
                  renderItem={(u) => (
                    <span>
                      {userName(u)} <span style={{ color: 'var(--text-dim)' }}>({u.user_login})</span>
                    </span>
                  )}
                  onSelect={addRecipient}
                />
                {recipients.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                    {recipients.map((u) => (
                      <span
                        key={u.user_id}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '4px 8px',
                          borderRadius: 999,
                          background: 'var(--surface-2, rgba(0,0,0,0.06))',
                          fontSize: 13,
                        }}
                      >
                        {userName(u)}
                        <button
                          type="button"
                          onClick={() => removeRecipient(u.user_id)}
                          aria-label="Убрать получателя"
                          style={{
                            border: 'none',
                            background: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-dim)',
                            fontSize: 15,
                            lineHeight: 1,
                            padding: 0,
                          }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div>
              <Button variant="primary" loading={sending} disabled={!canSend} onClick={send}>
                Отправить
              </Button>
            </div>

            {sendError && <div className={styles.error}>{sendError}</div>}
            {sendSuccess && <div style={{ fontSize: 13, color: '#16a34a' }}>Отправлено ✓</div>}
          </div>
        </div>
      </div>

      <Modal open={historyOpen} title="История системных сообщений" onClose={() => setHistoryOpen(false)} width={720}>
        <SystemMessagesHistory />
      </Modal>
    </div>
  )
}
