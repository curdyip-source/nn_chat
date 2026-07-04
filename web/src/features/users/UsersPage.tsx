import { useCallback, useEffect, useState } from 'react'
import { listUsers, setUserPermissionProfile, updateUser } from '../../api/endpoints'
import type { ActionScope, PermissionProfile, User, ViewScope } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import styles from './UsersPage.module.css'

const VIEW_OPTIONS: { value: ViewScope; label: string }[] = [
  { value: 'own', label: 'Только свои' },
  { value: 'establishment', label: 'Мои склады' },
  { value: 'all', label: 'Все склады' },
]

const ACTION_OPTIONS: { value: ActionScope; label: string }[] = [
  { value: 'none', label: 'Нет' },
  { value: 'own', label: 'Только свои' },
  { value: 'establishment', label: 'Мои склады' },
  { value: 'all', label: 'Все склады' },
]

const PRESETS: { key: string; label: string; profile: Omit<PermissionProfile, 'establishment_ids'> }[] = [
  { key: 'viewer', label: 'Просмотр', profile: { view_scope: 'establishment', can_create: false, edit_scope: 'none', delete_scope: 'none' } },
  { key: 'editor', label: 'Редактор', profile: { view_scope: 'establishment', can_create: true, edit_scope: 'own', delete_scope: 'own' } },
  { key: 'manager', label: 'Менеджер', profile: { view_scope: 'establishment', can_create: true, edit_scope: 'establishment', delete_scope: 'establishment' } },
]

const PAGE_SIZE = 100

function profileOf(u: User): PermissionProfile {
  return {
    establishment_ids: u.user_establishment_ids ?? [],
    view_scope: u.user_view_scope ?? 'establishment',
    can_create: u.user_can_create ?? false,
    edit_scope: u.user_edit_scope ?? 'none',
    delete_scope: u.user_delete_scope ?? 'none',
  }
}

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
  const [draft, setDraft] = useState<PermissionProfile | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const openUser = users.find((u) => u.user_id === openUserId) ?? null

  // Инициализируем черновик профиля при открытии панели.
  useEffect(() => {
    setDraft(openUser ? profileOf(openUser) : null)
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
        setUsers(
          [...res.items].sort(
            (a, b) => Number(a.user_active) - Number(b.user_active) || a.user_id - b.user_id,
          ),
        )
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

  const saveProfile = async () => {
    if (!openUser || !draft) return
    setSavingId(openUser.user_id)
    setError(null)
    try {
      const { item } = await setUserPermissionProfile(openUser.user_id, draft)
      setUsers((prev) => prev.map((x) => (x.user_id === item.user_id ? item : x)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить права')
    } finally {
      setSavingId(null)
    }
  }

  const toggleEstablishment = (id: number) => {
    setDraft((d) => {
      if (!d) return d
      const has = d.establishment_ids.includes(id)
      return { ...d, establishment_ids: has ? d.establishment_ids.filter((x) => x !== id) : [...d.establishment_ids, id] }
    })
  }

  const fullName = (u: User) => [u.user_first_name, u.user_second_name].filter(Boolean).join(' ') || u.user_login
  const selectStyle = { padding: '4px 8px', borderRadius: 6, minWidth: 150 } as const

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Пользователи</h1>
        </div>
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

      <Modal open={openUser != null} title="Управление пользователем" onClose={() => setOpenUserId(null)} width={520}>
        {openUser && draft && (
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
              <div style={{ paddingTop: 12, borderTop: '1px solid var(--border, rgba(128,128,128,0.2))', display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>Права</span>
                  <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>пресет:</span>
                  {PRESETS.map((p) => (
                    <button key={p.key} type="button" onClick={() => setDraft((d) => (d ? { ...d, ...p.profile } : d))}
                      style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12.5, cursor: 'pointer' }}>
                      {p.label}
                    </button>
                  ))}
                </div>

                <div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 4 }}>Склады (где работает)</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                    {establishments.length === 0 && <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Складов пока нет.</span>}
                    {establishments.map((e) => (
                      <label key={e.establishment_id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
                        <input type="checkbox" checked={draft.establishment_ids.includes(e.establishment_id)} onChange={() => toggleEstablishment(e.establishment_id)} />
                        {e.establishment_name}
                      </label>
                    ))}
                  </div>
                </div>

                <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 14 }}>
                  <span>Видит документы</span>
                  <select value={draft.view_scope} onChange={(e) => setDraft((d) => (d ? { ...d, view_scope: e.target.value as ViewScope } : d))} style={selectStyle}>
                    {VIEW_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 14 }}>
                  <span>Может создавать</span>
                  <input type="checkbox" checked={draft.can_create} onChange={(e) => setDraft((d) => (d ? { ...d, can_create: e.target.checked } : d))} />
                </label>

                <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 14 }}>
                  <span>Редактирует</span>
                  <select value={draft.edit_scope} onChange={(e) => setDraft((d) => (d ? { ...d, edit_scope: e.target.value as ActionScope } : d))} style={selectStyle}>
                    {ACTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 14 }}>
                  <span>Удаляет</span>
                  <select value={draft.delete_scope} onChange={(e) => setDraft((d) => (d ? { ...d, delete_scope: e.target.value as ActionScope } : d))} style={selectStyle}>
                    {ACTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </label>

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button variant="primary" loading={savingId === openUser.user_id} onClick={saveProfile}>Сохранить права</Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
