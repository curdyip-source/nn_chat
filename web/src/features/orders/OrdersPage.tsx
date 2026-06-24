import { useCallback, useEffect, useState } from 'react'
import { listOrders } from '../../api/endpoints'
import type { Order } from '../../api/types'
import { Button } from '../../ui/Button'
import { StatusChip } from '../../ui/StatusChip'
import { OrderCreate } from './OrderCreate'
import styles from './OrdersPage.module.css'

export function OrdersPage() {
  const [creating, setCreating] = useState(false)
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    listOrders(1, 30)
      .then((res) => {
        setOrders(res.items)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!creating) reload()
  }, [creating, reload])

  if (creating) {
    return (
      <OrderCreate
        onCancel={() => setCreating(false)}
        onCreated={() => setCreating(false)}
      />
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Заказы</h1>
          <p className="muted">Последние заказы и создание нового</p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>
          + Создать заказ
        </Button>
      </header>

      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : orders.length === 0 ? (
        <div className={styles.empty}>Заказов пока нет</div>
      ) : (
        <div className={styles.list}>
          {orders.map((o) => (
            <div key={o.order_id} className={styles.card}>
              <div className={styles.cardTop}>
                <span className={styles.orderNo}>№{o.order_id}</span>
                <span className={styles.customer}>{o.order_customer}</span>
                {o.order_status && (
                  <StatusChip label={o.order_status} color={o.order_status_color} />
                )}
              </div>
              <div className={styles.cardMeta}>
                {[o.order_establishment_name, o.order_method_name]
                  .filter(Boolean)
                  .join(' · ')}
                {o.items?.length ? ` · ${o.items.length} поз.` : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
