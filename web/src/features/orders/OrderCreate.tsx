import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import {
  cdekDeliveryPoints,
  cdekPrefill,
  cdekSuggestCities,
  createOrder,
  matchProductsByName,
  searchContacts,
  searchProducts,
  updateOrder,
  type CdekCity,
  type CdekPvz,
} from '../../api/endpoints'
import type { Contact, Order, OrderCreateCdek, Product } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { Field, TextArea } from '../../ui/Field'
import { SearchSelect } from '../../ui/SearchSelect'
import { cartItemFromProduct, newUid, type CartItem } from './cart'
import { CartRow } from './CartRow'
import { CreateProductModal } from './CreateProductModal'
import { CreateMissingProductsModal } from './CreateMissingProductsModal'
import styles from './OrderCreate.module.css'

// SheetJS тяжёлый — грузим экран импорта отдельным чанком только при открытии.
const ExcelImport = lazy(() =>
  import('./ExcelImport').then((m) => ({ default: m.ExcelImport })),
)

const CONTACT_METHODS = ['WA', 'TG', 'AV', 'IG', 'SMS', 'MX']

const cdekInput: React.CSSProperties = {
  width: '100%',
  height: 38,
  padding: '0 12px',
  borderRadius: 10,
  border: '1px solid var(--border, #d8dbe0)',
  background: '#fff',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
}

// Строка вставленного списка: «Наименование <таб/2+ пробела> Цена».
// Цену отделяем только явным разделителем (таб или 2+ пробела), чтобы не спутать
// её с числами внутри названия («Кабель 2x2», «Лампа LED 9W»).
function parsePastedLine(line: string): { name: string; price: string | null } {
  const m = line.match(/^(.*\S)(?:\t+| {2,})(\d+(?:[.,]\d+)?)$/)
  if (m) return { name: m[1].trim(), price: Number(m[2].replace(',', '.')).toFixed(2) }
  return { name: line.trim(), price: null }
}

type Step = 'info' | 'cart'

