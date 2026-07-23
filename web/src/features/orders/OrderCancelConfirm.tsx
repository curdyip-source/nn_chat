import { Button } from '../../ui/Button'
import { Modal } from '../../ui/Modal'

/** Диалог при переводе заказа в «Отменен»: отменить и все товары или оставить их статусы. */
export function OrderCancelConfirm({
  open,
  note,
  onDismiss,
  onCancelAll,
  onKeepItems,
}: {
  open: boolean
  note?: string
  onDismiss: () => void
  onCancelAll: () => void
  onKeepItems: () => void
}) {
  return (
    <Modal
      open={open}
      title="Отменить заказ"
      onClose={onDismiss}
      width={520}
      footer={
        <>
          <Button variant="ghost" onClick={onDismiss}>
            Назад
          </Button>
          <Button variant="secondary" onClick={onKeepItems}>
            Только заказ
          </Button>
          <Button variant="danger" onClick={onCancelAll}>
            Заказ и товары
          </Button>
        </>
      }
    >
      <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.5 }}>
        <b>«Заказ и товары»</b> — все позиции тоже получат статус «Отменен».{' '}
        <b>«Только заказ»</b> — статусы товаров останутся как есть.
        {note ? ` ${note}` : ''}
      </p>
    </Modal>
  )
}
