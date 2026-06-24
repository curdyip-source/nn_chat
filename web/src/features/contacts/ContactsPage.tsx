import { useCallback, useEffect, useState } from 'react'
import { listContacts } from '../../api/endpoints'
import type { Contact } from '../../api/types'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { TextInput } from '../../ui/Field'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import styles from './ContactsPage.module.css'

const PAGE_SIZE = 50
type Tab = 'buyer' | 'supplier'

export function ContactsPage() {
  const [tab, setTab] = useState<Tab>('buyer')
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    setPage(1)
  }, [tab, debouncedSearch])

  const load = useCallback(() => {
    setLoading(true)
    listContacts(tab, { search: debouncedSearch, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setContacts(res.items)
        setTotal(res.pagination?.total ?? res.items.length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [tab, debouncedSearch, page])

  useEffect(load, [load])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Контрагенты{total ? ` · ${total}` : ''}</h1>
        <p className="muted">Покупатели и поставщики из заказов и документов</p>
      </header>

      <div className={styles.filters}>
        <ButtonGroup<Tab>
          columns={2}
          value={tab}
          onChange={(t) => t && setTab(t)}
          options={[
            { value: 'buyer', label: 'Покупатели' },
            { value: 'supplier', label: 'Поставщики' },
          ]}
        />
        <TextInput placeholder="Поиск по имени…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div className={styles.pager}>
          <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>←</Button>
          <span className={styles.pageInfo}>Стр. {page} из {totalPages}</span>
          <Button variant="secondary" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>→</Button>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
        {loading ? (
          <div className="dim">Загрузка…</div>
        ) : contacts.length === 0 ? (
          <div className={styles.empty}>Контрагентов не найдено</div>
        ) : (
          <div className={styles.list}>
            {contacts.map((c) => (
              <div key={c.contact_id} className={styles.row}>
                <div className={styles.name}>{c.contact_name}</div>
                <div className={styles.meta}>
                  {[c.contact_info, c.contact_establishment_name, c.contact_order_method_name, c.contact_order_sub_method]
                    .filter(Boolean)
                    .join(' · ')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
