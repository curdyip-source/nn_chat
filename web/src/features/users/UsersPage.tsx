import { useCallback, useEffect, useState } from 'react'
import { listUsers, setUserPermissions, updateUser } from '../../api/endpoints'
import type { ActionScope, EstablishmentPermission, User, ViewScope } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import styles from './UsersPage.module.css'

const VIEW_OPTIONS: { value: ViewScope; label: string }[] = [
  { value: 'own', label: 'Только свои' },
  { value: 'establishment', label: 'Все на складе' },
]

const ACTION_OPTIONS: { value: ActionScope; label: string }[] = [
  { value: 'none', label: 'Нет' },
  { value: 'own', label: 'Только свои' },
  { value: 'establishment', label: 'Все на складе' },
]

type Scopes = Omit<EstablishmentPermission, 'establishment_id'>

const PRESETS: { key: string; label: string; scopes: Scopes }[] = [
  { key: 'viewer', label: 'Просмотр', scopes: { view_scope: 'establishment', can_create: false, edit_scope: 'none', delete_scope: 'none' } },
  { key: 'editor', label: 'Редактор', scopes: { view_scope: 'establishment', can_create: true, edit_scope: 'own', delete_scope: 'own' } },
  { key: 'manager', label: 'Менеджер', scopes: { view_scope: 'establishment', can_create: true, edit_scope: 'establishment', delete_scope: 'establishment' } },
]

const DEFAULT_SCOPES: Scopes = PRESETS[0].scopes

const PAGE_SIZE = 100

