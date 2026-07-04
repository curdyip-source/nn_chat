import { useCallback, useEffect, useState } from 'react'
import { listUsers, setUserEstablishmentRoles, updateUser } from '../../api/endpoints'
import type { EstablishmentRole, User } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import styles from './UsersPage.module.css'

const ROLE_OPTIONS: { value: '' | EstablishmentRole['role']; label: string }[] = [
  { value: '', label: '—' },
  { value: 'viewer', label: 'Просмотр' },
  { value: 'editor', label: 'Редактор' },
  { value: 'manager', label: 'Менеджер' },
]

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
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch])

  const reload = useCallback(() => {
    setLoading(true)
    listUsers({ search: debouncedSearch, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setError(null)
        setTotal(res.pagination?.total ?? res.items.length)
        // Неподтверждённые — наверх.
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

  const setRole = async (u: User, establishmentId: number, role: '' | EstablishmentRole['role']) => {
    const next = (u.user_establishment_roles ?? []).filter((r) => r.establishment_id !== establishmentId)
    if (role) next.push({ establishment_id: establishmentId, role })
    setSavingId(u.user_id)
    setError(null)
    try {
      const { item } = await setUserEstablishmentRoles(u.user_id, next)
      setUsers((prev) => prev.map((x) => (x.user_id === item.user_id ? item : x)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось изменить роли складов')
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Пользователи</h1>
        </div>
      </header>

      <div className={styles.filters}>
        <TextInput
          placeholder="Поиск по логину или имени…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className={styles.pager}>
          <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
            ←
          </Button>
          <span className={styles.pageInfo}>
            Стр.{' '}
            <input
              className={styles.pageInput}
              type="number"
              min={1}
              max={totalPages}
              value={page}
              onChange={(e) => {
                const n = Number(e.target.value)
                if (n >= 1 && n <= totalPages) setPage(n)
              }}
            />{' '}
            из {totalPages}
          </span>
          <Button variant="secondary" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>
            →
          </Button>
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
            <div
              key={u.user_id}
              className={[styles.row, u.user_active ? '' : styles.pending].join(' ')}
            >
              <div className={styles.info}>
                <div className={styles.name}>
                  {[u.user_first_name, u.user_second_name].filter(Boolean).join(' ') || u.user_login}
                  {u.user_admin && <span className={styles.adminBadge}>админ</span>}
                  {!u.user_active && <span className={styles.pendingBadge}>не подтверждён</span>}
                </div>
                <div className={styles.login}>@{u.user_login}</div>
              </div>
              <div className={styles.actions}>
                {u.user_active ? (
                  <Button
                    variant="ghost"
                    loading={savingId === u.user_id}
                    onClick={() => patch(u, { user_active: false })}
                  >
                    Деактивировать
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    loading={savingId === u.user_id}
                    onClick={() => patch(u, { user_active: true })}
                  >
                    Подтвердить
                  </Button>
                )}
                <Button
                  variant="secondary"
                  loading={savingId === u.user_id}
                  onClick={() => patch(u, { user_admin: !u.user_admin })}
                >
                  {u.user_admin ? 'Снять админа' : 'Сделать админом'}
                </Button>
              </div>
              {!u.user_admin && establishments.length > 0 && (
                <div style={{ flexBasis: '100%', display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border, rgba(128,128,128,0.2))' }}>
                  <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Доступ к складам:</span>
                  {establishments.map((e) => {
                    const cur = u.user_establishment_roles?.find((r) => r.establishment_id === e.establishment_id)?.role ?? ''
                    return (
                      <label key={e.establishment_id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                        <span>{e.establishment_name}</span>
                        <select
                          value={cur}
                          disabled={savingId === u.user_id}
                          onChange={(ev) => setRole(u, e.establishment_id, ev.target.value as '' | EstablishmentRole['role'])}
                          style={{ padding: '2px 6px', borderRadius: 6 }}
                        >
                          {ROLE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      </div>
    </div>
  )
}
