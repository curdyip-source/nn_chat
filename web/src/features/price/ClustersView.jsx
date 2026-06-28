import { useEffect, useMemo, useState } from "react";
import { priceFetch } from "./priceApi.js";
import { ownerKey, partyLabel } from "./CounterpartiesView.jsx";
import CopyBtn from "./CopyBtn.jsx";

// Метод, которым сделано соответствие (alias.source) — подсказка на имени.
const METHOD = {
  search: "поиск",
  suggest: "подсказка",
  stage1: "этап 1",
  stage3: "этап 3",
  import: "импорт",
  manual: "вручную",
  auto: "авто",
};

export default function ClustersView() {
  const PER_PAGE = 20;
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(() => new Set());
  // Все контрагенты (а не только поставщики с прайсами) — участником связки
  // может быть и заказчик без прайса, его номенклатуру добавляем вручную.
  const [parties, setParties] = useState([]);
  // Открытая форма добавления: {cid, label, who, q, opts}.
  const [add, setAdd] = useState(null);

  const load = () => priceFetch("/api/clusters").then((r) => r.json()).then(setItems);

  useEffect(() => {
    load();
    priceFetch("/api/counterparties").then((r) => r.json()).then(setParties);
  }, []);

  const delAlias = (aliasId) =>
    priceFetch(`/api/clusters/alias/${aliasId}`, { method: "DELETE" }).then(load);

  const toggleSel = (id) =>
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });

  const delSelected = () => {
    const ids = [...selected];
    if (!ids.length) return;
    if (!window.confirm(`Удалить выбранные связки (${ids.length})?`)) return;
    Promise.all(
      ids.map((id) => priceFetch(`/api/clusters/${id}`, { method: "DELETE" }))
    ).then(() => {
      setSelected(new Set());
      load();
    });
  };

  // --- добавление имени в связку (оверлей) ---
  const openAdd = (c) => {
    const who = parties[0] ? ownerKey(parties[0]) : "";
    setAdd({ cid: c.id, label: c.label || `#${c.id}`, who, q: "", opts: [] });
    if (who) fetchOpts(who, "");
  };

  // Esc закрывает оверлей добавления.
  useEffect(() => {
    if (!add) return;
    const onKey = (e) => e.key === "Escape" && setAdd(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [add]);

  // Варианты из прайса участника (если он поставщик с прайсом). Для заказчика
  // без прайса вернётся пусто — тогда добавляем введённое имя вручную.
  const fetchOpts = (who, q) => {
    priceFetch(`/api/suppliers/offers?email=${encodeURIComponent(who)}&q=${encodeURIComponent(q)}`)
      .then((r) => r.json())
      .then((opts) => setAdd((a) => (a ? { ...a, opts } : a)));
  };

  const commitAdd = (name, code) => {
    priceFetch("/api/clusters/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cluster_id: add.cid,
        include: [{ source: add.who, name, code: code ?? null, via: "manual" }],
        method: "manual",
      }),
    }).then(() => {
      setAdd(null);
      load();
    });
  };

  const pickOffer = (o) => commitAdd(o.name, o.code);

  const f = filter.trim().toLowerCase();
  const visible = useMemo(
    () =>
      items.filter(
        (c) =>
          !f ||
          c.label.toLowerCase().includes(f) ||
          c.aliases.some(
            (a) =>
              a.name.toLowerCase().includes(f) ||
              (a.supplier_email || "").toLowerCase().includes(f)
          )
      ),
    [items, f]
  );

  // Пагинация: показываем по PER_PAGE карточек. При смене фильтра — на 1-ю
  // страницу; после удалений номер не должен вылетать за пределы.
  useEffect(() => setPage(1), [f]);
  const totalPages = Math.max(1, Math.ceil(visible.length / PER_PAGE));
  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);
  const pageItems = visible.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  // Группы источников внутри связки: CL первым, затем поставщики/заказчики
  // (по email), затем имена «вручную» без источника. Каждая группа — «ячейка»
  // карточки со своими именами.
  const sourceGroups = (c) => {
    const groups = new Map();
    for (const a of c.aliases) {
      let key, label;
      if (a.kind === "cl") {
        key = "CL";
        label = "CL · наш товар";
      } else if (a.supplier_email) {
        key = a.supplier_email;
        label = a.supplier_email;
      } else {
        key = "__manual";
        label = "Вручную";
      }
      if (!groups.has(key)) groups.set(key, { key, label, aliases: [] });
      groups.get(key).aliases.push(a);
    }
    return [...groups.values()].sort((x, y) => {
      if (x.key === "CL") return -1;
      if (y.key === "CL") return 1;
      if (x.key === "__manual") return 1;
      if (y.key === "__manual") return -1;
      return x.key.localeCompare(y.key);
    });
  };

  const allSel = visible.length > 0 && visible.every((c) => selected.has(c.id));
  const toggleAll = () =>
    setSelected((s) => {
      const n = new Set(s);
      if (allSel) visible.forEach((c) => n.delete(c.id));
      else visible.forEach((c) => n.add(c.id));
      return n;
    });

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
          <button className="btn-danger" onClick={delSelected}>
            Удалить выбранные ({selected.size})
          </button>
        )}
        <span className="muted">Всего связок: {items.length}</span>
      </div>

      <div className="price-pane">
      {visible.length === 0 ? (
        <p className="muted">{f ? "Ничего не найдено" : "Связок пока нет"}</p>
      ) : (
        <>
          <label className="cl-selall">
            <input type="checkbox" checked={allSel} onChange={toggleAll} />
            выбрать все
          </label>
          <div className="cl-cards">
            {pageItems.map((c) => (
              <div
                key={c.id}
                className={"cl-card" + (selected.has(c.id) ? " sel" : "")}
              >
                <div className="cl-card-head">
                  <input
                    type="checkbox"
                    checked={selected.has(c.id)}
                    onChange={() => toggleSel(c.id)}
                  />
                  <span className="cl-card-title">{c.label || `#${c.id}`}</span>
                  <button
                    className="cl-add-btn"
                    onClick={() => openAdd(c)}
                    title="добавить в связку"
                  >
                    +
                  </button>
                </div>
                <div className="cl-card-body">
                  {sourceGroups(c).map((g) => (
                    <div key={g.key} className="cl-group">
                      <div className="cl-group-label">{g.label}</div>
                      {g.aliases.map((a) => (
                        <div
                          key={a.id}
                          className="cl-alias"
                          title={`метод: ${METHOD[a.source] || a.source}`}
                        >
                          <span className="cl-alias-main">
                            <span className="cl-alias-name">{a.name}</span>
                            <CopyBtn text={a.name} />
                          </span>
                          <button
                            className="cl-x"
                            onClick={() => delAlias(a.id)}
                            title="убрать из связки"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {totalPages > 1 && (
            <div className="cl-pager">
              <button
                className="btn-ghost"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ‹ Назад
              </button>
              <span className="muted">
                стр. {page} из {totalPages}
              </span>
              <button
                className="btn-ghost"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Вперёд ›
              </button>
            </div>
          )}
        </>
      )}
      </div>

      {add && (
        <div className="cp-overlay" onClick={() => setAdd(null)}>
          <div className="cp-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cl-modal-head">
              <h3 className="cp-modal-title">Добавить в связку</h3>
              <span className="muted small">{add.label}</span>
              <button className="cl-x" onClick={() => setAdd(null)} title="закрыть">
                ✕
              </button>
            </div>
            <label className="cp-field">
              Участник
              <select
                className="cp-ctrl"
                value={add.who}
                onChange={(e) => {
                  const who = e.target.value;
                  setAdd((a) => ({ ...a, who, opts: [] }));
                  fetchOpts(who, add.q);
                }}
              >
                {parties.map((p) => (
                  <option key={p.id} value={ownerKey(p)}>
                    {partyLabel(p)}
                  </option>
                ))}
              </select>
            </label>
            <label className="cp-field">
              Номенклатура
              <input
                className="cp-ctrl"
                placeholder="поиск по прайсу или имя вручную…"
                autoFocus
                value={add.q}
                onChange={(e) => {
                  const q = e.target.value;
                  setAdd((a) => ({ ...a, q }));
                  fetchOpts(add.who, q);
                }}
              />
            </label>
            <div className="cl-add-opts">
              {/* Добавить введённое имя как есть — для заказчиков без прайса. */}
              {add.q.trim() && (
                <button
                  className="cl-add-opt cl-add-manual"
                  onClick={() => commitAdd(add.q.trim(), null)}
                >
                  + Добавить «{add.q.trim()}»
                </button>
              )}
              {add.opts.map((o, i) => (
                <button key={i} className="cl-add-opt" onClick={() => pickOffer(o)}>
                  {o.name}
                </button>
              ))}
              {add.opts.length === 0 && !add.q.trim() && (
                <span className="muted small">
                  начните вводить имя — из прайса или вручную
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
