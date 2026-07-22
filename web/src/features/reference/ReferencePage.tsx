import { useState } from 'react'
import { saveCurrency, saveEstablishment, saveOrderMethod, saveSalesChannel, saveStatus } from '../../api/endpoints'
import type { Currency, Establishment, OrderMethod, SalesChannel, Status } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { ColorField } from '../../ui/ColorField'
import { Field, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { StatusChip } from '../../ui/StatusChip'
import styles from './ReferencePage.module.css'

type Tab = 'statuses' | 'establishments' | 'methods' | 'channels' | 'currencies'

const TABS: { key: Tab; label: string }[] = [
  { key: 'statuses', label: 'Статусы' },
  { key: 'establishments', label: 'Склады' },
  { key: 'methods', label: 'Способы' },
  { key: 'channels', label: 'Каналы' },
  { key: 'currencies', label: 'Валюты' },
]

const STATUS_TYPES: { value: string; label: string }[] = [
  { value: 'orders', label: 'Заказы' },
  { value: 'order_products', label: 'Позиции заказа' },
  { value: 'inventory', label: 'Инвентаризации' },
  { value: 'product_registration', label: 'Приёмки' },
]

export function ReferencePage() {
  const ref = useReference()
  const [tab, setTab] = useState<Tab>('statuses')

  const [statusEdit, setStatusEdit] = useState<Status | null | 'new'>(null)
  const [estEdit, setEstEdit] = useState<Establishment | null | 'new'>(null)
  const [methodEdit, setMethodEdit] = useState<OrderMethod | null | 'new'>(null)
  const [channelEdit, setChannelEdit] = useState<SalesChannel | null | 'new'>(null)
  const [currEdit, setCurrEdit] = useState<Currency | null | 'new'>(null)

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Справочники</h1>
        </div>
        <Button
          variant="primary"
          onClick={() => {
            if (tab === 'statuses') setStatusEdit('new')
            else if (tab === 'establishments') setEstEdit('new')
            else if (tab === 'methods') setMethodEdit('new')
            else if (tab === 'channels') setChannelEdit('new')
            else setCurrEdit('new')
          }}
        >
          + Добавить
        </Button>
      </header>

      <div className={styles.tabs}>
        <ButtonGroup size="sm" value={tab} onChange={(t) => t && setTab(t)} options={TABS.map((t) => ({ value: t.key, label: t.label }))} />
      </div>

      <div className={styles.scroll}>
        {tab === 'statuses' &&
          STATUS_TYPES.map((st) => {
            const items = ref.statusesByType(st.value)
            if (items.length === 0) return null
            return (
              <div key={st.value} className={styles.group}>
                <div className={styles.groupTitle}>{st.label}</div>
                <div className={styles.chips}>
                  {items.map((s) => (
                    <button key={s.status_id} className={styles.chipBtn} onClick={() => setStatusEdit(s)}>
                      <StatusChip label={s.status_status} color={s.status_color} />
                    </button>
                  ))}
                </div>
              </div>
            )
          })}

        {tab === 'establishments' && (
          <div className={styles.list}>
            {ref.establishments.map((e) => (
              <button key={e.establishment_id} className={styles.row} onClick={() => setEstEdit(e)}>
                {e.establishment_name}
              </button>
            ))}
          </div>
        )}

        {tab === 'methods' && (
          <div className={styles.list}>
            {ref.order_methods.map((m) => (
              <button key={m.order_method_id} className={styles.row} onClick={() => setMethodEdit(m)}>
                <span>{m.order_method_name}</span>
                {m.order_method_sub_methods.length > 0 && (
                  <span className="dim"> · {m.order_method_sub_methods.join(', ')}</span>
                )}
              </button>
            ))}
          </div>
        )}

        {tab === 'channels' && (
          <div className={styles.list}>
            {ref.sales_channels.map((c) => (
              <button key={c.order_sales_channel_id} className={styles.row} onClick={() => setChannelEdit(c)}>
                {c.order_sales_channel_name}
              </button>
            ))}
          </div>
        )}

        {tab === 'currencies' && (
          <div className={styles.list}>
            {ref.currencies.map((c) => (
              <button key={c.currency_id} className={styles.row} onClick={() => setCurrEdit(c)}>
                {c.currency_name} {c.currency_sign ? `(${c.currency_sign})` : ''}
              </button>
            ))}
          </div>
        )}
      </div>

      {statusEdit !== null && (
        <StatusModal
          item={statusEdit === 'new' ? null : statusEdit}
          onClose={() => setStatusEdit(null)}
          onSaved={() => {
            setStatusEdit(null)
            ref.reload()
          }}
        />
      )}
      {estEdit !== null && (
        <EstablishmentModal
          item={estEdit === 'new' ? null : estEdit}
          onClose={() => setEstEdit(null)}
          onSaved={() => {
            setEstEdit(null)
            ref.reload()
          }}
        />
      )}
      {methodEdit !== null && (
        <MethodModal
          item={methodEdit === 'new' ? null : methodEdit}
          onClose={() => setMethodEdit(null)}
          onSaved={() => {
            setMethodEdit(null)
            ref.reload()
          }}
        />
      )}
      {channelEdit !== null && (
        <SalesChannelModal
          item={channelEdit === 'new' ? null : channelEdit}
          onClose={() => setChannelEdit(null)}
          onSaved={() => {
            setChannelEdit(null)
            ref.reload()
          }}
        />
      )}
      {currEdit !== null && (
        <CurrencyModal
          item={currEdit === 'new' ? null : currEdit}
          onClose={() => setCurrEdit(null)}
          onSaved={() => {
            setCurrEdit(null)
            ref.reload()
          }}
        />
      )}
    </div>
  )
}

