import { useEffect, useRef, useState } from 'react'
import { addOrderComment, getOrderComments, type OrderComment } from '../../api/endpoints'
import { useAuth } from '../../auth/AuthContext'
import { useRealtime } from '../../data/RealtimeContext'
import styles from './OrderChat.module.css'

function authorName(c: OrderComment): string {
  const full = [c.order_comment_owner_second_name, c.order_comment_owner_first_name].filter(Boolean).join(' ')
  return full || c.order_comment_owner_user_login || 'Пользователь'
}

function timeLabel(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function OrderChat({ orderId }: { orderId: number }) {
  const { user } = useAuth()
  const { revision } = useRealtime()
  const [comments, setComments] = useState<OrderComment[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const listRef = useRef<HTMLDivElement>(null)

  // Загрузка при монтировании (раскрытии карточки) и на каждое realtime-событие.
  useEffect(() => {
    let alive = true
    getOrderComments(orderId)
      .then(({ items }) => {
        if (alive) setComments(items)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [orderId, revision])

  // Автоскролл вниз при появлении новых сообщений.
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [comments.length])

  const send = async () => {
    const text = draft.trim()
    if (!text || sending) return
    setSending(true)
    setError('')
    try {
      const { item } = await addOrderComment(orderId, text)
      setComments((prev) => [...prev, item])
      setDraft('')
    } catch (e) {
      setError((e as Error)?.message || 'Не удалось отправить')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className={styles.chat}>
      <div className={styles.title}>Чат заказа</div>
      <div className={styles.list} ref={listRef}>
        {comments.length === 0 ? (
          <div className={styles.empty}>Сообщений пока нет</div>
        ) : (
          comments.map((c) => {
            const mine = user?.user_id === c.order_comment_owner_user_id
            return (
              <div key={c.order_comment_id} className={`${styles.msg} ${mine ? styles.mine : ''}`}>
                <div className={styles.msgHead}>
                  <span className={styles.author}>{authorName(c)}</span>
                  <span className={styles.time}>{timeLabel(c.order_comment_created_at)}</span>
                </div>
                {c.order_comment_text ? <div className={styles.text}>{c.order_comment_text}</div> : null}
                {c.attachments?.length ? (
                  <div className={styles.attachments}>
                    {c.attachments.map((a) => {
                      const url = `/media/message-attachments/${a.attachment_id}`
                      const isImage = (a.attachment_mime_type || '').startsWith('image/')
                      return isImage ? (
                        <a key={a.attachment_id} href={url} target="_blank" rel="noreferrer">
                          <img className={styles.photo} src={url} alt={a.attachment_original_filename || ''} />
                        </a>
                      ) : (
                        <a key={a.attachment_id} className={styles.file} href={url} target="_blank" rel="noreferrer">
                          📎 {a.attachment_original_filename || 'файл'}
                        </a>
                      )
                    })}
                  </div>
                ) : null}
              </div>
            )
          })
        )}
      </div>
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.composer}>
        <input
          className={styles.input}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
          placeholder="Написать в чат заказа…"
        />
        <button className={styles.send} onClick={() => void send()} disabled={sending || !draft.trim()}>
          {sending ? '…' : 'Отпр.'}
        </button>
      </div>
    </div>
  )
}
