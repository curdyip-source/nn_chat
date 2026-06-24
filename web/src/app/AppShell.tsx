import { useState } from 'react'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { AuditPage } from '../features/audit/AuditPage'
import { OrdersPage } from '../features/orders/OrdersPage'
import { UsersPage } from '../features/users/UsersPage'
import styles from './AppShell.module.css'

type Section = {
  key: string
  label: string
  icon: string
  render: () => ReactNode
  ready: boolean
}

const SECTIONS: Section[] = [
  { key: 'orders', label: 'Заказы', icon: '📦', render: () => <OrdersPage />, ready: true },
  { key: 'products', label: 'Товары', icon: '🏷️', render: () => <Placeholder name="Товары" />, ready: false },
  { key: 'inventory', label: 'Инвентаризации', icon: '📊', render: () => <Placeholder name="Инвентаризации" />, ready: false },
  { key: 'reference', label: 'Справочники', icon: '⚙️', render: () => <Placeholder name="Справочники" />, ready: false },
  { key: 'users', label: 'Пользователи', icon: '👤', render: () => <UsersPage />, ready: true },
  { key: 'audit', label: 'Аудит', icon: '📜', render: () => <AuditPage />, ready: true },
  { key: 'chat', label: 'Чат', icon: '💬', render: () => <Placeholder name="Чат" />, ready: false },
]

function Placeholder({ name }: { name: string }) {
  return (
    <div className={styles.placeholder}>
      <h2>{name}</h2>
      <p className="muted">Этот раздел будет перенесён на новый интерфейс следующим шагом.</p>
    </div>
  )
}

export function AppShell() {
  const { user, logout } = useAuth()
  const [active, setActive] = useState('orders')
  const section = SECTIONS.find((s) => s.key === active) ?? SECTIONS[0]

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>NufNaf</div>
        <nav className={styles.nav}>
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              className={[styles.navItem, s.key === active ? styles.navActive : ''].join(' ')}
              onClick={() => setActive(s.key)}
            >
              <span className={styles.navIcon}>{s.icon}</span>
              <span>{s.label}</span>
              {!s.ready && <span className={styles.soon}>скоро</span>}
            </button>
          ))}
        </nav>
        <div className={styles.userBox}>
          <div className={styles.userName}>{user?.user_login}</div>
          <button className={styles.logout} onClick={logout}>
            Выйти
          </button>
        </div>
      </aside>
      <main className={styles.main}>{section.render()}</main>
    </div>
  )
}
