import { useEffect, useRef, useState } from 'react'
import { addOrderComment, deleteOrderComment, getOrderComments, updateOrderComment, type OrderComment } from '../../api/endpoints'
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

type ReplyFragment = { author: string; quote: string; body: string }

// Ответы в чате заказа кодируются текстовым префиксом (как в приложении):
// «| Автор\n> цитата\nтело». Бэкенд про reply не знает — это клиентская конвенция.
function parseReply(text: string | null): ReplyFragment | null {
  if (!text) return null
  const trimmed = text.trim()
  if (!trimmed.startsWith('| ')) return null
  const parts = trimmed.split('\n')
  const author = parts[0].slice(2).trim()
  if (parts.length < 2) return null
  const second = parts[1].trim()
  let quote: string
  if (second.startsWith('> ') || second.startsWith('| ')) {
    quote = second.slice(2).trim()
  } else {
    return null
  }
  const body = parts.slice(2).join('\n').trim()
  return { author, quote, body }
}

export function OrderChat({ orderId }: { orderId: number }) {
  const { user } = useAuth()
  const { revision } = useRealtime()
  const [comments, setComments] = useState<OrderComment[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
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

  const startEdit = (c: OrderComment) => {
    const reply = parseReply(c.order_comment_text)
    setEditingId(c.order_comment_id)
    setEditText(reply ? reply.body : c.order_comment_text ?? '')
  }

  const saveEdit = async (c: OrderComment) => {
    const text = editText.trim()
    if (!text) return
    // Сохраняем reply-префикс исходного сообщения, редактируется только тело.
    const reply = parseReply(c.order_comment_text)
    const composed = reply ? `| ${reply.author}\n> ${reply.quote}\n${text}` : text
    setError('')
    try {
      const { item } = await updateOrderComment(orderId, c.order_comment_id, composed)
      setComments((prev) => prev.map((x) => (x.order_comment_id === item.order_comment_id ? item : x)))
      setEditingId(null)
      setEditText('')
    } catch (e) {
      setError((e as Error)?.message || 'Не удалось изменить')
    }
  }

  const remove = async (c: OrderComment) => {
    if (!window.confirm('Удалить сообщение?')) return
    setError('')
    try {
      await deleteOrderComment(orderId, c.order_comment_id)
      setComments((prev) => prev.filter((x) => x.order_comment_id !== c.order_comment_id))
    } catch (e) {
      setError((e as Error)?.message || 'Не удалось удалить')
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
            const reply = parseReply(c.order_comment_text)
            const bodyText = reply ? reply.body : c.order_comment_text
            const hasAttachments = !!c.attachments?.length
            const canEdit = mine && !hasAttachments && !!(c.order_comment_text ?? '').trim()
            const canDelete = mine || !!user?.user_admin
            const isEditing = editingId === c.order_comment_id
            return (
              <div key={c.order_comment_id} className={`${styles.msg} ${mine ? styles.mine : ''}`}>
                <div className={styles.msgHead}>
                  <span className={styles.author}>{authorName(c)}</span>
                  <span className={styles.time}>{timeLabel(c.order_comment_created_at)}</span>
                </div>
                {isEditing ? (
                  <div className={styles.editBox}>
                    <textarea
                      className={styles.editArea}
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={2}
                    />
                    <div className={styles.editActions}>
                      <button onClick={() => { setEditingId(null); setEditText('') }}>Отмена</button>
                      <button onClick={() => void saveEdit(c)} disabled={!editText.trim()}>Сохранить</button>
                    </div>
                  </div>
                ) : (
                  <>
                    {reply ? (
                      <div className={styles.reply}>
                        <span className={styles.replyAuthor}>{reply.author}</span>
                        {reply.quote ? <span className={styles.replyQuote}>{reply.quote}</span> : null}
                      </div>
                    ) : null}
                    {bodyText ? <div className={styles.text}>{bodyText}</div> : null}
                    {hasAttachments ? (
                      <div className={styles.attachments}>
                        {c.attachments.map((a) => {
                          const url = `/media/order-comment-attachments/${a.attachment_id}`
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
                    {(canEdit || canDelete) && (
                      <div className={styles.actions}>
                        {canEdit && (
                          <button title="Изменить" onClick={() => startEdit(c)}>✏️</button>
                        )}
                        {canDelete && (
                          <button title="Удалить" onClick={() => void remove(c)}>🗑️</button>
                        )}
                      </div>
                    )}
                  </>
                )}
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