function useSaver<T>(fn: () => Promise<T>, onSaved: () => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async () => {
    setError('')
    setBusy(true)
    try {
      await fn()
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, run }
}

function StatusModal({ item, onClose, onSaved }: { item: Status | null; onClose: () => void; onSaved: () => void }) {
  const [type, setType] = useState(item?.status_type ?? 'orders')
  const [name, setName] = useState(item?.status_status ?? '')
  const [color, setColor] = useState(item?.status_color ?? 'blue')
  const { busy, error, run } = useSaver(
    () => saveStatus(item?.status_id ?? null, { status_type: type, status_status: name.trim(), status_color: color.trim() }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Статус' : 'Новый статус'}
      onClose={onClose}
      width={440}
      footer={<ModalFooter onClose={onClose} busy={busy} disabled={!name.trim()} onSave={run} />}
    >
      <div className={styles.form}>
        {!item && (
          <Field label="Раздел">
            <ButtonGroup value={type} onChange={(t) => t && setType(t)} options={STATUS_TYPES} />
          </Field>
        )}
        <Field label="Название">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </Field>
        <Field label="Цвет" hint="Виден и в приложении, и в вебе одинаково">
          <ColorField value={color} onChange={setColor} />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function EstablishmentModal({ item, onClose, onSaved }: { item: Establishment | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(item?.establishment_name ?? '')
  const { busy, error, run } = useSaver(
    () => saveEstablishment(item?.establishment_id ?? null, { establishment_name: name.trim() }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Склад' : 'Новый склад'}
      onClose={onClose}
      width={420}
      footer={<ModalFooter onClose={onClose} busy={busy} disabled={!name.trim()} onSave={run} />}
    >
      <div className={styles.form}>
        <Field label="Название">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function MethodModal({ item, onClose, onSaved }: { item: OrderMethod | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(item?.order_method_name ?? '')
  const [subs, setSubs] = useState((item?.order_method_sub_methods ?? []).join(', '))
  const { busy, error, run } = useSaver(
    () =>
      saveOrderMethod(item?.order_method_id ?? null, {
        order_method_name: name.trim(),
        order_method_sub_methods: subs.split(',').map((s) => s.trim()).filter(Boolean),
      }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Способ' : 'Новый способ'}
      onClose={onClose}
      width={460}
      footer={<ModalFooter onClose={onClose} busy={busy} disabled={!name.trim()} onSave={run} />}
    >
      <div className={styles.form}>
        <Field label="Название">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </Field>
        <Field label="Подспособы" hint="Через запятую: Авито, СДЭК, Яндекс">
          <TextInput value={subs} onChange={(e) => setSubs(e.target.value)} />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function SalesChannelModal({ item, onClose, onSaved }: { item: SalesChannel | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(item?.order_sales_channel_name ?? '')
  const { busy, error, run } = useSaver(
    () => saveSalesChannel(item?.order_sales_channel_id ?? null, { order_sales_channel_name: name.trim() }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Канал' : 'Новый канал'}
      onClose={onClose}
      width={420}
      footer={<ModalFooter onClose={onClose} busy={busy} disabled={!name.trim()} onSave={run} />}
    >
      <div className={styles.form}>
        <Field label="Название">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus placeholder="Розница" />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function CurrencyModal({ item, onClose, onSaved }: { item: Currency | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(item?.currency_name ?? '')
  const [sign, setSign] = useState(item?.currency_sign ?? '')
  const { busy, error, run } = useSaver(
    () => saveCurrency(item?.currency_id ?? null, { currency_name: name.trim(), currency_sign: sign.trim() || null }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Валюта' : 'Новая валюта'}
      onClose={onClose}
      width={400}
      footer={<ModalFooter onClose={onClose} busy={busy} disabled={!name.trim()} onSave={run} />}
    >
      <div className={styles.form}>
        <Field label="Код / название">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus placeholder="USD" />
        </Field>
        <Field label="Знак">
          <TextInput value={sign} onChange={(e) => setSign(e.target.value)} placeholder="$" />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function ModalFooter({ onClose, busy, disabled, onSave }: { onClose: () => void; busy: boolean; disabled: boolean; onSave: () => void }) {
  return (
    <>
      <Button variant="ghost" onClick={onClose}>
        Отмена
      </Button>
      <Button variant="primary" loading={busy} disabled={disabled} onClick={onSave}>
        Сохранить
      </Button>
    </>
  )
}
