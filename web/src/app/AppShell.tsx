import { useState } from 'react'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { LayoutProvider, useLayout } from './LayoutContext'
import { AuditPage } from '../features/audit/AuditPage'
import { ChatPage } from '../features/chat/ChatPage'
import { ContactsPage } from '../features/contacts/ContactsPage'
import { DocumentsPage } from '../features/documents/DocumentsPage'
import { INVENTORY_KIND, REGISTRATION_KIND } from '../features/documents/docKind'
import { OrdersPage } from '../features/orders/OrdersPage'
import { ProductsPage } from '../features/products/ProductsPage'
import { ReferencePage } from '../features/reference/ReferencePage'
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
  { key: 'products', label: 'Товары', icon: '🏷️', render: () => <ProductsPage />, ready: true },
  { key: 'inventory', label: 'Инвентаризации', icon: '📊', render: () => <DocumentsPage kind={INVENTORY_KIND} />, ready: true },
  { key: 'registrations', label: 'Приёмки', icon: '📥', render: () => <DocumentsPage kind={REGISTRATION_KIND} />, ready: true },
  { key: 'contacts', label: 'Контрагенты', icon: '👥', render: () => <ContactsPage />, ready: true },
  { key: 'reference', label: 'Справочники', icon: '⚙️', render: () => <ReferencePage />, ready: true },
  { key: 'users', label: 'Пользователи', icon: '👤', render: () => <UsersPage />, ready: true },
  { key: 'audit', label: 'Аудит', icon: '📜', render: () => <AuditPage />, ready: true },
  { key: 'chat', label: 'Чат', icon: '💬', render: () => <ChatPage />, ready: true },
]

export function AppShell() {
  return (
    <LayoutProvider>
      <AppShellInner />
    </LayoutProvider>
  )
}

function AppShellInner() {
  const { user, logout } = useAuth()
  const { sidebarHidden, setSidebarHidden } = useLayout()
  const [active, setActive] = useState('orders')
  const section = SECTIONS.find((s) => s.key === active) ?? SECTIONS[0]

  return (
    <div className={[styles.layout, sidebarHidden ? styles.noSidebar : ''].join(' ')}>
      {!sidebarHidden && (
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
      )}
      <main className={styles.main}>
        {sidebarHidden && (
          <button className={styles.restoreMenu} onClick={() => setSidebarHidden(false)} title="Показать меню">
            ☰
          </button>
        )}
        {section.render()}
      </main>
    </div>
  )
}
