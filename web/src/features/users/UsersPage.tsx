import { useCallback, useEffect, useState } from 'react'
import { listUsers, setUserEstablishmentRoles, updateUser } from '../../api/endpoints'
import type { EstablishmentRole, User } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import styles from './UsersPage.module.css'

const ROLE_OPTIONS: { value: '' | EstablishmentRole['role']; label: string }[] = [
  { value: '', label: 'Нет доступа' },
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
  const [openUserId, setOpenUserId] = useState<number | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  // Открытый в панели пользователь берётся из списка по id — так панель всегда
  // отражает свежее состояние после действий (patch/setRole обновляют users).
  const openUser = users.find((u) => u.user_id === openUserId) ?? null

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

  const fullName = (u: User) => [u.user_first_name, u.user_second_name].filter(Boolean).join(' ') || u.user_login

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
              onClick={() => setOpenUserId(u.user_id)}
              style={{ cursor: 'pointer' }}
              title="Открыть управление пользователем"
            >
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

      <Modal
        open={openUser != null}
        title="Управление пользователем"
        onClose={() => setOpenUserId(null)}
        width={480}
      >
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
                <Button variant="ghost" loading={savingId === openUser.user_id} onClick={() => patch(openUser, { user_active: false })}>
                  Деактивировать
                </Button>
              ) : (
                <Button variant="primary" loading={savingId === openUser.user_id} onClick={() => patch(openUser, { user_active: true })}>
                  Подтвердить
                </Button>
              )}
              <Button variant="secondary" loading={savingId === openUser.user_id} onClick={() => patch(openUser, { user_admin: !openUser.user_admin })}>
                {openUser.user_admin ? 'Снять админа' : 'Сделать админом'}
              </Button>
            </div>

            <div style={{ paddingTop: 12, borderTop: '1px solid var(--border, rgba(128,128,128,0.2))' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Доступ к складам</div>
              {openUser.user_admin ? (
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Администратор имеет полный доступ ко всем складам.
                </div>
              ) : establishments.length === 0 ? (
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Складов пока нет.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {establishments.map((e) => {
                    const cur = openUser.user_establishment_roles?.find((r) => r.establishment_id === e.establishment_id)?.role ?? ''
                    return (
                      <label key={e.establishment_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 14 }}>
                        <span>{e.establishment_name}</span>
                        <select
                          value={cur}
                          disabled={savingId === openUser.user_id}
                          onChange={(ev) => setRole(openUser, e.establishment_id, ev.target.value as '' | EstablishmentRole['role'])}
                          style={{ padding: '4px 8px', borderRadius: 6, minWidth: 140 }}
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
          </div>
        )}
      </Modal>
    </div>
  )
}