export function UsersPage() {
  const ref = useReference()
  const establishments = ref.establishments
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [savingId, setSavingId] = useState<number | null>(null)
  const [openUserId, setOpenUserId] = useState<number | null>(null)
  // Черновик прав: карта establishment_id → настройки (только доступные склады).
  const [draft, setDraft] = useState<Record<number, EstablishmentPermission>>({})
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const openUser = users.find((u) => u.user_id === openUserId) ?? null

  useEffect(() => {
    const map: Record<number, EstablishmentPermission> = {}
    for (const r of openUser?.user_establishment_roles ?? []) map[r.establishment_id] = r
    setDraft(map)
  }, [openUserId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch])

  const reload = useCallback(() => {
    setLoading(true)
    listUsers({ search: debouncedSearch, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setError(null)
        setTotal(res.pagination?.total ?? res.items.length)
        setUsers([...res.items].sort((a, b) => Number(a.user_active) - Number(b.user_active) || a.user_id - b.user_id))
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [debouncedSearch, page])

  useEffect(reload, [reload])

  const patch = async (u: User, body: Partial<Pick<User, 'user_active' | 'user_admin'>>) => {
    setSavingId(u.user_id)
    setError(null)
    try {
      const { item } = await updateUser(u.user_id, body)
      setUsers((prev) => prev.map((x) => (x.user_id === item.user_id ? item : x)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось обновить пользователя')
    } finally {
      setSavingId(null)
    }
  }

  const savePermissions = async () => {
    if (!openUser) return
    setSavingId(openUser.user_id)
    setError(null)
    try {
      const { item } = await setUserPermissions(openUser.user_id, Object.values(draft))
      setUsers((prev) => prev.map((x) => (x.user_id === item.user_id ? item : x)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить права')
    } finally {
      setSavingId(null)
    }
  }

  const toggleAccess = (establishmentId: number) => {
    setDraft((d) => {
      const next = { ...d }
      if (next[establishmentId]) delete next[establishmentId]
      else next[establishmentId] = { establishment_id: establishmentId, ...DEFAULT_SCOPES }
      return next
    })
  }
  const patchScopes = (establishmentId: number, patch: Partial<Scopes>) => {
    setDraft((d) => (d[establishmentId] ? { ...d, [establishmentId]: { ...d[establishmentId], ...patch } } : d))
  }

  const fullName = (u: User) => [u.user_first_name, u.user_second_name].filter(Boolean).join(' ') || u.user_login
  const selectStyle = { padding: '3px 6px', borderRadius: 6, minWidth: 130 } as const

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div><h1 className={styles.title}>Пользователи</h1></div>
      </header>

      <div className={styles.filters}>
        <TextInput placeholder="Поиск по логину или имени…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div className={styles.pager}>
          <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>←</Button>
          <span className={styles.pageInfo}>
            Стр.{' '}
            <input className={styles.pageInput} type="number" min={1} max={totalPages} value={page}
              onChange={(e) => { const n = Number(e.target.value); if (n >= 1 && n <= totalPages) setPage(n) }} />{' '}
            из {totalPages}
          </span>
          <Button variant="secondary" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>→</Button>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : users.length === 0 ? (
        <div className={styles.empty}>Пользователей не найдено</div>
      ) : (
        <div className={styles.list}>
          {users.map((u) => (
            <div key={u.user_id} className={[styles.row, u.user_active ? '' : styles.pending].join(' ')}
              onClick={() => setOpenUserId(u.user_id)} style={{ cursor: 'pointer' }} title="Открыть управление пользователем">
              <div className={styles.info}>
                <div className={styles.name}>
                  {fullName(u)}
                  {u.user_admin && <span className={styles.adminBadge}>админ</span>}
                  {!u.user_active && <span className={styles.pendingBadge}>не подтверждён</span>}
                </div>
                <div className={styles.login}>@{u.user_login}</div>
              </div>
              <span style={{ color: 'var(--text-muted)', fontSize: 18, marginLeft: 'auto' }}>›</span>
            </div>
          ))}
        </div>
      )}
      </div>

      <Modal open={openUser != null} title="Управление пользователем" onClose={() => setOpenUserId(null)} width={560}>
        {openUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                {fullName(openUser)}
                {openUser.user_admin && <span className={styles.adminBadge}>админ</span>}
                {!openUser.user_active && <span className={styles.pendingBadge}>не подтверждён</span>}
              </div>
              <div className={styles.login}>@{openUser.user_login}</div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {openUser.user_active ? (
                <Button variant="ghost" loading={savingId === openUser.user_id} onClick={() => patch(openUser, { user_active: false })}>Деактивировать</Button>
              ) : (
                <Button variant="primary" loading={savingId === openUser.user_id} onClick={() => patch(openUser, { user_active: true })}>Подтвердить</Button>
              )}
              <Button variant="secondary" loading={savingId === openUser.user_id} onClick={() => patch(openUser, { user_admin: !openUser.user_admin })}>
                {openUser.user_admin ? 'Снять админа' : 'Сделать админом'}
              </Button>
            </div>

            {openUser.user_admin ? (
              <div style={{ paddingTop: 12, borderTop: '1px solid var(--border, rgba(128,128,128,0.2))', fontSize: 13, color: 'var(--text-muted)' }}>
                Администратор имеет полный доступ ко всем складам и разделам — настройка прав не требуется.
              </div>
            ) : (
              <div style={{ paddingTop: 12, borderTop: '1px solid var(--border, rgba(128,128,128,0.2))', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>Права по складам</div>
                {establishments.length === 0 && <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Складов пока нет.</span>}
                {establishments.map((e) => {
                  const perm = draft[e.establishment_id]
                  const on = !!perm
                  return (
                    <div key={e.establishment_id} style={{ border: '1px solid var(--border, rgba(128,128,128,0.2))', borderRadius: 8, padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600 }}>
                          <input type="checkbox" checked={on} onChange={() => toggleAccess(e.establishment_id)} />
                          {e.establishment_name}
                        </label>
                        {on && (
                          <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>пресет:</span>
                            {PRESETS.map((p) => (
                              <button key={p.key} type="button" onClick={() => patchScopes(e.establishment_id, p.scopes)}
                                style={{ padding: '2px 8px', borderRadius: 999, fontSize: 12, cursor: 'pointer' }}>{p.label}</button>
                            ))}
                          </span>
                        )}
                      </div>
                      {on && perm && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                          <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 13.5 }}>
                            <span>Видит</span>
                            <select value={perm.view_scope} onChange={(ev) => patchScopes(e.establishment_id, { view_scope: ev.target.value as ViewScope })} style={selectStyle}>
                              {VIEW_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 13.5 }}>
                            <span>Может создавать</span>
                            <input type="checkbox" checked={perm.can_create} onChange={(ev) => patchScopes(e.establishment_id, { can_create: ev.target.checked })} />
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 13.5 }}>
                            <span>Редактирует</span>
                            <select value={perm.edit_scope} onChange={(ev) => patchScopes(e.establishment_id, { edit_scope: ev.target.value as ActionScope })} style={selectStyle}>
                              {ACTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 13.5 }}>
                            <span>Удаляет</span>
                            <select value={perm.delete_scope} onChange={(ev) => patchScopes(e.establishment_id, { delete_scope: ev.target.value as ActionScope })} style={selectStyle}>
                              {ACTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                          </label>
                        </div>
                      )}
                    </div>
                  )
                })}
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button variant="primary" loading={savingId === openUser.user_id} onClick={savePermissions}>Сохранить права</Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
