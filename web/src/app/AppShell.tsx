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
import { AdminPage } from '../features/admin/AdminPage'
import PriceSection from '../features/price/PriceSection.jsx'
import logoUrl from '../assets/general-title-logo.png'
import styles from './AppShell.module.css'

type Section = {
  key: string
  label: string
  icon: string
  render: () => ReactNode
  ready: boolean
  adminOnly?: boolean
}

const SECTIONS: Section[] = [
  { key: 'orders', label: 'Заказы', icon: '📦', render: () => <OrdersPage />, ready: true },
  { key: 'products', label: 'Товары', icon: '🏷️', render: () => <ProductsPage />, ready: true },
  { key: 'inventory', label: 'Инвентаризации', icon: '📊', render: () => <DocumentsPage kind={INVENTORY_KIND} />, ready: true },
  { key: 'registrations', label: 'Приёмки', icon: '📥', render: () => <DocumentsPage kind={REGISTRATION_KIND} />, ready: true },
  { key: 'contacts', label: 'Контрагенты', icon: '👥', render: () => <ContactsPage />, ready: true },
  // Административные разделы — только для админа (управление правами/системой).
  { key: 'reference', label: 'Справочники', icon: '⚙️', render: () => <ReferencePage />, ready: true, adminOnly: true },
  { key: 'users', label: 'Пользователи', icon: '👤', render: () => <UsersPage />, ready: true, adminOnly: true },
  { key: 'audit', label: 'Аудит', icon: '📜', render: () => <AuditPage />, ready: true, adminOnly: true },
  { key: 'chat', label: 'Чат', icon: '💬', render: () => <ChatPage />, ready: true },
  { key: 'price', label: 'Прайс', icon: '💲', render: () => <PriceSection />, ready: true },
  { key: 'admin', label: 'Админка', icon: '🛠️', render: () => <AdminPage />, ready: true, adminOnly: true },
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
  // Видимость: админ — всё; не-админ — админ-разделы скрыты, остальное по user_sections
  // (null = всё). Режимы: chat/price напрямую; пункты СРМ требуют режим 'crm' + свой ключ.
  const secs = user?.user_sections
  const has = (key: string) => secs == null || secs.includes(key)
  const CRM_KEYS = ['orders', 'products', 'inventory', 'registrations', 'contacts']
  const visibleSections = SECTIONS.filter((s) => {
    if (user?.user_admin) return true
    if (s.adminOnly) return false
    if (CRM_KEYS.includes(s.key)) return has('crm') && has(s.key)
    return has(s.key) // chat, price
  })
  const section = visibleSections.find((s) => s.key === active) ?? visibleSections[0]

  return (
    <div className={[styles.layout, sidebarHidden ? styles.noSidebar : ''].join(' ')}>
      {!sidebarHidden && (
        <aside className={styles.sidebar}>
          <div className={styles.brand}>
            <img src={logoUrl} alt="" className={styles.brandLogo} />
            <span>NufNaf</span>
          </div>
          <nav className={styles.nav}>
            {visibleSections.map((s) => (
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
