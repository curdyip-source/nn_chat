import { useRef, useState } from 'react'
import { getProductImportJob, importProductsXlsx } from '../../api/endpoints'
import type { ProductImportJob } from '../../api/types'
import { Button } from '../../ui/Button'
import { Modal } from '../../ui/Modal'
import styles from './ImportXlsxModal.module.css'

type Props = {
  open: boolean
  onClose: () => void
  onDone: () => void
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export function ImportXlsxModal({ open, onClose, onDone }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [job, setJob] = useState<ProductImportJob | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const reset = () => {
    setJob(null)
    setError('')
    setBusy(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  const run = async (file: File) => {
    setError('')
    setBusy(true)
    try {
      const { item } = await importProductsXlsx(file)
      setJob(item)
      let current = item
      // Поллинг до завершения.
      while (current.status === 'queued' || current.status === 'running') {
        await sleep(800)
        const res = await getProductImportJob(current.job_id)
        current = res.item
        setJob(current)
      }
      if (current.status === 'completed') onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось импортировать файл')
    } finally {
      setBusy(false)
    }
  }

  const done = job?.status === 'completed' || job?.status === 'failed'

  return (
    <Modal
      open={open}
      title="Импорт каталога из Excel"
      onClose={() => {
        reset()
        onClose()
      }}
      width={480}
      footer={
        done ? (
          <Button variant="primary" onClick={() => { reset(); onClose() }}>
            Готово
          </Button>
        ) : null
      }
    >
      {!job ? (
        <div className={styles.dropzone} onClick={() => !busy && fileRef.current?.click()}>
          <div className={styles.icon}>⬆️</div>
          <div className={styles.title}>{busy ? 'Загрузка…' : 'Выберите .xlsx файл'}</div>
          <div className="dim">
            Колонки: A — артикул, B — наименование, D — цена (USD). Совпадение по артикулу.
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void run(f)
            }}
          />
        </div>
      ) : (
        <div className={styles.progress}>
          <div className={styles.status}>
            {job.status === 'completed'
              ? '✓ Импорт завершён'
              : job.status === 'failed'
                ? '✕ Ошибка импорта'
                : 'Обработка…'}
          </div>
          <div className={styles.counts}>
            Обработано {job.processed} из {job.total_rows}
          </div>
          {done && job.status === 'completed' && (
            <div className={styles.result}>
              Добавлено: <b>{job.created}</b> · Обновлено: <b>{job.updated}</b> · Пропущено:{' '}
              <b>{job.skipped}</b>
            </div>
          )}
          {job.error_message && <div className={styles.error}>{job.error_message}</div>}
        </div>
      )}
    </Modal>
  )
}
