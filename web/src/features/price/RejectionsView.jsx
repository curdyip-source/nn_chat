import { useEffect, useMemo, useState } from "react";
import { priceFetch } from "./priceApi.js";

// «Точно нет» — единая отрицательная память сопоставления: одна таблица.
// Каждая строка: заказчик · исходная номенклатура · источник (CL/поставщик) ·
// найденный, но отклонённый вариант. Удаление разблокирует кандидата.
export default function RejectionsView() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(() => new Set());

  const load = () =>
    priceFetch("/api/rejections")
      .then((r) => r.json())
      .then((d) => {
        setRows(Array.isArray(d) ? d : []);
        setSelected(new Set());
      });

  useEffect(() => {
    load();
  }, []);

  const del = (id) =>
    priceFetch(`/api/rejections/${id}`, { method: "DELETE" }).then(load);

  const bulkDel = (ids) => {
    if (!ids.length) return;
    if (!window.confirm(`Удалить отмеченные (${ids.length})? Кандидаты снова начнут предлагаться.`))
      return;
    Promise.all(
      ids.map((id) => priceFetch(`/api/rejections/${id}`, { method: "DELETE" }))
    ).then(load);
  };

  const toggle = (id) =>
    setSelected((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const f = filter.trim().toLowerCase();
  const visible = useMemo(
    () =>
      rows.filter(
        (r) =>
          !f ||
          [r.counterparty, r.counterparty_email, r.source_text, r.source, r.cand_name, r.cand_code]
            .filter(Boolean)
            .some((v) => String(v).toLowerCase().includes(f))
      ),
    [rows, f]
  );

  const allSel = visible.length > 0 && visible.every((r) => selected.has(r.id));
  const toggleAll = () =>
    setSelected((s) => {
      const next = new Set(s);
      if (allSel) visible.forEach((r) => next.delete(r.id));
      else visible.forEach((r) => next.add(r.id));
      return next;
    });

  const srcCell = (src) =>
    src === "CL" ? (
      <span className="tag ok">CL</span>
    ) : (
      <span className="src-tag">{src}</span>
    );

  return (
    <div className="price-view">
      <div className="conf-toolbar">
        <input
          className="filter"
          placeholder="фильтр…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {selected.size > 0 && (
          <button className="btn-danger" onClick={() => bulkDel([...selected])}>
            Удалить выбранные ({selected.size})
          </button>
        )}
        <span className="muted">Всего: {rows.length}</span>
      </div>

      <div className="price-pane">
      <div className="jobs-head">
        <label className="jobs-selall">
          <input type="checkbox" checked={allSel} onChange={toggleAll} />
          выбрать все
        </label>
      </div>

      <table className="cp-table">
        <thead>
          <tr>
            <th />
            <th>Заказчик</th>
            <th>Исходная номенклатура</th>
            <th>Источник</th>
            <th>Найденный вариант (отклонён)</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {visible.map((r) => (
            <tr key={r.id}>
              <td>
                <input
                  type="checkbox"
                  checked={selected.has(r.id)}
                  onChange={() => toggle(r.id)}
                />
              </td>
              <td>
                {r.counterparty}
                {r.counterparty_email && r.counterparty_email !== r.counterparty && (
                  <div className="muted small">{r.counterparty_email}</div>
                )}
              </td>
              <td>{r.source_text}</td>
              <td>{srcCell(r.source)}</td>
              <td>{r.cand_name}</td>
              <td>
                <button
                  className="cl-x"
                  title="удалить (разблокировать)"
                  onClick={() => del(r.id)}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
          {visible.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                {f ? "Ничего не найдено" : "Пусто"}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
    </div>
  );
}
