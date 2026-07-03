import { useEffect, useState } from 'react'
import {
  cdekCreateWaybill,
  cdekDeliveryPoints,
  cdekSuggestCities,
  cdekTariffs,
  type CdekCity,
  type CdekPvz,
  type CdekTariff,
} from '../../api/endpoints'
import type { Order, OrderCdek } from '../../api/types'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { Field } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { SearchSelect } from '../../ui/SearchSelect'

type Props = { order: Order; onClose: () => void; onCreated: (cdek: OrderCdek) => void }

const inputStyle: React.CSSProperties = {
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

export function CdekWaybillModal({ order, onClose, onCreated }: Props) {
  const c = order.cdek // предзаполнение данными, сохранёнными при создании заказа (метод СДЭК)
  const [recipientName, setRecipientName] = useState(c?.recipient_name || order.order_customer || '')
  const [recipientPhone, setRecipientPhone] = useState(c?.recipient_phone || '')
  // Город отправителя (origin). Дефолт — Москва (44); оператор меняет на Тулу и др. при необходимости.
  const [fromCityName, setFromCityName] = useState('Москва')
  const [fromCityCode, setFromCityCode] = useState<number | null>(44)
  const [cityName, setCityName] = useState(c?.city_name || '')
  const [cityCode, setCityCode] = useState<number | null>(c?.city_code ?? null)
  const [mode, setMode] = useState<'pvz' | 'door'>(c?.delivery_mode === 'door' ? 'door' : 'pvz')
  const [pvzAddress, setPvzAddress] = useState(c?.pvz_address || '')
  const [pvzCode, setPvzCode] = useState<string | null>(c?.pvz_code || null)
  const [deliveryAddress, setDeliveryAddress] = useState(c?.delivery_address || '')
  const [weight, setWeight] = useState(500)
  const [length, setLength] = useState(20)
  const [width, setWidth] = useState(15)
  const [height, setHeight] = useState(10)
  const [tariffs, setTariffs] = useState<CdekTariff[]>([])
  const [tariffsLoading, setTariffsLoading] = useState(false)
  const [tariffCode, setTariffCode] = useState<number | null>(null)
  const [declaredValue, setDeclaredValue] = useState(0)
  const [insurance, setInsurance] = useState(false)
  const [codAmount, setCodAmount] = useState(0)
  const [sms, setSms] = useState(false)
  const [payer, setPayer] = useState<'sender' | 'recipient'>('sender')
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Тарифы зависят от города-отправителя (origin), города-получателя и веса.
  useEffect(() => {
    if (cityCode == null) {
      setTariffs([])
      setTariffCode(null)
      return
    }
    let alive = true
    setTariffsLoading(true)
    cdekTariffs(cityCode, weight, fromCityCode)
      .then((r) => {
        if (alive) setTariffs(r.items)
      })
      .catch(() => {
        if (alive) setTariffs([])
      })
      .finally(() => {
        if (alive) setTariffsLoading(false)
      })
    return () => {
      alive = false
    }
  }, [cityCode, weight, fromCityCode])

  const submit = async () => {
    if (cityCode == null) return setError('Выберите город')
    if (mode === 'pvz' && !pvzCode) return setError('Выберите пункт выдачи')
    if (mode === 'door' && !deliveryAddress.trim()) return setError('Укажите адрес доставки')
    if (tariffCode == null) return setError('Выберите тариф')
    if (!recipientName.trim() || !recipientPhone.trim()) return setError('Укажите ФИО и телефон получателя')
    setSubmitting(true)
    setError('')
    try {
      const { item } = await cdekCreateWaybill(order.order_id, {
        tariff_code: tariffCode,
        recipient_name: recipientName.trim(),
        recipient_phone: recipientPhone.trim(),
        from_city_code: fromCityCode,
        from_city_name: fromCityName || null,
        city_code: cityCode,
        city_name: cityName || null,
        delivery_mode: mode,
        pvz_code: mode === 'pvz' ? pvzCode : null,
        pvz_address: mode === 'pvz' ? pvzAddress : null,
        delivery_address: mode === 'door' ? deliveryAddress.trim() : null,
        package: { weight, length, width, height },
        comment: comment.trim() || null,
        save_to_contact: true,
        declared_value: declaredValue,
        insurance,
        sms,
        cod_amount: codAmount,
        delivery_paid_by_recipient: payer === 'recipient',
        delivery_cost: payer === 'recipient' ? tariffs.find((t) => t.tariff_code === tariffCode)?.delivery_sum ?? 0 : 0,
      })
      onCreated(item)
    } catch (e) {
      setError((e as Error)?.message || 'Ошибка создания накладной')
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open
      title={`Накладная СДЭК — заказ №${order.order_id}`}
      onClose={onClose}
      width={560}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Отмена
          </Button>
          <Button variant="primary" onClick={submit} disabled={submitting}>
            {submitting ? 'Создание…' : 'Создать накладную'}
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Получатель (ФИО)">
          <input style={inputStyle} value={recipientName} onChange={(e) => setRecipientName(e.target.value)} placeholder="Иван Иванов" />
        </Field>
        <Field label="Телефон">
          <input style={inputStyle} value={recipientPhone} onChange={(e) => setRecipientPhone(e.target.value)} placeholder="+7 900 000-00-00" />
        </Field>

        <Field label="Откуда — город отправителя (по умолчанию Москва)">
          <SearchSelect<CdekCity>
            placeholder="Город отправителя"
            value={fromCityName}
            onValueChange={(v) => {
              setFromCityName(v)
              setFromCityCode(null)
            }}
            search={(q) => cdekSuggestCities(q).then((r) => r.items)}
            getKey={(c) => c.code}
            renderItem={(c) => <span>{c.full_name}</span>}
            onSelect={(c) => {
              setFromCityName(c.full_name)
              setFromCityCode(c.code)
            }}
          />
        </Field>

        <Field label="Куда — город получателя (поиск по названию)">
          <SearchSelect<CdekCity>
            placeholder="Начните вводить город"
            value={cityName}
            onValueChange={(v) => {
              setCityName(v)
              setCityCode(null)
              setPvzCode(null)
              setPvzAddress('')
            }}
            search={(q) => cdekSuggestCities(q).then((r) => r.items)}
            getKey={(c) => c.code}
            renderItem={(c) => <span>{c.full_name}</span>}
            onSelect={(c) => {
              setCityName(c.full_name)
              setCityCode(c.code)
            }}
          />
        </Field>

        <Field label="Способ доставки">
          <ButtonGroup
            value={mode}
            onChange={(v) => setMode(v as 'pvz' | 'door')}
            options={[
              { value: 'pvz', label: 'В пункт выдачи' },
              { value: 'door', label: 'Курьером' },
            ]}
          />
        </Field>

        {mode === 'pvz' ? (
          <Field label="Пункт выдачи (поиск по адресу)">
            <SearchSelect<CdekPvz>
              placeholder={cityCode == null ? 'Сначала выберите город' : 'Поиск ПВЗ по адресу'}
              value={pvzAddress}
              onValueChange={(v) => {
                setPvzAddress(v)
                setPvzCode(null)
              }}
              search={(q) => (cityCode == null ? Promise.resolve([]) : cdekDeliveryPoints(cityCode, q).then((r) => r.items))}
              getKey={(p) => p.code}
              renderItem={(p) => (
                <span>
                  {p.address}
                  {p.work_time ? <small style={{ display: 'block', opacity: 0.7 }}>{p.work_time}</small> : null}
                </span>
              )}
              onSelect={(p) => {
                setPvzAddress(p.address)
                setPvzCode(p.code)
              }}
            />
          </Field>
        ) : (
          <Field label="Адрес доставки">
            <input style={inputStyle} value={deliveryAddress} onChange={(e) => setDeliveryAddress(e.target.value)} placeholder="Улица, дом, квартира" />
          </Field>
        )}

        <Field label="Габариты посылки (вес г · Д×Ш×В см)">
          <div style={{ display: 'flex', gap: 8 }}>
            <input style={inputStyle} type="number" min={1} value={weight} onChange={(e) => setWeight(Number(e.target.value) || 0)} title="Вес, г" />
            <input style={inputStyle} type="number" min={1} value={length} onChange={(e) => setLength(Number(e.target.value) || 0)} title="Длина, см" />
            <input style={inputStyle} type="number" min={1} value={width} onChange={(e) => setWidth(Number(e.target.value) || 0)} title="Ширина, см" />
            <input style={inputStyle} type="number" min={1} value={height} onChange={(e) => setHeight(Number(e.target.value) || 0)} title="Высота, см" />
          </div>
        </Field>

        <Field label="Тариф">
          {cityCode == null ? (
            <div style={{ fontSize: 13.5, opacity: 0.7 }}>Сначала выберите город</div>
          ) : tariffsLoading ? (
            <div style={{ fontSize: 13.5, opacity: 0.7 }}>Загрузка тарифов…</div>
          ) : (
            <select style={inputStyle} value={tariffCode ?? ''} onChange={(e) => setTariffCode(e.target.value ? Number(e.target.value) : null)}>
              <option value="">— выберите тариф —</option>
              {tariffs.map((t) => (
                <option key={t.tariff_code} value={t.tariff_code}>
                  {t.tariff_name} — {t.delivery_sum}₽ ({t.period_min}–{t.period_max} дн)
                </option>
              ))}
            </select>
          )}
        </Field>

        <Field label="Объявленная стоимость, ₽ (база страхования)">
          <input style={inputStyle} type="number" min={0} value={declaredValue} onChange={(e) => setDeclaredValue(Number(e.target.value) || 0)} />
        </Field>

        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 14, cursor: 'pointer' }}>
          <input type="checkbox" checked={insurance} onChange={(e) => setInsurance(e.target.checked)} />
          Страхование (по объявленной стоимости)
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 14, cursor: 'pointer' }}>
          <input type="checkbox" checked={sms} onChange={(e) => setSms(e.target.checked)} />
          СМС-уведомление получателю <span style={{ opacity: 0.6 }}>(зависит от тарифа/договора)</span>
        </label>

        <Field label="Наложенный платёж, ₽ (0 — нет)">
          <input style={inputStyle} type="number" min={0} value={codAmount} onChange={(e) => setCodAmount(Number(e.target.value) || 0)} />
        </Field>

        <Field label="Оплата доставки">
          <ButtonGroup
            value={payer}
            onChange={(v) => setPayer((v as 'sender' | 'recipient') ?? 'sender')}
            options={[
              { value: 'sender', label: 'Отправитель' },
              { value: 'recipient', label: 'Получатель' },
            ]}
          />
        </Field>

        <Field label="Комментарий (необязательно)">
          <input style={inputStyle} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Комментарий к отправлению" />
        </Field>

        {error && <div style={{ color: 'var(--danger, #d33)', fontSize: 13.5 }}>{error}</div>}
      </div>
    </Modal>
  )
}
