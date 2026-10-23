import { useEffect, useState } from 'react'
import { deleteContact, getContactOrders, updateContact, type OrderTotal } from '../../api/endpoints'
import type { Contact, Order } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { formatAmount } from '../../lib/format'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { ConfirmDeleteModal } from '../../ui/ConfirmDeleteModal'
import { Field, TextArea, TextInput } from '../../ui/Field'
import { StatusChip } from '../../ui/StatusChip'
import { Switch } from '../../ui/Switch'
import { CONTACT_METHODS } from '../orders/contactMethods'
import styles from './ContactEditor.module.css'

const formatDate = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString('ru-RU') : '')

/** Карточка контрагента: правка/удаление; у покупателя — сумма отгруженного и его заказы. */
export function ContactEditor({
  contact,
  onBack,
  onSaved,
  onDeleted,
}: {
  contact: Contact
  onBack: () => void
  onSaved: () => void
  onDeleted: () => void
}) {
  const ref = useReference()
  const isBuyer = contact.contact_type === 'buyer'

  const [name, setName] = useState(contact.contact_name)
  const [info, setInfo] = useState(contact.contact_info ?? '')
  const [establishmentId, setEstablishmentId] = useState<number | null>(contact.contact_establishment_id ?? null)
  const [methodId, setMethodId] = useState<number | null>(contact.contact_order_method_id ?? null)
  const [subMethod, setSubMethod] = useState<string | null>(contact.contact_order_sub_method ?? null)
  const [contactMethod, setContactMethod] = useState<string | null>(contact.contact_contact_method ?? null)
  const [salesChannel, setSalesChannel] = useState<string | null>(contact.contact_sales_channel ?? null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)

  const [showOrders, setShowOrders] = useState(false)
  const [orders, setOrders] = useState<Order[] | null>(null)
  const [shippedTotals, setShippedTotals] = useState<OrderTotal[] | null>(null)
  const [ordersError, setOrdersError] = useState('')

  useEffect(() => {
    if (!isBuyer) return
    getContactOrders(contact.contact_id)
      .then((r) => {
        setOrders(r.items)
        setShippedTotals(r.shipped_totals)
      })
      .catch((e) => setOrdersError(e instanceof Error ? e.message : 'Не удалось загрузить заказы'))
  }, [contact.contact_id, isBuyer])

  const subMethods = ref.order_methods.find((m) => m.order_method_id === methodId)?.order_method_sub_methods ?? []
  const canSave = name.trim().length > 0

  const save = async () => {
    setError('')
    setSaving(true)
    try {
      await updateContact(contact.contact_id, {
        contact_name: name.trim(),
        contact_info: info.trim() || null,
        contact_establishment_id: establishmentId,
        contact_order_method_id: methodId,
        contact_order_sub_method: subMethod,
        contact_contact_method: contactMethod,
        contact_sales_channel: salesChannel,
      })
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setSaving(false)
    }
  }

  const shippedLabel = !isBuyer
    ? ''
    : shippedTotals == null
      ? 'Отгружено: …'
      : shippedTotals.length
        ? `Отгружено на ${shippedTotals.map((t) => `${formatAmount(t.amount)}${t.currency_sign ?? ''}`).join(' · ')}`
        : 'Отгружено: 0'

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <button className={styles.back} onClick={onBack}>
          ← Назад
        </button>
        <h1 className={styles.title}>{isBuyer ? 'Покупатель' : 'Поставщик'}</h1>
      </header>

      <div className={styles.scroll}>
        <div className={styles.section}>
          <Field label="Имя">
            <TextInput value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          {isBuyer && orders && orders.length > 0 && name.trim() !== contact.contact_name && (
            <div className={styles.hint}>Имя поменяется и в заказах покупателя ({orders.length}).</div>
          )}

          <Field label="Информация">
            <TextArea value={info} onChange={(e) => setInfo(e.target.value)} />
          </Field>

          {isBuyer && (
            <>
              {ref.sales_channels.length > 0 && (
                <Field label="Канал">
                  <ButtonGroup
                    deselectable
                    columns={3}
                    value={salesChannel}
                    onChange={setSalesChannel}
                    options={ref.sales_channels.map((c) => ({
                      value: c.order_sales_channel_name,
                      label: c.order_sales_channel_name,
                    }))}
                  />
                </Field>
              )}

              <Field label="Склад">
                <ButtonGroup
                  deselectable
                  value={establishmentId}
                  onChange={setEstablishmentId}
                  options={ref.establishments.map((e) => ({ value: e.establishment_id, label: e.establishment_name }))}
                />
              </Field>

              <Field label="Способ связи">
                <ButtonGroup
                  deselectable
                  value={contactMethod}
                  onChange={setContactMethod}
                  options={CONTACT_METHODS.map((m) => ({ value: m, label: m }))}
                />
              </Field>

              <Field label="Способ">
                <ButtonGroup
                  deselectable
                  columns={3}
                  value={methodId}
                  onChange={(id) => {
                    setMethodId(id)
                    setSubMethod(null)
                  }}
                  options={ref.order_methods.map((m) => ({ value: m.order_method_id, label: m.order_method_name }))}
                />
              </Field>

              {subMethods.length > 0 && (
                <Field label="Подспособ">
                  <ButtonGroup
                    deselectable
                    value={subMethod}
                    onChange={setSubMethod}
                    options={subMethods.map((s) => ({ value: s, label: s }))}
                  />
                </Field>
              )}

              <div className={styles.ordersToggle}>
                <Switch
                  checked={showOrders}
                  onChange={setShowOrders}
                  label={`Заказы покупателя${orders ? ` · ${orders.length}` : ''}`}
                />
              </div>

              {showOrders && (
                <div className={styles.orders}>
                  {ordersError ? (
                    <div className={styles.error}>{ordersError}</div>
                  ) : orders == null ? (
                    <div className="dim">Загрузка…</div>
                  ) : orders.length === 0 ? (
                    <div className="dim">Заказов нет</div>
                  ) : (
                    orders.map((o) => (
                      <div key={o.order_id} className={styles.order}>
                        <div className={styles.orderHead}>
                          <span className={styles.orderNo}>№{o.order_id}</span>
                          <span className="dim">{formatDate(o.order_created_at)}</span>
                          {o.order_establishment_name && <span className="dim">{o.order_establishment_name}</span>}
                          {o.order_status && <StatusChip label={o.order_status} color={o.order_status_color} />}
                        </div>
                        <div className={styles.items}>
                          {o.items.map((it) => {
                            const sign = ref.currencies.find((c) => c.currency_id === it.order_item_currency_id)?.currency_sign ?? ''
                            return (
                              <div key={it.order_item_id} className={styles.item}>
                                <span className={styles.itemName}>{it.order_item_name}</span>
                                <span className={styles.itemQty}>
                                  {it.order_item_quantity} × {formatAmount(Number(it.order_item_price) || 0)}
                                  {sign}
                                </span>
                                {it.order_item_status ? (
                                  <StatusChip label={it.order_item_status} color={it.order_item_status_color} />
                                ) : (
                                  <span />
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          )}

          {error && <div className={styles.error}>{error}</div>}
        </div>
      </div>

      <footer className={styles.footer}>
        <div className={styles.total}>{shippedLabel}</div>
        <div className={styles.footerActions}>
          <Button variant="danger" disabled={saving} onClick={() => setConfirmDelete(true)}>
            Удалить
          </Button>
          <Button variant="primary" loading={saving} disabled={!canSave} onClick={save}>
            Сохранить
          </Button>
        </div>
      </footer>

      <ConfirmDeleteModal
        open={confirmDelete}
        title={isBuyer ? 'Удалить покупателя' : 'Удалить поставщика'}
        message={`Точно удалить «${contact.contact_name}» из контрагентов? Заказы и документы останутся как есть.`}
        onClose={() => setConfirmDelete(false)}
        onConfirm={async () => {
          await deleteContact(contact.contact_id)
          onDeleted()
        }}
      />
    </div>
  )
}
