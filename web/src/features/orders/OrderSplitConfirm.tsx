import { Button } from '../../ui/Button'
import { Modal } from '../../ui/Modal'

/** Диалог при переводе смешанного заказа в «На сборку»: разделить или отмена. */
export function OrderSplitConfirm({
  open,
  onDismiss,
  onSplit,
}: {
  open: boolean
  onDismiss: () => void
  onSplit: () => void
}) {
  return (
    <Modal
      open={open}
      title="Разделить заказ?"
      onClose={onDismiss}
      width={480}
      footer={
        <>
          <Button variant="ghost" onClick={onDismiss}>
            Отмена
          </Button>
          <Button variant="primary" onClick={onSplit}>
            Разделить и на сборку
          </Button>
        </>
      }
    >
      <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.5 }}>
        В заказе есть товары не в наличии. Товары «В наличии»/«Собрано» останутся в этом заказе
        и он уйдёт на сборку, а остальные — в новый заказ-дубль.
      </p>
    </Modal>
  )
}
