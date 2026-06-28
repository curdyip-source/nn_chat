import { useEffect, useRef, useState } from "react";
import { priceFetch } from "./priceApi.js";
import { ROLE_RU } from "./CounterpartiesView.jsx";
import CopyBtn from "./CopyBtn.jsx";

// Подробная подпись для селекта: имя · наименование · почта · тип.
const cpOption = (p) =>
  [p.name, p.title, p.email].filter(Boolean).join(" · ") +
  ` · ${ROLE_RU[p.role] || p.role}`;

const STATUS_RU = {
  pending: "не решено",
  confirmed: "из справочника",
  auto: "авто",
  manual: "вручную",
  rejected: "нет подходящего",
  no_match: "не найдено",
};
const FILTERS = [
  ["pending", "На проверку"],
  ["no_match", "Не найдено"],
  ["confirmed", "Из справочника"],
  ["manual", "Вручную"],
  ["rejected", "Отклонено"],
  ["", "Все"],
];
const fmtPrice = (p) =>
  p === null || p === undefined ? "—" : Number(p).toLocaleString("ru-RU");

// Дата создания задания: «04.06.2026, 14:30».
const fmtDate = (s) => {
  if (!s) return "";
  const d = new Date(s);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
};

// Задание выполнено, когда все позиции решены.
const isDone = (j) => j.total > 0 && j.decided_count >= j.total;

