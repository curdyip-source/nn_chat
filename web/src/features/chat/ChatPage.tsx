import { useCallback, useEffect, useRef, useState } from 'react'
import { deleteMessage, editMessage, listMessages, sendMessage } from '../../api/endpoints'
import type { ChatMessage } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { Button } from '../../ui/Button'
import { StatusChip } from '../../ui/StatusChip'
import { formatDateTime } from '../../lib/format'
import styles from './ChatPage.module.css'

function mergeById(a: ChatMessage[], b: ChatMessage[]): ChatMessage[] {
  const map = new Map<number, ChatMessage>()
  for (const m of [...a, ...b]) map.set(m.message_id, m)
  return [...map.values()].sort((x, y) => x.message_id - y.message_id)
}

export function ChatPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      const el = scrollRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  const loadLatest = useCallback((initial = false) => {
    listMessages({ pageSize: 50 })
      .then((res) => {
        const asc = [...res.items].reverse()
        setHasMore((res.pagination?.total ?? asc.length) > asc.length)
        setMessages((prev) => {
          const merged = mergeById(prev, asc)
          return merged
        })
        setError(null)
        if (initial) scrollToBottom()
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => initial && setLoading(false))
  }, [])

  useEffect(() => {
    loadLatest(true)
    const id = window.setInterval(() => loadLatest(false), 20000)
    return () => window.clearInterval(id)
  }, [loadLatest])

  const loadOlder = () => {
    const oldest = messages[0]?.message_id
    if (!oldest) return
    listMessages({ beforeMessageId: oldest, pageSize: 50 }).then((res) => {
      const asc = [...res.items].reverse()
      setHasMore(res.items.length >= 50)
      setMessages((prev) => mergeById(asc, prev))
    })
  }

  const send = async () => {
    const value = text.trim()
    if (!value) return
    setSending(true)
    try {
      const { item } = await sendMessage(value)
      setText('')
      setMessages((prev) => mergeById(prev, [item]))
      scrollToBottom()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось отправить')
    } finally {
      setSending(false)
    }
  }

  const saveEdit = async (id: number) => {
    const value = editText.trim()
    if (!value) return
    try {
      const { item } = await editMessage(id, value)
      setMessages((prev) => prev.map((m) => (m.message_id === id ? item : m)))
      setEditingId(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось изменить')
    }
  }

  const remove = async (id: number) => {
    if (!window.confirm('Удалить сообщение?')) return
    try {
      await deleteMessage(id)
      setMessages((prev) => prev.filter((m) => m.message_id !== id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить')
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Чат</h1>
        <p className="muted">Общая лента команды</p>
      </header>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.scroll} ref={scrollRef}>
        {loading ? (
          <div className="dim">Загрузка…</div>
        ) : (
          <>
            {hasMore && (
              <div className={styles.loadMore}>
                <Button variant="ghost" onClick={loadOlder}>
                  Загрузить раньше
                </Button>
              </div>
            )}
            {messages.map((m) => {
              const own = m.message_owner_user_id === user?.user_id
              const author = [m.message_owner_first_name, m.message_owner_second_name].filter(Boolean).join(' ') || m.message_owner_user_login || 'Пользователь'
              return (
                <div key={m.message_id} className={[styles.msgRow, own ? styles.own : ''].join(' ')}>
                  <div className={styles.bubble}>
                    {!own && <div className={styles.author}>{author}</div>}

                    {m.message_order_id && m.order && (
                      <Preview icon="📦" label={`Заказ №${m.order.order_id}`} title={m.order.order_customer} status={m.order.order_status} color={m.order.order_status_color} count={m.order.items?.length} />
                    )}
                    {m.message_inventory_id && m.inventory && (
                      <Preview icon="📊" label={`Инвентаризация №${m.inventory.inventory_id}`} title={m.inventory.inventory_supplier ?? ''} status={m.inventory.inventory_status} color={m.inventory.inventory_status_color} count={m.inventory.items?.length} />
                    )}
                    {m.message_product_registration_id && m.product_registration && (
                      <Preview icon="📥" label={`Приёмка №${m.product_registration.product_registration_id}`} title={m.product_registration.product_registration_supplier ?? ''} status={m.product_registration.product_registration_status} color={m.product_registration.product_registration_status_color} count={m.product_registration.items?.length} />
                    )}

                    {editingId === m.message_id ? (
                      <div className={styles.editBox}>
                        <textarea className={styles.editArea} value={editText} onChange={(e) => setEditText(e.target.value)} rows={2} />
                        <div className={styles.editActions}>
                          <Button variant="ghost" onClick={() => setEditingId(null)}>Отмена</Button>
                          <Button variant="primary" onClick={() => saveEdit(m.message_id)}>Сохранить</Button>
                        </div>
                      </div>
                    ) : (
                      m.message_text && <div className={styles.text}>{m.message_text}</div>
                    )}

                    {m.attachments.map((a) =>
                      a.attachment_kind === 'photo' ? (
                        <a key={a.attachment_id} href={`/media/message-attachments/${a.attachment_id}`} target="_blank" rel="noreferrer">
                          <img className={styles.photo} src={`/media/message-attachments/${a.attachment_id}`} alt={a.attachment_original_filename} />
                        </a>
                      ) : (
                        <a key={a.attachment_id} className={styles.file} href={`/media/message-attachments/${a.attachment_id}`} target="_blank" rel="noreferrer">
                          📎 {a.attachment_original_filename}
                        </a>
                      ),
                    )}

                    <div className={styles.meta}>
                      <span>{formatDateTime(m.message_created_at)}</span>
                      {own && m.message_type === 'message' && editingId !== m.message_id && (
                        <span className={styles.actions}>
                          <button onClick={() => { setEditingId(m.message_id); setEditText(m.message_text ?? '') }}>✏️</button>
                          <button onClick={() => remove(m.message_id)}>🗑️</button>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </>
        )}
      </div>

      <div className={styles.composer}>
        <textarea
          className={styles.input}
          placeholder="Сообщение…  (Enter — отправить, Shift+Enter — перенос)"
          value={text}
          rows={1}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
        />
        <Button variant="primary" loading={sending} disabled={!text.trim()} onClick={send}>
          Отправить
        </Button>
      </div>
    </div>
  )
}

function Preview({ icon, label, title, status, color, count }: { icon: string; label: string; title: string; status?: string | null; color?: string | null; count?: number }) {
  return (
    <div className={styles.preview}>
      <span className={styles.previewIcon}>{icon}</span>
      <div className={styles.previewBody}>
        <div className={styles.previewLabel}>
          {label}
          {count ? ` · ${count} поз.` : ''}
        </div>
        {title && <div className={styles.previewTitle}>{title}</div>}
      </div>
      {status && <StatusChip label={status} color={color} />}
    </div>
  )
}
