import { useEffect, useState } from "react";
import { priceFetch } from "./priceApi.js";

export const ROLE_RU = {
  customer: "Заказчик",
  supplier: "Поставщик",
  both: "Зак+Пост",
};

export function cpLabel(cp) {
  if (!cp) return "";
  const base = cp.title || cp.name || cp.email || `#${cp.id}`;
  return `${base} · ${ROLE_RU[cp.role] || cp.role}`;
}

// Ключ колонки контрагента в связке — как его пишет бэкенд (owner_key):
// email, иначе имя, иначе cp#id. По нему попадаем в нужный столбец.
export const ownerKey = (cp) => cp.email || cp.name || `cp#${cp.id}`;

// Подпись участника, где почта видна ВСЕГДА (когда есть): столбцы в таблице
// связок именованы по почте, иначе имя в селекте со столбцом не сопоставить.
export function partyLabel(cp) {
  if (!cp) return "";
  const parts = [cp.title || cp.name, cp.email].filter(Boolean);
  if (!parts.length) parts.push(`#${cp.id}`);
  return `${parts.join(" · ")} · ${ROLE_RU[cp.role] || cp.role}`;
}

const EMPTY = { name: "", title: "", email: "", role: "supplier" };

const ROLE_OPTIONS = [
  ["supplier", "Поставщик"],
  ["customer", "Заказчик"],
  ["both", "Зак+Пост"],
];

export default function CounterpartiesView() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [adding, setAdding] = useState(false);
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY);

  const load = () =>
    priceFetch("/api/counterparties").then((r) => r.json()).then(setItems);

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!adding) return;
    const onKey = (e) => e.key === "Escape" && setAdding(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [adding]);

  const openAdd = () => {
    setForm(EMPTY);
    setAdding(true);
  };

  const add = (e) => {
    e.preventDefault();
    if (!form.name && !form.title && !form.email) return;
    priceFetch("/api/counterparties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    }).then(() => {
      setForm(EMPTY);
      setAdding(false);
      load();
    });
  };

  const startEdit = (c) => {
    setEditId(c.id);
    setEditForm({ name: c.name, title: c.title, email: c.email, role: c.role });
  };

  const saveEdit = (id) => {
    priceFetch(`/api/counterparties/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(editForm),
    }).then(() => {
      setEditId(null);
      load();
    });
  };

  const remove = (c) => {
    if (!window.confirm(`Удалить контрагента «${c.title || c.name || c.email}»?`))
      return;
    priceFetch(`/api/counterparties/${c.id}`, { method: "DELETE" }).then(load);
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const setE = (k) => (e) => setEditForm({ ...editForm, [k]: e.target.value });

  // Enter не отправляет форму, а переводит фокус на следующее поле.
  const onFieldEnter = (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    const fields = [...e.currentTarget.form.querySelectorAll("input, select")];
    const next = fields[fields.indexOf(e.currentTarget) + 1];
    if (next) next.focus();
  };

  return (
    <>
      <p className="muted">
        Поставщики и заказчики. При обработке документа выбираешь, от кого он —
        и все сопоставления привязываются к этому контрагенту.
      </p>

      <div className="cp-toolbar">
        <button className="cp-ctrl cp-btn cp-btn-primary" onClick={openAdd}>
          + контрагент
        </button>
      </div>

      {adding && (
        <div className="cp-overlay" onClick={() => setAdding(false)}>
          <form
            className="cp-modal"
            onSubmit={add}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="cp-modal-title">Новый контрагент</h3>
            <label className="cp-field">
              <span>Имя</span>
              <input className="cp-ctrl" autoFocus value={form.name} onChange={set("name")} onKeyDown={onFieldEnter} />
            </label>
            <label className="cp-field">
              <span>Наименование</span>
              <input className="cp-ctrl" value={form.title} onChange={set("title")} onKeyDown={onFieldEnter} />
            </label>
            <label className="cp-field">
              <span>Почта</span>
              <input className="cp-ctrl" value={form.email} onChange={set("email")} onKeyDown={onFieldEnter} />
            </label>
            <label className="cp-field">
              <span>Тип</span>
              <select className="cp-ctrl" value={form.role} onChange={set("role")}>
                {ROLE_OPTIONS.map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </label>
            <div className="cp-modal-actions">
              <button
                className="cp-ctrl cp-btn"
                type="button"
                onClick={() => setAdding(false)}
              >
                Отмена
              </button>
              <button className="cp-ctrl cp-btn cp-btn-primary" type="submit">
                Добавить
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="table-scroll">
      <table className="cp-table">
        <colgroup>
          <col className="cp-c-name" />
          <col className="cp-c-title" />
          <col className="cp-c-email" />
          <col className="cp-c-role" />
          <col className="cp-c-act" />
        </colgroup>
        <thead>
          <tr>
            <th>Имя</th>
            <th>Наименование</th>
            <th>Почта</th>
            <th>Тип</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) =>
            editId === c.id ? (
              <tr key={c.id} className="cp-row cp-row-edit">
                <td className="cp-d-name">
                  <input className="cp-ctrl" placeholder="Имя" value={editForm.name} onChange={setE("name")} />
                </td>
                <td className="cp-d-title">
                  <input className="cp-ctrl" placeholder="Наименование" value={editForm.title} onChange={setE("title")} />
                </td>
                <td className="cp-d-email">
                  <input className="cp-ctrl" placeholder="Почта" value={editForm.email} onChange={setE("email")} />
                </td>
                <td className="cp-d-role">
                  <select className="cp-ctrl" value={editForm.role} onChange={setE("role")}>
                    {ROLE_OPTIONS.map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </td>
                <td className="cp-d-act">
                  <div className="cp-actions">
                    <button className="cp-ctrl cp-btn" onClick={() => saveEdit(c.id)}>
                      Сохранить
                    </button>
                    <button className="cp-ctrl cp-btn" onClick={() => setEditId(null)}>
                      Отмена
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={c.id} className="cp-row">
                <td className="cp-d-name">{c.name || "—"}</td>
                <td className="cp-d-title">{c.title || "—"}</td>
                <td className="cp-d-email">{c.email || "—"}</td>
                <td className="cp-d-role">{ROLE_RU[c.role] || c.role}</td>
                <td className="cp-d-act">
                  <div className="cp-actions">
                    <button className="cp-ctrl cp-btn" onClick={() => startEdit(c)}>
                      Изменить
                    </button>
                    <button className="cp-ctrl cp-btn cp-btn-del" onClick={() => remove(c)}>
                      ✕
                    </button>
                  </div>
                </td>
              </tr>
            )
          )}
        </tbody>
      </table>
      </div>
      <div className="muted">Всего: {items.length}</div>
    </>
  );
}
