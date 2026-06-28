import { useEffect, useState } from "react";
import { priceFetch } from "./priceApi.js";

export default function SynonymsView() {
  const [items, setItems] = useState([]);
  const [term, setTerm] = useState("");
  const [canonical, setCanonical] = useState("");
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("");

  const load = () =>
    priceFetch("/api/synonyms")
      .then((r) => r.json())
      .then(setItems)
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const add = (e) => {
    e.preventDefault();
    setError(null);
    priceFetch("/api/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: term.trim(), canonical: canonical.trim() }),
    }).then(async (r) => {
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        setError(j.detail || `HTTP ${r.status}`);
        return;
      }
      setTerm("");
      setCanonical("");
      load();
    });
  };

  const toggle = (s) =>
    priceFetch(`/api/synonyms/${s.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !s.enabled }),
    }).then(load);

  const remove = (s) =>
    priceFetch(`/api/synonyms/${s.id}`, { method: "DELETE" }).then(load);

  const visible = items.filter(
    (s) =>
      !filter ||
      s.term.includes(filter.toLowerCase()) ||
      s.canonical.includes(filter.toLowerCase())
  );

  return (
    <div className="price-view">
      {/* Всё над данными из БД закреплено: форма добавления + фильтр.
          Скроллится только таблица ниже (.price-pane). */}
      <div className="price-fixed">
        <form className="syn-form" onSubmit={add}>
          <input
            placeholder="термин (дезодорант)"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            required
          />
          <span className="arrow">→</span>
          <input
            placeholder="канонический (deodorant)"
            value={canonical}
            onChange={(e) => setCanonical(e.target.value)}
            required
          />
          <button type="submit">Добавить</button>
        </form>
        {error && <div className="status error">Ошибка: {error}</div>}
        <input
          className="filter"
          placeholder="фильтр…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="price-pane">
      <div className="table-scroll">
        <table className="syn-table">
          <thead>
            <tr>
              <th>термин</th>
              <th></th>
              <th>канонический</th>
              <th>вкл.</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((s) => (
              <tr key={s.id} className={s.enabled ? "" : "off"}>
                <td className="syn-d-term">{s.term}</td>
                <td className="arrow syn-d-arrow">→</td>
                <td className="syn-d-canon">{s.canonical}</td>
                <td className="syn-d-en">
                  <input
                    type="checkbox"
                    checked={s.enabled}
                    onChange={() => toggle(s)}
                  />
                </td>
                <td className="syn-d-del">
                  <button className="del" onClick={() => remove(s)}>
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="muted">Всего: {items.length}</div>
      </div>
    </div>
  );
}
