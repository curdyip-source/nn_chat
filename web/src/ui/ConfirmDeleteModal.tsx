import { useState } from 'react'
import { Button } from './Button'
import { Modal } from './Modal'

/** Подтверждение необратимого удаления. Сам вызывает onConfirm, держит «Удаление…»
 *  и показывает ошибку сервера (например, 403 «нет прав») прямо в окне. */
export function ConfirmDeleteModal({
  open,
  title,
  message,
  onClose,
  onConfirm,
}: {
  open: boolean
  title: string
  message: string
  onClose: () => void
  onConfirm: () => Promise<void>
}) {
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const close = () => {
    if (deleting) return
    setError('')
    onClose()
  }

  const confirm = async () => {
    setDeleting(true)
    setError('')
    try {
      await onConfirm()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Modal
      open={open}
      title={title}
      onClose={close}
      width={420}
      footer={
        <>
          <Button variant="ghost" onClick={close} disabled={deleting}>
            Отмена
          </Button>
          <Button variant="danger" onClick={confirm} disabled={deleting}>
            {deleting ? 'Удаление…' : 'Удалить'}
          </Button>
        </>
      }
    >
      <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.5 }}>{message} Действие необратимо.</p>
      {error && (
        <p style={{ margin: '10px 0 0', fontSize: 13, lineHeight: 1.5, color: 'var(--danger)' }}>{error}</p>
      )}
    </Modal>
  )
}