export default function MatchView() {
  const [stage, setStage] = useState("jobs"); // jobs | review
  const [jobs, setJobs] = useState([]);
  const [job, setJob] = useState(null);
  const [parties, setParties] = useState([]);
  const [filter, setFilter] = useState("pending");
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [pushing, setPushing] = useState(false);
  const [pushMsg, setPushMsg] = useState(null);
  const [activeSup, setActiveSup] = useState({}); // itemId -> email активного таба
  const [suppliers, setSuppliers] = useState([]); // поставщики с прайсами (опции фильтра)
  const [selSup, setSelSup] = useState(() => new Set()); // фильтр: показанные поставщики
  const [selJobs, setSelJobs] = useState(() => new Set()); // выбранные задания для удаления
  const [supOpen, setSupOpen] = useState(false); // открыт ли дропдаун фильтра
  const [prog, setProg] = useState(null); // прогресс этапа 3 с учётом фильтра
  const [authorized, setAuthorized] = useState(null); // подключён ли Google
  const poll = useRef(null);
  const supRef = useRef(null); // контейнер дропдауна — для закрытия по клику вне

  const loadJobs = () =>
    priceFetch("/api/match/jobs").then((r) => r.json()).then(setJobs);

  const loadParties = () =>
    priceFetch("/api/counterparties").then((r) => r.json()).then(setParties);

  // Статус Google-авторизации: пока нет — кнопки выгрузки в/из Gsheet серые.
  useEffect(() => {
    const load = () =>
      priceFetch("/api/price/status")
        .then((r) => r.json())
        .then((d) => setAuthorized(!!d.authorized))
        .catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    loadJobs();
    loadParties();
    priceFetch("/api/match/suppliers")
      .then((r) => r.json())
      .then((list) => {
        // CL (наш прайс) — такая же колонка-источник, как поставщик, первой в фильтре.
        const cols = [{ email: "CL", date: "наш прайс", offers: "" }, ...list];
        setSuppliers(cols);
        setSelSup(new Set(cols.map((s) => s.email))); // по умолчанию — все
      })
      .catch(() => {
        setSuppliers([{ email: "CL", date: "наш прайс", offers: "" }]);
        setSelSup(new Set(["CL"]));
      });
    return () => clearInterval(poll.current);
  }, []);

  const toggleSup = (email) =>
    setSelSup((s) => {
      // Отмечены все и кликнули по одному — изолируем его (снимаем остальные).
      // Дальше — обычный toggle; вернуть всё можно кнопкой «Все».
      if (s.size === suppliers.length) return new Set([email]);
      const next = new Set(s);
      next.has(email) ? next.delete(email) : next.add(email);
      return next;
    });

  // Прогресс этапа 3 с учётом фильтра поставщиков (считает бэкенд по всем позициям).
  useEffect(() => {
    if (!job || job.status !== "ready") {
      setProg(null);
      return;
    }
    const params = new URLSearchParams();
    [...selSup].forEach((e) => params.append("emails", e));
    priceFetch(`/api/match/jobs/${job.id}/progress?${params}`)
      .then((r) => r.json())
      .then(setProg)
      .catch(() => {});
  }, [job, selSup, items]);

  // Закрыть дропдаун фильтра по клику/тапу вне него.
  useEffect(() => {
    if (!supOpen) return;
    const onDown = (e) => {
      if (supRef.current && !supRef.current.contains(e.target)) setSupOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("touchstart", onDown);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("touchstart", onDown);
    };
  }, [supOpen]);

  // Полная подпись контрагента как в селекте: имя · наименование · почта · тип.
  const partyOption = (id) => {
    const cp = parties.find((p) => p.id === id);
    return cp ? cpOption(cp) : id ? `#${id}` : "";
  };

  // Короткая подпись заказчика для заголовка задания: «Имя · почта».
  const custLabel = (id) => {
    const cp = parties.find((p) => p.id === id);
    if (!cp) return id ? `#${id}` : "";
    return [cp.name || cp.title, cp.email].filter(Boolean).join(" · ");
  };

  const fromGsheet = () => {
    setBusy(true);
    setError(null);
    priceFetch(`/api/match/from-gsheet`, { method: "POST" })
      .then(async (r) => {
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
        return j;
      })
      .then((list) => {
        // Бэкенд делит лист на задания по заказчику → возвращает список.
        const arr = Array.isArray(list) ? list : [list];
        loadJobs();
        if (arr.length === 1) openReview(arr[0]);
        // Несколько заказчиков — остаёмся на списке заданий (он обновился).
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  // --- review ---
  const openReview = (j) => {
    setJob(j);
    setStage("review");
    clearInterval(poll.current);
    if (j.status === "processing") {
      poll.current = setInterval(() => refreshJob(j.id), 1000);
    } else {
      loadItems(j.id);
    }
  };

  const refreshJob = (id) =>
    priceFetch(`/api/match/jobs/${id}`)
      .then((r) => r.json())
      .then((j) => {
        setJob(j);
        if (j.status !== "processing") {
          clearInterval(poll.current);
          loadItems(id);
          loadJobs();
        }
      });

  // Грузим все позиции задания; вкладки/фильтр источников считаем на клиенте —
  // «решено» зависит от выбранных источников, серверный статус тут не годится.
  const loadItems = (id) =>
    priceFetch(`/api/match/jobs/${id}/items?limit=200`)
      .then((r) => r.json())
      .then(setItems);

  const changeFilter = (st) => setFilter(st);

  const decide = (item, body) =>
    priceFetch(`/api/match/items/${item.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((r) => r.json())
      .then((updated) => {
        setItems((prev) => prev.map((it) => (it.id === updated.id ? updated : it)));
        refreshJob(job.id);
      });

  const pushGsheet = () => {
    setPushing(true);
    setPushMsg(null);
    priceFetch(`/api/match/jobs/${job.id}/push-gsheet`, { method: "POST" })
      .then(async (r) => {
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
        return j;
      })
      .then((j) =>
        setPushMsg({
          ok: true,
          text:
            `Залито строк: ${j.rows}` +
            (j.skipped ? ` · не найдено в таблице: ${j.skipped} (пропущены)` : ""),
          url: j.url,
        })
      )
      .catch((e) => setPushMsg({ ok: false, text: e.message }))
      .finally(() => setPushing(false));
  };

  const tagClass = (status) => {
    if (status === "auto" || status === "manual" || status === "confirmed")
      return "tag ok";
    if (status === "rejected" || status === "no_match") return "tag bad";
    return "tag";
  };

  // --- группировка кандидатов по источнику (CL + поставщики) ---
  const groupBySupplier = (cands) => {
    const m = new Map();
    for (const c of cands) {
      const k = c.supplier_email || "?";
      if (!m.has(k)) m.set(k, { email: k, date: c.price_date, list: [] });
      m.get(k).list.push(c);
    }
    // CL — первой группой.
    return [...m.values()].sort((a, b) =>
      a.email === "CL" ? -1 : b.email === "CL" ? 1 : a.email.localeCompare(b.email)
    );
  };
  // Лучшее предложение поставщика (мин. цена) — CL в picks не лежит, не учитывается.
  const bestPick = (picks) => {
    let best = null;
    for (const p of Object.values(picks || {})) {
      if (!p || p.reject || p.price == null) continue;
      if (!best || Number(p.price) < Number(best.price)) best = p;
    }
    return best;
  };
  // Состояние источника по позиции: auto|manual|reject|empty|pending.
  // empty = кандидатов нет (нечего решать) → источник считается решённым.
  const sourceState = (it, email) => {
    const p = it.picks?.[email];
    if (p) {
      if (p.reject) return "reject";
      if (p.product_id != null || p.offer_id != null)
        return p.via === "auto" ? "auto" : "manual";
    }
    const has = (it.candidates || []).some((c) => c.supplier_email === email);
    return has ? "pending" : "empty";
  };
  const DECIDED_SRC = new Set(["auto", "manual", "reject", "empty"]);
  const supDecided = (it, email) => DECIDED_SRC.has(sourceState(it, email));
  // Относится ли источник к позиции: CL — к каждой строке; поставщик — только
  // если у него есть кандидат или уже сделан выбор.
  const supApplies = (it, email) =>
    email === "CL" ||
    (it.candidates || []).some((c) => c.supplier_email === email) ||
    it.picks?.[email] != null;
  // Источники, которые надо решить по позиции с учётом фильтра.
  const reqSources = (it) => [...selSup].filter((e) => supApplies(it, e));
  // Состояние позиции относительно фильтра источников (опорный пункт).
  const itemState = (it) => {
    const req = reqSources(it);
    if (!req.length) return "out"; // не относится к выбранным источникам
    const sts = req.map((e) => sourceState(it, e));
    if (sts.some((s) => s === "pending")) return "pending";
    if (sts.every((s) => s === "empty")) return "no_match";
    if (!sts.some((s) => s === "auto" || s === "manual")) return "rejected";
    if (sts.every((s) => s === "auto" || s === "empty")) return "confirmed";
    return "manual";
  };
  // Видимость позиции во вкладке с учётом фильтра источников.
  const matchesTab = (it) => {
    const st = itemState(it);
    if (st === "out") return false;
    if (filter === "") return true;
    return st === filter;
  };

  // --- выбор и удаление заданий (история одноразовая) ---
  const toggleJob = (id) =>
    setSelJobs((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  const allJobsSelected = jobs.length > 0 && jobs.every((j) => selJobs.has(j.id));
  const toggleAllJobs = () =>
    setSelJobs((s) => {
      const next = new Set(s);
      if (allJobsSelected) jobs.forEach((j) => next.delete(j.id));
      else jobs.forEach((j) => next.add(j.id));
      return next;
    });
  const bulkDeleteJobs = () => {
    const ids = [...selJobs];
    if (!ids.length) return;
    if (!window.confirm(`Удалить отмеченные задания (${ids.length})? Это только история — на справочник и сопоставления не влияет.`))
      return;
    priceFetch("/api/match/jobs/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    }).then(() => {
      setSelJobs(new Set());
      loadJobs();
    });
  };

  // ---------- render ----------
  if (stage === "jobs") {
    return (
      <>
        <div className="match-intro">
          <p className="muted match-intro-text">
            В листе «Этап 1. CL parsing» заполни колонку «Заказчик» (email) и
            «Оптовый заказ (Исходный). Наименование позиций».
          </p>
          <button
            className="btn-primary match-intro-btn"
            disabled={busy || !authorized}
            onClick={fromGsheet}
            title={
              authorized
                ? "Лист «Этап 1. CL parsing»: заказчик + исходник → CL и прайсы поставщиков"
                : "Подключите Google на вкладке Price update"
            }
          >
            {busy ? "Загружаю…" : "Загрузить из Gsheet"}
          </button>
        </div>
        {error && <div className="status error">Ошибка: {error}</div>}
        {jobs.length > 0 && (
          <>
            <div className="jobs-head">
              <h3 className="muted">Прежние задания</h3>
              <label className="jobs-selall">
                <input
                  type="checkbox"
                  checked={allJobsSelected}
                  onChange={toggleAllJobs}
                />
                выбрать все
              </label>
              {selJobs.size > 0 && (
                <button className="btn-danger" onClick={bulkDeleteJobs}>
                  Удалить выбранные ({selJobs.size})
                </button>
              )}
            </div>
            <ul className="results">
              {jobs.map((j) => (
                <li
                  key={j.id}
                  className={`row job${selJobs.has(j.id) ? " sel" : ""}`}
                  onClick={() => openReview(j)}
                >
                  <input
                    type="checkbox"
                    className="job-chk"
                    checked={selJobs.has(j.id)}
                    onClick={(e) => e.stopPropagation()}
                    onChange={() => toggleJob(j.id)}
                    title="Отметить для удаления"
                  />
                  <div className="name">
                    {j.counterparty_id ? <b>{custLabel(j.counterparty_id)} · </b> : null}
                    {j.filename}
                  </div>
                  <div className="meta">
                    {fmtDate(j.created_at)} · статус: {j.status} · позиций:{" "}
                    {j.total} · из справочника: {j.auto_count} · решено:{" "}
                    {j.decided_count}
                  </div>
                  {isDone(j) && (
                    <span className="job-done" title="Выполнено">
                      ✓
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </>
    );
  }

  // stage === review
  return (
    <>
      <div className="job-head">
        <button className="btn-ghost" onClick={() => { setStage("jobs"); loadJobs(); }}>
          ← Задания
        </button>
        <div className="muted">
          {job.counterparty_id ? <b>{custLabel(job.counterparty_id)} · </b> : null}
          {job.filename} · {job.status}
          {job.status === "processing" && " — обрабатывается…"}
        </div>
        {job.status === "ready" && (
          <>
            <a className="btn-primary" href={`/api/match/jobs/${job.id}/export`}>
              Скачать Excel
            </a>
            <button
              className="btn-primary"
              disabled={pushing || !authorized}
              onClick={pushGsheet}
              title={authorized ? "" : "Подключите Google на вкладке Price update"}
            >
              {pushing ? "Заливаю…" : "Залить в Gsheet"}
            </button>
          </>
        )}
      </div>

      {pushMsg && (
        <div className={`status ${pushMsg.ok ? "" : "error"}`}>
          {pushMsg.text}
          {pushMsg.url && (
            <>
              {" · "}
              <a href={pushMsg.url} target="_blank" rel="noreferrer">
                открыть таблицу
              </a>
            </>
          )}
        </div>
      )}

      {job.status === "error" && (
        <div className="status error">
          Не удалось обработать файл. {job.filename}
        </div>
      )}
      {job.status === "processing" && (
        <div className="status">Обрабатывается… подбираю кандидатов по строкам.</div>
      )}

      {job.total > 0 && (() => {
        // С фильтром по источникам прогресс считает бэкенд (prog) только по
        // выбранным поставщикам; без него — общий счётчик задания.
        const total = prog ? prog.total : job.total;
        const decided = prog ? prog.decided : job.decided_count;
        const auto = prog ? prog.auto : job.auto_count;
        const pct = total ? Math.round((decided / total) * 100) : 0;
        const filtered = prog && selSup.size !== suppliers.length;
        return (
          <div className="progress">
            <div className="bar" style={{ width: `${pct}%` }} />
            <span>
              решено {decided} из {total} · из связок {auto}
              {filtered && " · по фильтру источников"}
            </span>
          </div>
        );
      })()}

      <div className="tabs filters filters-wide">
        {FILTERS.map(([st, label]) => (
          <button
            key={st}
            className={filter === st ? "tab active" : "tab"}
            onClick={() => changeFilter(st)}
          >
            {label}
          </button>
        ))}
      </div>

      {suppliers.length > 0 && (
        <div className="sup-filter">
          <span className="muted">Фильтр по источникам:</span>
          <div className="dropdown" ref={supRef}>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setSupOpen((o) => !o)}
            >
              показано {selSup.size}/{suppliers.length} ▾
            </button>
            {supOpen && (
              <div className="dropdown-panel">
                <div className="dd-actions dd-actions-top">
                  <span className="dd-title muted small">Фильтр по источникам</span>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setSelSup(new Set(suppliers.map((s) => s.email)))}
                  >
                    Все
                  </button>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setSelSup(new Set())}
                  >
                    Снять
                  </button>
                </div>
                {suppliers.map((s) => (
                  <label key={s.email} className="dd-item">
                    <input
                      type="checkbox"
                      checked={selSup.has(s.email)}
                      onChange={() => toggleSup(s.email)}
                    />
                    <span>
                      {s.email}
                      <span className="muted"> · {s.date} · {s.offers}</span>
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <ul className="results">
        {items.filter(matchesTab).map((it) => {
          const st = itemState(it);
          let groups = groupBySupplier(it.candidates).filter((gr) => selSup.has(gr.email));
          // CL — источник всегда (даже без кандидатов: только «нет подходящего»).
          if (selSup.has("CL") && !groups.some((gr) => gr.email === "CL")) {
            groups = [{ email: "CL", date: "наш прайс", list: [] }, ...groups];
          }
          const bp = bestPick(it.picks);
          const active =
            activeSup[it.id] ||
            (groups.find((gr) => !supDecided(it, gr.email)) || groups[0])?.email;
          const g = groups.find((x) => x.email === active) || groups[0];
          const isCL = g && g.email === "CL";
          return (
            <li key={it.id} className="match-card">
              <div className="item-title">
                <span className={tagClass(st)}>{STATUS_RU[st]}</span>
                <span className="item-name">{it.source_text}</span>
                <CopyBtn text={it.source_text} />
              </div>
              {bp && (
                <div className="sup-best">
                  ▶ лучшее предложение: <b>{bp.supplier_email}</b> · {bp.name} ·{" "}
                  {fmtPrice(bp.price)}
                </div>
              )}
              {it.candidates.length === 0 && (
                <span className="muted">кандидатов не найдено</span>
              )}
              {groups.length > 0 && g && (
                <>
                  <div className="sup-tabs">
                    {groups.map((gr) => (
                      <button
                        key={gr.email}
                        className={
                          "sup-tab" +
                          (gr.email === active ? " active" : "") +
                          (supDecided(it, gr.email) ? " done" : "")
                        }
                        onClick={() => setActiveSup((s) => ({ ...s, [it.id]: gr.email }))}
                      >
                        {supDecided(it, gr.email) ? "✓ " : ""}
                        {gr.email === "CL" ? "CL (наш товар)" : gr.email.split("@")[0]}
                      </button>
                    ))}
                  </div>
                  <div className="sup-head">
                    {isCL ? "CL · наш прайс" : `${g.email} · ${g.date}`}
                  </div>
                  <div className="cands">
                    {g.list.map((c) => {
                      const checked = isCL
                        ? it.picks?.CL?.product_id === c.product_id
                        : it.picks?.[g.email]?.offer_id === c.offer_id;
                      return (
                        <label
                          key={c.offer_id ?? c.product_id}
                          className={checked ? "cand chosen" : "cand"}
                        >
                          <input
                            type="radio"
                            name={`it${it.id}_${g.email}`}
                            checked={checked}
                            onChange={() =>
                              decide(
                                it,
                                isCL
                                  ? { chosen_product_id: c.product_id }
                                  : { supplier_email: g.email, chosen_offer_id: c.offer_id }
                              )
                            }
                          />
                          <div className="cand-main">
                            <div className="cname">
                              {c.name}
                              <CopyBtn text={c.name} />
                            </div>
                            <div className="cmeta">
                              {c.code && <span className="code">{c.code}</span>}
                              <span className="muted">
                                слов: {c.word_score}
                                {c.type_match !== 0 && (c.type_match > 0 ? " · тип✓" : " · тип✗")}
                                {c.volume_match !== 0 &&
                                  (c.volume_match > 0 ? " · объём✓" : " · объём✗")}
                                {" · близость "}
                                {Math.round(Number(c.similarity) * 100)}%
                              </span>
                            </div>
                          </div>
                          <div className="cprice">{fmtPrice(c.price)}</div>
                        </label>
                      );
                    })}
                    <label
                      className={
                        (isCL ? !!it.picks?.CL?.reject : !!it.picks?.[g.email]?.reject)
                          ? "cand chosen"
                          : "cand"
                      }
                    >
                      <input
                        type="radio"
                        name={`it${it.id}_${g.email}`}
                        checked={
                          isCL ? !!it.picks?.CL?.reject : !!it.picks?.[g.email]?.reject
                        }
                        onChange={() =>
                          decide(it, isCL ? { reject: true } : { supplier_email: g.email, reject: true })
                        }
                      />
                      <div className="cand-main">
                        <div className="cname muted">нет подходящего</div>
                      </div>
                    </label>
                  </div>
                </>
              )}
            </li>
          );
        })}
      </ul>
      {items.filter(matchesTab).length === 0 && (
        <p className="muted">Нет позиций в этом фильтре.</p>
      )}
    </>
  );
}
