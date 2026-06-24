import { useState } from 'react'
import { searchContacts } from '../../api/endpoints'
import type { Contact } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { Field } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { SearchSelect } from '../../ui/SearchSelect'
import type { ExtraMode, ItemExtra } from './itemStatusExtra'

type Props = {
  mode: ExtraMode
  initial: ItemExtra
  onCancel: () => void
  onConfirm: (extra: ItemExtra) => void
}

export function ItemStatusExtraModal({ mode, initial, onCancel, onConfirm }: Props) {
  const ref = useReference()
  const [source, setSource] = useState<number | null>(initial.sourceEstablishmentId ?? null)
  const [dest, setDest] = useState<number | null>(initial.destinationEstablishmentId ?? null)
  const [supplier, setSupplier] = useState(initial.supplier ?? '')
  const [error, setError] = useState('')

  const title = mode === 'movement' ? 'Перемещение' : 'Заказ поставщику'

  const confirm = () => {
    if (mode === 'movement') {
      if (source == null || dest == null) {
        setError('Выберите склад-источник и склад-назначения')
        return
      }
      if (source === dest) {
        setError('Склад-источник и назначения должны отличаться')
        return
      }
      onConfirm({ sourceEstablishmentId: source, destinationEstablishmentId: dest })
    } else {
      if (!supplier.trim()) {
        setError('Укажите поставщика')
        return
      }
      onConfirm({ supplier: supplier.trim() })
    }
  }

  const options = ref.establishments.map((e) => ({ value: e.establishment_id, label: e.establishment_name }))

  return (
    <Modal
      open
      title={title}
      onClose={onCancel}
      width={460}
      footer={
        <>
          <Button variant="ghost" onClick={onCancel}>
            Отмена
          </Button>
          <Button variant="primary" onClick={confirm}>
            Применить
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {mode === 'movement' ? (
          <>
            <Field label="Откуда (склад-источник)">
              <ButtonGroup value={source} onChange={setSource} options={options} />
            </Field>
            <Field label="Куда (склад-назначения)">
              <ButtonGroup value={dest} onChange={setDest} options={options} />
            </Field>
          </>
        ) : (
          <Field label="Поставщик" hint="Поиск по контактам или ввод имени">
            <SearchSelect<Contact>
              placeholder="Поставщик"
              value={supplier}
              onValueChange={setSupplier}
              search={(q, signal) => searchContacts('supplier', q, signal).then((r) => r.items)}
              getKey={(c) => c.contact_id}
              renderItem={(c) => <span>{c.contact_name}</span>}
              onSelect={(c) => setSupplier(c.contact_name)}
            />
          </Field>
        )}
        {error && <div style={{ color: 'var(--danger)', fontSize: 13.5 }}>{error}</div>}
      </div>
    </Modal>
  )
}
