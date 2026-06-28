import { useCallback, useEffect, useState } from "react";
import { priceFetch } from "./priceApi.js";

const LABELS = {
  success: "Успешно",
  error: "Ошибка",
  pending: "Ожидание",
  running: "Выполняется…",
};

function Stage({ number, title, stage, link, linkLabel, stale }) {
  const status = stage?.status || "pending";
  const done = status === "success";
  // Прайс за сегодня ещё не получен → успешные этапы относятся к прошлому
  // прогону: гасим зелёный в серый, чтобы не выглядело «всё ок за сегодня».
  const tag = done ? (stale ? "tag" : "tag ok") : status === "error" ? "tag bad" : "tag";
  return (
    <div className="pstage">
      <div className={`pstage-check${done ? " done" : ""}${done && stale ? " stale" : ""}`}>
        {done ? "✓" : ""}
      </div>
      <div className="pstage-body">
      <div className="pstage-head">
        <span className="pstage-num">Этап {number}</span>
        <span className={tag}>{LABELS[status] || status}</span>
      </div>
      <div className="pstage-title">{title}</div>
      {stage?.products != null && status === "success" && (
        <div className="muted small">товаров в БД: {stage.products}</div>
      )}
      {link && status === "success" && (
        <a href={link} target="_blank" rel="noreferrer">
          {linkLabel}
        </a>
      )}
      {stage?.timestamp && (
        <div className="muted small">
          {new Date(stage.timestamp).toLocaleString("ru-RU")}
        </div>
      )}
      {stage?.error && <div className="status error">{stage.error}</div>}
      </div>
    </div>
  );
}

// «03.06» из «2026-06-03».
const ddmm = (iso) => {
  const [, m, d] = iso.split("-");
  return `${d}.${m}`;
};

// Подпись столбца по позиции с конца: сегодня / вчера / позавчера.
const dayLabel = (idx, len) => {
  const fromEnd = len - 1 - idx;
  return fromEnd === 0
    ? "сегодня"
    : fromEnd === 1
    ? "вчера"
    : fromEnd === 2
    ? "позавчера"
    : "";
};

// Сетка обновлений прайсов поставщиков: строки — поставщики, столбцы — дни.
function SupplierGrid() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const load = () =>
      priceFetch("/api/price-out/calendar")
        .then((r) => r.json())
        .then(setData)
        .catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  if (!data || !data.suppliers?.length) return null;

  return (
    <div className="sup-grid-wrap">
      <table className="sup-grid">
        <thead>
          <tr>
            <th className="sg-cp">Контрагент</th>
            <th className="sg-email">Поставщик</th>
            {data.days.map((d, i) => (
              <th key={d}>
                <div>{dayLabel(i, data.days.length)}</div>
                <div className="muted small">{ddmm(d)}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.suppliers.map((s) => (
            <tr key={s.email}>
              <td className="sg-cp">
                {s.name || s.title ? (
                  <>
                    {s.name && <div className="sg-name">{s.name}</div>}
                    {s.title && <div className="muted small">{s.title}</div>}
                  </>
                ) : (
                  <span className="muted small">— не заполнено —</span>
                )}
              </td>
              <td className="sg-email">{s.email}</td>
              {s.cells.map((n, i) => (
                <td
                  key={i}
                  className="sg-cell"
                  data-day={dayLabel(i, data.days.length) || ddmm(data.days[i])}
                >
                  {n > 0 ? (
                    <span className="sg-ok" title={`обновлён · ${n} позиций`}>
                      ✓
                    </span>
                  ) : (
                    <span className="sg-no" title="прайс за день не получен">
                      —
                    </span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PriceView() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("stages"); // stages | suppliers

  const load = useCallback(
    () =>
      priceFetch("/api/price/status")
        .then((r) => r.json())
        .then((d) => {
          setStatus(d);
          setError(null);
        })
        .catch((e) => setError(e.message)),
    []
  );

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const processing = status?.processing;
  const authorized = status?.authorized;

  const checkNow = () => {
    setBusy(true);
    // 1) проверить почту (CL + прайсы поставщиков); 2) выгрузить справочник
    // контрагентов в лист «База данных» таблицы order.
    Promise.all([
      priceFetch("/api/price/process", { method: "POST" }),
      priceFetch("/api/counterparties/push-gsheet", { method: "POST" }),
    ])
      .then(() => setTimeout(load, 800))
      .finally(() => setBusy(false));
  };

  return (
    <>
      {error && <div className="status error">Ошибка: {error}</div>}

      {status && (
        <div className="price-top">
          {authorized && (
            <div className="seg">
              <button
                className={view === "stages" ? "seg-btn active" : "seg-btn"}
                onClick={() => setView("stages")}
              >
                Этапы приёма
              </button>
              <button
                className={view === "suppliers" ? "seg-btn active" : "seg-btn"}
                onClick={() => setView("suppliers")}
              >
                Прайсы поставщиков
              </button>
            </div>
          )}
          <div className="price-top-actions">
            {authorized ? (
              <button
                className="btn-primary"
                disabled={busy || processing}
                onClick={checkNow}
              >
                {processing ? "Обработка…" : "Проверить почту"}
              </button>
            ) : (
              <span className="price-auth">
                Google-аккаунт не подключён.{" "}
                {/* OAuth-старт прайса проксируется nginx чата под /price-api
                    (срезается -> бэкенд /auth/login). Редирект верхнего уровня,
                    а не fetch, поэтому без priceApi. */}
                <a className="btn-primary" href="/price-api/auth/login">
                  Подключить Google
                </a>
              </span>
            )}
          </div>
        </div>
      )}

      {authorized && processing && view === "stages" && (
        <div className="status">Идёт обработка — этапы обновляются автоматически…</div>
      )}

      {authorized && view === "stages" && status && (
        <>
          <p className="muted">
            {status.priceReceivedToday
              ? "Прайс за сегодня получен"
              : "Прайс за сегодня ещё не получен"}
            {status.lastFileName && ` · файл: ${status.lastFileName}`}
            {status.lastRun &&
              ` · последняя проверка: ${new Date(status.lastRun).toLocaleString("ru-RU")}`}
          </p>
          <div className="pstages">
            <Stage
              number={1}
              title="Прайс получен"
              stage={status.stage1}
              stale={!status.priceReceivedToday}
            />
            <Stage
              number={2}
              title="Загружено на Google Диск"
              stage={status.stage2}
              stale={!status.priceReceivedToday}
              link={status.stage2?.folderUrl || status.stage2?.fileUrl}
              linkLabel={
                status.stage2?.folderPath
                  ? `Открыть папку ${status.stage2.folderPath} на Диске`
                  : "Открыть папку на Диске"
              }
            />
            <Stage
              number={3}
              title="Загружено в Google Таблицу Price"
              stage={status.stage3}
              stale={!status.priceReceivedToday}
              link={status.stage3?.sheetUrl}
              linkLabel="Открыть таблицу"
            />
            <Stage
              number={4}
              title="Обновление базы данных"
              stage={status.stage4}
              stale={!status.priceReceivedToday}
            />
          </div>
        </>
      )}

      {authorized && view === "suppliers" && <SupplierGrid />}
    </>
  );
}
