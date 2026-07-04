import { useCallback, useEffect, useMemo, useState } from 'react'
import { listUsers, setUserPermissions, updateUser } from '../../api/endpoints'
import type { ActionScope, EstablishmentPermission, User, ViewScope } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
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
const DEFAULT_SCOPES: Omit<EstablishmentPermission, 'establishment_id'> = {
  view_scope: 'establishment',
  can_create: false,
  edit_scope: 'none',
  delete_scope: 'none',
}

const PAGE_SIZE = 100
const fullName = (u: User) => [u.user_first_name, u.user_second_name].filter(Boolean).join(' ') || u.user_login

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [openUserId, setOpenUserId] = useState<number | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const openUser = users.find((u) => u.user_id === openUserId) ?? null

  useEffect(() => setPage(1), [debouncedSearch])

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

  const onUserUpdated = (u: User) => setUsers((prev) => prev.map((x) => (x.user_id === u.user_id ? u : x)))

  if (openUser) {
    return <UserDetail key={openUser.user_id} user={openUser} onBack={() => setOpenUserId(null)} onUpdated={onUserUpdated} />
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Пользователи</h1>
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
                onClick={() => setOpenUserId(u.user_id)} style={{ cursor: 'pointer' }} title="Открыть карточку пользователя">
                <div className={styles.info}>
                  <div className={styles.name}>
                    {fullName(u)}
                    {u.user_admin && <span className={styles.adminBadge}>админ</span>}
                    {!u.user_active && <span className={styles.pendingBadge}>не подтверждён</span>}
                  </div>
                  <div className={styles.rowMeta}>
                    <span className={styles.login}>@{u.user_login}</span>
                    {!u.user_admin && (u.user_establishment_roles?.length ?? 0) > 0 && (
                      <span className={styles.chip}>складов: {u.user_establishment_roles!.length}</span>
                    )}
                  </div>
                </div>
                <span className={styles.rowChevron}>›</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function UserDetail({ user, onBack, onUpdated }: { user: User; onBack: () => void; onUpdated: (u: User) => void }) {
  const ref = useReference()
  const establishments = ref.establishments
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState<'info' | 'access' | 'perms' | null>(null)

  // Личные данные — черновик.
  const [info, setInfo] = useState({
    user_first_name: user.user_first_name ?? '',
    user_second_name: user.user_second_name ?? '',
    user_age: user.user_age != null ? String(user.user_age) : '',
    user_address: user.user_address ?? '',
  })
  const infoDirty =
    info.user_first_name !== (user.user_first_name ?? '') ||
    info.user_second_name !== (user.user_second_name ?? '') ||
    info.user_age !== (user.user_age != null ? String(user.user_age) : '') ||
    info.user_address !== (user.user_address ?? '')

  // Права по складам — черновик (карта establishment_id → настройки).
  const initialPerms = useMemo(() => {
    const map: Record<number, EstablishmentPermission> = {}
    for (const r of user.user_establishment_roles ?? []) map[r.establishment_id] = r
    return map
  }, [user])
  const [perms, setPerms] = useState<Record<number, EstablishmentPermission>>(initialPerms)

  const run = async (kind: 'info' | 'access' | 'perms', fn: () => Promise<{ item: User }>) => {
    setSaving(kind)
    setError(null)
    try {
      const { item } = await fn()
      onUpdated(item)
      if (kind === 'perms') {
        const map: Record<number, EstablishmentPermission> = {}
        for (const r of item.user_establishment_roles ?? []) map[r.establishment_id] = r
        setPerms(map)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setSaving(null)
    }
  }

  const saveInfo = () =>
    run('info', () =>
      updateUser(user.user_id, {
        user_first_name: info.user_first_name.trim(),
        user_second_name: info.user_second_name.trim(),
        user_age: info.user_age ? Number(info.user_age) : undefined,
        user_address: info.user_address.trim(),
      }),
    )
  const setAccess = (body: Partial<Pick<User, 'user_active' | 'user_admin'>>) => run('access', () => updateUser(user.user_id, body))
  const savePerms = () => run('perms', () => setUserPermissions(user.user_id, Object.values(perms)))

  const toggleAccess = (id: number) =>
    setPerms((p) => {
      const next = { ...p }
      if (next[id]) delete next[id]
      else next[id] = { establishment_id: id, ...DEFAULT_SCOPES }
      return next
    })
  const patchScopes = (id: number, patch: Partial<EstablishmentPermission>) =>
    setPerms((p) => (p[id] ? { ...p, [id]: { ...p[id], ...patch } } : p))

  const initial = (user.user_first_name || user.user_login || '?').charAt(0).toUpperCase()

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <button className={styles.backBtn} onClick={onBack}>← Все пользователи</button>

        <div className={styles.detailHead}>
          <div className={styles.avatar}>{initial}</div>
          <div>
            <div className={styles.detailName}>
              {fullName(user)}
              {user.user_admin && <span className={styles.adminBadge}>админ</span>}
              {!user.user_active && <span className={styles.pendingBadge}>не подтверждён</span>}
            </div>
            <div className={styles.login}>@{user.user_login}</div>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.cards}>
          {/* Личные данные */}
          <section className={styles.card}>
            <div className={styles.cardHead}>
              <div className={styles.cardTitle}><span className={styles.cardIcon}>👤</span> Личные данные</div>
            </div>
            <div className={styles.fieldGrid}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Имя</span>
                <TextInput value={info.user_first_name} onChange={(e) => setInfo((s) => ({ ...s, user_first_name: e.target.value }))} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Фамилия</span>
                <TextInput value={info.user_second_name} onChange={(e) => setInfo((s) => ({ ...s, user_second_name: e.target.value }))} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Возраст</span>
                <TextInput inputMode="numeric" value={info.user_age} onChange={(e) => setInfo((s) => ({ ...s, user_age: e.target.value.replace(/\D/g, '') }))} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Адрес</span>
                <TextInput value={info.user_address} onChange={(e) => setInfo((s) => ({ ...s, user_address: e.target.value }))} />
              </label>
              <div className={styles.field}>
                <span className={styles.fieldLabel}>Логин</span>
                <span className={styles.readonly}>@{user.user_login}</span>
              </div>
            </div>
            <div className={styles.cardFooter}>
              <Button variant="primary" disabled={!infoDirty} loading={saving === 'info'} onClick={saveInfo}>Сохранить данные</Button>
            </div>
          </section>

          {/* Администрирование */}
          <section className={styles.card}>
            <div className={styles.cardHead}>
              <div className={styles.cardTitle}><span className={styles.cardIcon}>🛡️</span> Доступ и статус</div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {user.user_active ? (
                <Button variant="ghost" loading={saving === 'access'} onClick={() => setAccess({ user_active: false })}>Деактивировать</Button>
              ) : (
                <Button variant="primary" loading={saving === 'access'} onClick={() => setAccess({ user_active: true })}>Подтвердить</Button>
              )}
              <Button variant="secondary" loading={saving === 'access'} onClick={() => setAccess({ user_admin: !user.user_admin })}>
                {user.user_admin ? 'Снять права админа' : 'Сделать администратором'}
              </Button>
            </div>
          </section>

          {/* Права по складам */}
          <section className={styles.card}>
            <div className={styles.cardHead}>
              <div className={styles.cardTitle}><span className={styles.cardIcon}>🏬</span> Права по складам</div>
            </div>
            {user.user_admin ? (
              <div className={styles.hint}>Администратор имеет полный доступ ко всем складам и разделам — отдельная настройка не требуется.</div>
            ) : establishments.length === 0 ? (
              <div className={styles.hint}>Складов пока нет.</div>
            ) : (
              <>
                <div className={styles.whList}>
                  {establishments.map((e) => {
                    const perm = perms[e.establishment_id]
                    const on = !!perm
                    return (
                      <div key={e.establishment_id} className={[styles.whCard, on ? styles.whCardOn : ''].join(' ')}>
                        <label className={styles.whHead}>
                          <input type="checkbox" checked={on} onChange={() => toggleAccess(e.establishment_id)} />
                          {e.establishment_name}
                        </label>
                        {on && perm && (
                          <div className={styles.whScopes}>
                            <div className={styles.scopeRow}>
                              <span>Видит</span>
                              <select className={styles.scopeSelect} value={perm.view_scope} onChange={(ev) => patchScopes(e.establishment_id, { view_scope: ev.target.value as ViewScope })}>
                                {VIEW_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                              </select>
                            </div>
                            <label className={styles.scopeRow}>
                              <span>Может создавать</span>
                              <input type="checkbox" checked={perm.can_create} onChange={(ev) => patchScopes(e.establishment_id, { can_create: ev.target.checked })} />
                            </label>
                            <div className={styles.scopeRow}>
                              <span>Редактирует</span>
                              <select className={styles.scopeSelect} value={perm.edit_scope} onChange={(ev) => patchScopes(e.establishment_id, { edit_scope: ev.target.value as ActionScope })}>
                                {ACTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                              </select>
                            </div>
                            <div className={styles.scopeRow}>
                              <span>Удаляет</span>
                              <select className={styles.scopeSelect} value={perm.delete_scope} onChange={(ev) => patchScopes(e.establishment_id, { delete_scope: ev.target.value as ActionScope })}>
                                {ACTION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                              </select>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
                <div className={styles.cardFooter}>
                  <Button variant="primary" loading={saving === 'perms'} onClick={savePerms}>Сохранить права</Button>
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
