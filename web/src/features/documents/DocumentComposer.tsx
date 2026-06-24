import { lazy, Suspense, useMemo, useState } from 'react'
import { searchContacts, searchProducts } from '../../api/endpoints'
import type { Contact, Product } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { SearchSelect } from '../../ui/SearchSelect'
import { cartItemFromProduct, newUid, type CartItem } from '../orders/cart'
import { CartRow } from '../orders/CartRow'
import { CreateProductModal } from '../orders/CreateProductModal'
import type { DocKind, DocView } from './docKind'
import styles from './documents.module.css'

const ExcelImport = lazy(() =>
  import('../orders/ExcelImport').then((m) => ({ default: m.ExcelImport })),
)

export function DocumentComposer({
  kind,
  editDoc,
  onCancel,
  onCreated,
}: {
  kind: DocKind
  editDoc?: DocView | null
  onCancel: () => void
  onCreated: () => void
}) {
  const ref = useReference()
  const defaultCurrencyId = ref.defaultCurrency?.currency_id ?? null

  const [supplier, setSupplier] = useState(editDoc?.supplier ?? '')
  const [establishmentId, setEstablishmentId] = useState<number | null>(editDoc?.establishmentId ?? null)
  const [saveContact, setSaveContact] = useState(false)
  const [items, setItems] = useState<CartItem[]>(
    editDoc
      ? editDoc.items.map((it) => ({
          uid: newUid(),
          productId: it.productId,
          article: it.article,
          name: it.name,
          quantity: it.quantity,
          price: it.cost,
          currencyId: it.currencyId,
        }))
      : [],
  )
  const [excelOpen, setExcelOpen] = useState(false)
  const [createProductName, setCreateProductName] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const total = useMemo(
    () => items.reduce((s, it) => s + (Number(it.price) || 0) * it.quantity, 0).toFixed(2),
    [items],
  )

  const addProduct = (p: Product) => setItems((prev) => [...prev, cartItemFromProduct(p, defaultCurrencyId)])
  const patchItem = (uid: string, patch: Partial<CartItem>) =>
    setItems((prev) => prev.map((it) => (it.uid === uid ? { ...it, ...patch } : it)))
  const removeItem = (uid: string) => setItems((prev) => prev.filter((it) => it.uid !== uid))

  const canSubmit =
    establishmentId != null && items.length > 0 && (!kind.supplierRequired || supplier.trim())

  const submit = async () => {
    setError('')
    if (items.some((it) => !it.price.trim())) {
      setError('Заполните цену у всех позиций')
      return
    }
    if (!canSubmit) {
      setError('Заполните склад, поставщика и добавьте товары')
      return
    }
    setSubmitting(true)
    const state = {
      establishmentId: establishmentId!,
      supplier: supplier.trim() || null,
      saveContact,
      items,
    }
    try {
      if (editDoc) await kind.update(editDoc.id, state)
      else await kind.create(state)
      onCreated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось создать документ')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.cHeader}>
        <button className={styles.back} onClick={onCancel}>
          ← Назад
        </button>
        <h1 className={styles.title}>{editDoc ? `${kind.singular} №${editDoc.id}` : kind.createTitle}</h1>
      </header>

      <div className={styles.scroll}>
        <div className={styles.section}>
          <div className={styles.field}>
            <div className={styles.fieldHead}>
              <span className={styles.label}>
                {kind.supplierLabel}
                {kind.supplierRequired ? '' : ' (необязательно)'}
              </span>
              <label className={styles.saveContact}>
                <input type="checkbox" checked={saveContact} onChange={(e) => setSaveContact(e.target.checked)} />
                Сохранить контакт
              </label>
            </div>
            <SearchSelect<Contact>
              placeholder="Название поставщика"
              value={supplier}
              onValueChange={setSupplier}
              search={(q, signal) => searchContacts('supplier', q, signal).then((r) => r.items)}
              getKey={(c) => c.contact_id}
              renderItem={(c) => <span>{c.contact_name}</span>}
              onSelect={(c) => {
                setSupplier(c.contact_name)
                if (c.contact_establishment_id) setEstablishmentId(c.contact_establishment_id)
              }}
            />
          </div>

          <div className={styles.field}>
            <span className={styles.label}>Склад</span>
            <ButtonGroup
              value={establishmentId}
              onChange={setEstablishmentId}
              options={ref.establishments.map((e) => ({ value: e.establishment_id, label: e.establishment_name }))}
            />
          </div>

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
                renderEmptyAction={(q) => (
                  <button className={styles.createLink} onClick={() => setCreateProductName(q)}>
                    + Создать товар «{q}»
                  </button>
                )}
              />
            </div>
            <Button variant="secondary" onClick={() => setExcelOpen(true)}>
              📄 Импорт из Excel
            </Button>
          </div>

          {items.length === 0 ? (
            <div className={styles.emptyCart}>Добавьте товары поиском или импортом из Excel</div>
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

          {error && <div className={styles.error}>{error}</div>}
        </div>
      </div>

      <footer className={styles.footer}>
        <div className={styles.total}>
          {items.length} поз. · итого {total}
        </div>
        <Button variant="primary" loading={submitting} disabled={!canSubmit} onClick={submit}>
          {editDoc ? 'Сохранить' : 'Создать'}
        </Button>
      </footer>

      {excelOpen && (
        <Suspense fallback={null}>
          <ExcelImport
            open={excelOpen}
            onClose={() => setExcelOpen(false)}
            currencies={ref.currencies}
            defaultCurrencyId={defaultCurrencyId}
            onImport={(newItems) => setItems((prev) => [...prev, ...newItems])}
          />
        </Suspense>
      )}
      <CreateProductModal
        open={createProductName != null}
        defaultName={createProductName ?? ''}
        onClose={() => setCreateProductName(null)}
        onCreated={addProduct}
      />
    </div>
  )
}