export function OrderCreate({
  editOrder,
  onCancel,
  onCreated,
}: {
  editOrder?: Order | null
  onCancel: () => void
  onCreated: () => void
}) {
  const ref = useReference()
  const defaultCurrencyId = ref.defaultCurrency?.currency_id ?? null

  const [step, setStep] = useState<Step>('info')
  const [customer, setCustomer] = useState(editOrder?.order_customer ?? '')
  const [info, setInfo] = useState(editOrder?.order_info ?? '')
  const [establishmentId, setEstablishmentId] = useState<number | null>(editOrder?.order_establishment_id ?? null)
  const [methodId, setMethodId] = useState<number | null>(editOrder?.order_method_id ?? null)
  const [subMethod, setSubMethod] = useState<string | null>(editOrder?.order_sub_method ?? null)
  const [contactMethod, setContactMethod] = useState<string | null>(editOrder?.order_contact_method ?? null)
  const [saveContact, setSaveContact] = useState(false)

  // --- Данные СДЭК (когда метод/подметод = СДЭК): сохраняются в заказ, тянутся в накладную ---
  const ec = editOrder?.cdek
  const [cdekName, setCdekName] = useState(ec?.recipient_name ?? '')
  const [cdekPhone, setCdekPhone] = useState(ec?.recipient_phone ?? '')
  const [cdekCityName, setCdekCityName] = useState(ec?.city_name ?? '')
  const [cdekCityCode, setCdekCityCode] = useState<number | null>(ec?.city_code ?? null)
  const [cdekMode, setCdekMode] = useState<'pvz' | 'door'>(ec?.delivery_mode === 'door' ? 'door' : 'pvz')
  const [cdekPvzAddress, setCdekPvzAddress] = useState(ec?.pvz_address ?? '')
  const [cdekPvzCode, setCdekPvzCode] = useState<string | null>(ec?.pvz_code ?? null)
  const [cdekDeliveryAddress, setCdekDeliveryAddress] = useState(ec?.delivery_address ?? '')
  const [cdekPrefilledFor, setCdekPrefilledFor] = useState<string | null>(null)
  const [items, setItems] = useState<CartItem[]>(
    editOrder
      ? editOrder.items.map((it) => ({
          uid: newUid(),
          productId: it.order_item_product_id ?? null,
          article: it.order_item_article,
          name: it.order_item_name,
          quantity: it.order_item_quantity,
          price: it.order_item_price,
          currencyId: it.order_item_currency_id ?? null,
          statusId: it.order_item_status_id ?? null,
          supplier: it.order_item_supplier ?? null,
          sourceEstablishmentId: it.order_item_source_establishment_id ?? null,
          destinationEstablishmentId: it.order_item_destination_establishment_id ?? null,
        }))
      : [],
  )

  const [excelOpen, setExcelOpen] = useState(false)
  const [createProductName, setCreateProductName] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [bulkNote, setBulkNote] = useState<string | null>(null)
  const [missingNames, setMissingNames] = useState<string[]>([])
  const [missingOpen, setMissingOpen] = useState(false)
  const [pastedPrices, setPastedPrices] = useState<Record<string, string>>({})

  const selectedMethod = ref.order_methods.find((m) => m.order_method_id === methodId)
  const subMethods = selectedMethod?.order_method_sub_methods ?? []
  const isCdek = selectedMethod?.order_method_name === 'СДЭК' || subMethod === 'СДЭК'

  // Автозаполнение СДЭК-данных клиента из его прошлых заказов (один раз на имя клиента).
  useEffect(() => {
    const name = customer.trim()
    if (!isCdek || !name || cdekPrefilledFor === name) return
    setCdekPrefilledFor(name)
    cdekPrefill(name)
      .then(({ item }) => {
        if (!item) return
        if (item.recipient_name && !cdekName) setCdekName(item.recipient_name)
        if (item.recipient_phone && !cdekPhone) setCdekPhone(item.recipient_phone)
        if (item.city_name && !cdekCityName) setCdekCityName(item.city_name)
        if (item.city_code && cdekCityCode == null) setCdekCityCode(item.city_code)
        if (item.delivery_mode === 'door' || item.delivery_mode === 'pvz') setCdekMode(item.delivery_mode)
        if (item.pvz_address && !cdekPvzAddress) setCdekPvzAddress(item.pvz_address)
        if (item.pvz_code && !cdekPvzCode) setCdekPvzCode(item.pvz_code)
        if (item.delivery_address && !cdekDeliveryAddress) setCdekDeliveryAddress(item.delivery_address)
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCdek, customer])

  const cdekPayload = (): OrderCreateCdek | undefined =>
    isCdek
      ? {
          recipient_name: cdekName.trim() || null,
          recipient_phone: cdekPhone.trim() || null,
          city_code: cdekCityCode,
          city_name: cdekCityName || null,
          delivery_mode: cdekMode,
          pvz_code: cdekMode === 'pvz' ? cdekPvzCode : null,
          pvz_address: cdekMode === 'pvz' ? cdekPvzAddress || null : null,
          delivery_address: cdekMode === 'door' ? cdekDeliveryAddress.trim() || null : null,
        }
      : undefined

  const total = useMemo(
    () =>
      items.reduce((sum, it) => sum + (Number(it.price) || 0) * it.quantity, 0).toFixed(2),
    [items],
  )

  const applyContact = (c: Contact) => {
    setCustomer(c.contact_name)
    if (c.contact_info) setInfo(c.contact_info)
    if (c.contact_establishment_id) setEstablishmentId(c.contact_establishment_id)
    if (c.contact_order_method_id) setMethodId(c.contact_order_method_id)
    setSubMethod(c.contact_order_sub_method ?? null)
    setContactMethod(c.contact_contact_method ?? null)
  }

  const addProduct = (p: Product) =>
    setItems((prev) => [...prev, cartItemFromProduct(p, defaultCurrencyId)])
  const addMany = (newItems: CartItem[]) => setItems((prev) => [...prev, ...newItems])

  // Вставка списка прямо в поиск: «Наименование[<таб/2+ пробела>Цена]».
  // Сопоставляем с номенклатурой, кладём найденное в корзину и сразу проставляем цену из строки.
  const addFromPastedList = async (lines: string[]) => {
    const parsed = lines.map(parsePastedLine)
    setBulkNote(`Ищу ${parsed.length} поз. в номенклатуре…`)
    try {
      const { results } = await matchProductsByName(parsed.map((p) => p.name))
      const items: CartItem[] = []
      const missing: string[] = []
      const priceByName: Record<string, string> = {}
      results.forEach((r, i) => {
        const price = parsed[i].price
        if (price != null) priceByName[parsed[i].name] = price
        if (r.matched) {
          const base = cartItemFromProduct(r.matched, defaultCurrencyId)
          items.push(price != null ? { ...base, price } : base)
        } else {
          missing.push(r.query)
        }
      })
      if (items.length) addMany(items)
      setMissingNames(missing)
      setPastedPrices(priceByName)
      const anyPrice = parsed.some((p) => p.price != null)
      setBulkNote(
        `Добавлено ${items.length} из ${results.length}` +
          (anyPrice ? ', цены подтянуты' : '') +
          (missing.length ? ` · не найдено: ${missing.length}` : ''),
      )
    } catch {
      setMissingNames([])
      setBulkNote('Не удалось распознать список')
    }
  }

  // Товар создан в мастере для строки name — кладём в корзину (с ценой из списка, если была) и убираем из «ненайденных».
  const onMissingCreated = (name: string, product: Product) => {
    const base = cartItemFromProduct(product, defaultCurrencyId)
    const price = pastedPrices[name]
    addMany([price != null ? { ...base, price } : base])
    setMissingNames((prev) => prev.filter((n) => n !== name))
  }
  const patchItem = (uid: string, patch: Partial<CartItem>) =>
    setItems((prev) => prev.map((it) => (it.uid === uid ? { ...it, ...patch } : it)))
  const removeItem = (uid: string) => setItems((prev) => prev.filter((it) => it.uid !== uid))

  const canSubmit =
    customer.trim() && establishmentId != null && methodId != null && items.length > 0

  const submit = async () => {
    setError('')
    const missingPrice = items.find((it) => !it.price.trim())
    if (missingPrice) {
      setStep('cart')
      setError('Заполните цену у всех позиций')
      return
    }
    if (!canSubmit) {
      setError('Заполните клиента, заведение, способ и добавьте товары')
      return
    }
    setSubmitting(true)
    const mappedItems = items.map((it) => ({
      product_id: it.productId,
      product_article: it.productId ? null : it.article,
      product_name: it.productId ? null : it.name,
      order_item_quantity: it.quantity,
      order_item_price: (Number(it.price) || 0).toFixed(2),
      order_item_status_id: it.statusId ?? null,
      order_item_currency_id: it.currencyId,
      order_item_supplier: it.supplier ?? null,
      order_item_source_establishment_id: it.sourceEstablishmentId ?? null,
      order_item_destination_establishment_id: it.destinationEstablishmentId ?? null,
    }))
    try {
      if (editOrder) {
        await updateOrder(editOrder.order_id, {
          order_establishment_id: establishmentId!,
          order_method_id: methodId!,
          order_sub_method: subMethod,
          order_contact_method: contactMethod,
          order_customer: customer.trim(),
          order_info: info.trim(),
          order_status_id: editOrder.order_status_id!,
          items: mappedItems,
        })
      } else {
        await createOrder({
          order_establishment_id: establishmentId!,
          order_method_id: methodId!,
          order_sub_method: subMethod,
          order_contact_method: contactMethod,
          order_customer: customer.trim(),
          order_info: info.trim(),
          save_contact: saveContact,
          cdek: cdekPayload(),
          order_status_id: null,
          items: mappedItems,
        })
      }
      onCreated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить заказ')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <button className={styles.back} onClick={onCancel}>
          ← Назад
        </button>
        <h1 className={styles.title}>{editOrder ? `Заказ №${editOrder.order_id}` : 'Новый заказ'}</h1>
      </header>

      <div className={styles.tabs}>
        <ButtonGroup<Step>
          columns={2}
          value={step}
          onChange={(s) => s && setStep(s)}
          options={[
            { value: 'info', label: 'Информация' },
            { value: 'cart', label: `Товары${items.length ? ` · ${items.length}` : ''}` },
          ]}
        />
      </div>

      <div className={styles.scroll}>
      {step === 'info' ? (
        <div className={styles.section}>
          <div className={styles.clientField}>
            <div className={styles.clientHeader}>
              <span className={styles.clientLabel}>Клиент</span>
              <label className={styles.saveContact}>
                <input
                  type="checkbox"
                  checked={saveContact}
                  onChange={(e) => setSaveContact(e.target.checked)}
                />
                Сохранить клиента
              </label>
            </div>
            <SearchSelect<Contact>
              placeholder="Имя клиента"
              value={customer}
              onValueChange={setCustomer}
              search={(q, signal) => searchContacts('buyer', q, signal).then((r) => r.items)}
              getKey={(c) => c.contact_id}
              renderItem={(c) => (
                <span>
                  {c.contact_name}
                  {c.contact_info ? <span className="dim"> · {c.contact_info}</span> : null}
                </span>
              )}
              onSelect={applyContact}
            />
            <span className={styles.clientHint}>
              Вводите имя — поиск по контактам; выбор подставит данные заказа
            </span>
          </div>

          <Field label="Информация">
            <TextArea value={info} onChange={(e) => setInfo(e.target.value)} />
          </Field>

          <Field label="Склад">
            <ButtonGroup
              value={establishmentId}
              onChange={setEstablishmentId}
              options={ref.establishments.map((e) => ({
                value: e.establishment_id,
                label: e.establishment_name,
              }))}
            />
          </Field>

          <Field label="Способ">
            <ButtonGroup
              columns={3}
              value={methodId}
              onChange={(id) => {
                setMethodId(id)
                setSubMethod(null)
              }}
              options={ref.order_methods.map((m) => ({
                value: m.order_method_id,
                label: m.order_method_name,
              }))}
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

          {isCdek && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 12, border: '1px solid var(--border, #e2e5ea)', borderRadius: 12 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>Данные СДЭК</div>
              <Field label="Получатель (ФИО)">
                <input style={cdekInput} value={cdekName} onChange={(e) => setCdekName(e.target.value)} placeholder="Иван Иванов" />
              </Field>
              <Field label="Телефон">
                <input style={cdekInput} value={cdekPhone} onChange={(e) => setCdekPhone(e.target.value)} placeholder="+7 900 000-00-00" />
              </Field>
              <Field label="Город (поиск по названию)">
                <SearchSelect<CdekCity>
                  placeholder="Начните вводить город"
                  value={cdekCityName}
                  onValueChange={(v) => {
                    setCdekCityName(v)
                    setCdekCityCode(null)
                    setCdekPvzCode(null)
                    setCdekPvzAddress('')
                  }}
                  search={(q) => cdekSuggestCities(q).then((r) => r.items)}
                  getKey={(c) => c.code}
                  renderItem={(c) => <span>{c.full_name}</span>}
                  onSelect={(c) => {
                    setCdekCityName(c.full_name)
                    setCdekCityCode(c.code)
                  }}
                />
              </Field>
              <Field label="Способ доставки">
                <ButtonGroup
                  value={cdekMode}
                  onChange={(v) => setCdekMode((v as 'pvz' | 'door') ?? 'pvz')}
                  options={[
                    { value: 'pvz', label: 'В пункт выдачи' },
                    { value: 'door', label: 'Курьером' },
                  ]}
                />
              </Field>
              {cdekMode === 'pvz' ? (
                <Field label="Пункт выдачи (поиск по адресу)">
                  <SearchSelect<CdekPvz>
                    placeholder={cdekCityCode == null ? 'Сначала выберите город' : 'Поиск ПВЗ по адресу'}
                    value={cdekPvzAddress}
                    onValueChange={(v) => {
                      setCdekPvzAddress(v)
                      setCdekPvzCode(null)
                    }}
                    search={(q) => (cdekCityCode == null ? Promise.resolve([]) : cdekDeliveryPoints(cdekCityCode, q).then((r) => r.items))}
                    getKey={(p) => p.code}
                    renderItem={(p) => <span>{p.address}</span>}
                    onSelect={(p) => {
                      setCdekPvzAddress(p.address)
                      setCdekPvzCode(p.code)
                    }}
                  />
                </Field>
              ) : (
                <Field label="Адрес доставки">
                  <input style={cdekInput} value={cdekDeliveryAddress} onChange={(e) => setCdekDeliveryAddress(e.target.value)} placeholder="Улица, дом, квартира" />
                </Field>
              )}
            </div>
          )}

          <Field label="Способ связи">
            <ButtonGroup
              deselectable
              value={contactMethod}
              onChange={setContactMethod}
              options={CONTACT_METHODS.map((m) => ({ value: m, label: m }))}
            />
          </Field>

        </div>
      ) : (
        <div className={styles.section}>
          <div className={styles.cartActions}>
            <div className={styles.productSearch}>
              <SearchSelect<Product>
                placeholder="Добавить товар — поиск по названию или артикулу…"
                search={(q, signal) => searchProducts(q, signal).then((r) => r.items)}
                getKey={(p) => p.product_id}
                renderItem={(p) => (
                  <span>
                    {p.product_name}
                    <span className="dim"> · {p.product_article}</span>
                  </span>
                )}
                onSelect={addProduct}
                onBulkPaste={addFromPastedList}
                renderEmptyAction={(q) => (
                  <button className={styles.createLink} onClick={() => setCreateProductName(q)}>
                    + Создать товар «{q}»
                  </button>
                )}
              />
              {bulkNote && (
                <div className={styles.bulkNote}>
                  <span>{bulkNote}</span>
                  {missingNames.length > 0 && (
                    <button
                      type="button"
                      className={styles.createLink}
                      onClick={() => setMissingOpen(true)}
                    >
                      + Создать ненайденные ({missingNames.length})
                    </button>
                  )}
                  <button
                    type="button"
                    className={styles.bulkClose}
                    onClick={() => setBulkNote(null)}
                    aria-label="Скрыть"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
            <Button variant="secondary" onClick={() => setExcelOpen(true)}>
              📄 Импорт из Excel
            </Button>
          </div>

          {items.length === 0 ? (
            <div className={styles.emptyCart}>
              Добавьте товары поиском или импортом из Excel
            </div>
          ) : (
            <div className={styles.cart}>
              {items.map((it) => (
                <CartRow
                  key={it.uid}
                  item={it}
                  currencies={ref.currencies}
                  onChange={(patch) => patchItem(it.uid, patch)}
                  onRemove={() => removeItem(it.uid)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}
      </div>

      <footer className={styles.footer}>
        <div className={styles.total}>
          {items.length} поз. · итого {total}
        </div>
        <Button variant="primary" loading={submitting} disabled={!canSubmit} onClick={submit}>
          {editOrder ? 'Сохранить' : 'Создать заказ'}
        </Button>
      </footer>

      {excelOpen && (
        <Suspense fallback={null}>
          <ExcelImport
            open={excelOpen}
            onClose={() => setExcelOpen(false)}
            currencies={ref.currencies}
            defaultCurrencyId={defaultCurrencyId}
            onImport={addMany}
          />
        </Suspense>
      )}
      <CreateProductModal
        open={createProductName != null}
        defaultName={createProductName ?? ''}
        onClose={() => setCreateProductName(null)}
        onCreated={addProduct}
      />
      <CreateMissingProductsModal
        open={missingOpen}
        names={missingNames}
        prices={pastedPrices}
        onCreated={onMissingCreated}
        onClose={() => setMissingOpen(false)}
      />
    </div>
  )
}
