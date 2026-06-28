import { useEffect, useRef, useState } from "react";
import { priceFetch } from "./priceApi.js";
import CopyBtn from "./CopyBtn.jsx";
import { ownerKey, partyLabel } from "./CounterpartiesView.jsx";

function useDebounced(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

const fmtPrice = (p) =>
  p === null || p === undefined ? "—" : Number(p).toLocaleString("ru-RU");

// Подпись источника строки.
const srcLabel = (r) => (r.source === "CL" ? "CL (мой прайс)" : r.source);

// Ключ строки в корзине подбора — источник + имя (стабилен между запросами).
const itemKey = (r) => `${r.source}|${r.name}`;

export default function SearchView() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Корзина подбора связки: копится МЕЖДУ запросами, пока не нажмёшь «Сохранить».
  const [basket, setBasket] = useState([]); // [{key, source, name, code, via}]
  const [dismissed, setDismissed] = useState(() => new Set()); // снятые вручную подсказки
  const [saving, setSaving] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  // Контрагенты + «чей это запрос»: если запрос — копи-паст из номенклатуры
  // контрагента, при сохранении кладём его в ЕГО столбец связки (а не в общий
  // «запрос»). "" = мой ввод/коррекция поиска (обобщённое имя).
  const [parties, setParties] = useState([]);
  const [queryOwner, setQueryOwner] = useState("");
  // Целевая связка, выбранная вручную кликом по строке «в связке» в выдаче:
  // {id, name}. Имеет приоритет над авто-определением. Сброс при очистке/сохранении.
  const [picked, setPicked] = useState(null);
  // Текст запроса заказчика для столбца «Источник». Снимается в момент добавления
  // ПЕРВОГО товара в корзину (это исходная номенклатура заказчика) и больше не
  // перезаписывается сменой поискового запроса. Редактируется вручную.
  const [queryText, setQueryText] = useState("");
  // Фильтр источников: по каким прайсам искать (CL + поставщики).
  const [sources, setSources] = useState([]); // [{email, date, offers}]
  const [selSrc, setSelSrc] = useState(() => new Set()); // отмеченные источники
  const [srcOpen, setSrcOpen] = useState(false); // открыт ли дропдаун фильтра
  const reqId = useRef(0);
  const srcRef = useRef(null); // контейнер дропдауна — для закрытия по клику вне
  const debounced = useDebounced(query, 250);

  useEffect(() => {
    priceFetch("/api/counterparties").then((r) => r.json()).then(setParties);
    // CL (наш прайс) — такой же источник, как поставщик; первым в фильтре.
    priceFetch("/api/match/suppliers")
      .then((r) => r.json())
      .then((list) => {
        const cols = [{ email: "CL", date: "наш прайс", offers: "" }, ...list];
        setSources(cols);
        setSelSrc(new Set(cols.map((s) => s.email))); // по умолчанию — все
      })
      .catch(() => {
        setSources([{ email: "CL", date: "наш прайс", offers: "" }]);
        setSelSrc(new Set(["CL"]));
      });
  }, []);

  // Закрыть дропдаун фильтра по клику/тапу вне него.
  useEffect(() => {
    if (!srcOpen) return;
    const onDown = (e) => {
      if (srcRef.current && !srcRef.current.contains(e.target)) setSrcOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("touchstart", onDown);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("touchstart", onDown);
    };
  }, [srcOpen]);

  const toggleSrc = (email) =>
    setSelSrc((s) => {
      // Отмечены все и кликнули по одному — изолируем его (снимаем остальные).
      // Дальше — обычный toggle; вернуть всё можно кнопкой «Все».
      if (s.size === sources.length) return new Set([email]);
      const next = new Set(s);
      next.has(email) ? next.delete(email) : next.add(email);
      return next;
    });

  useEffect(() => {
    const q = debounced.trim();
    if (!q) {
      setData(null);
      setError(null);
      return;
    }
    if (!sources.length) return; // источники ещё не загрузились
    if (selSrc.size === 0) {
      setData({ query: q, normalized: "", count: 0, results: [] });
      setError(null);
      return;
    }
    const id = ++reqId.current;
    setLoading(true);
    const params = new URLSearchParams({ q, limit: "50" });
    // Отмечены все — фильтр не шлём (поведение «по всем», идентичное прежнему).
    const allSelected = selSrc.size === sources.length;
    if (!allSelected) [...selSrc].forEach((e) => params.append("emails", e));
    priceFetch(`/api/search/all?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (id === reqId.current) {
          setData(json);
          setError(null);
        }
      })
      .catch((e) => {
        if (id === reqId.current) setError(e.message);
      })
      .finally(() => {
        if (id === reqId.current) setLoading(false);
      });
  }, [debounced, selSrc, sources, refreshTick]);

  const inBasket = (r) => basket.some((it) => it.key === itemKey(r));

  // Целевая связка: выбранная вручную (клик по строке «в связке») имеет приоритет.
  // Иначе авто: если все «сохранённые» строки выдачи указывают на одну — пополняем её.
  const resultClusters = new Set(
    (data?.results || []).filter((r) => r.cluster_id).map((r) => r.cluster_id)
  );
  const autoTarget = resultClusters.size === 1 ? [...resultClusters][0] : null;
  const targetClusterId = picked?.id ?? autoTarget;

  // Сколько РАЗНЫХ колонок заполнит сохранение: источники отмеченных позиций +
  // колонка «Источника запроса» (если выбран). Новая связка имеет смысл только
  // при ≥2 колонках — иначе односторонняя запись без соответствия.
  const filledColumns = new Set(basket.map((it) => it.source));
  if (queryOwner) filledColumns.add(queryOwner);
  const canSave =
    basket.length > 0 && (targetClusterId != null || filledColumns.size >= 2);

  const toggleRow = (r) => {
    const k = itemKey(r);
    if (inBasket(r)) {
      setBasket((b) => b.filter((it) => it.key !== k));
      setDismissed((d) => new Set(d).add(k)); // не возвращать авто-подсказкой
    } else {
      // Первый товар в пустой корзине задаёт запрос заказчика для столбца «Источник».
      if (basket.length === 0) setQueryText((data?.query || query).trim());
      setDismissed((d) => {
        const n = new Set(d);
        n.delete(k);
        return n;
      });
      setBasket((b) => [
        ...b,
        { key: k, source: r.source, name: r.name, code: r.code ?? null, via: "manual" },
      ]);
    }
  };

  const removeFromBasket = (key) => {
    setBasket((b) => b.filter((it) => it.key !== key));
    setDismissed((d) => new Set(d).add(key));
  };

  const clearBasket = () => {
    setBasket([]);
    setDismissed(new Set());
    setQueryText("");
    setPicked(null);
  };

  const saveCluster = () => {
    if (!canSave) return;
    const qtext = queryText.trim();
    const include = basket.map(({ source, name, code, via }) => ({ source, name, code, via }));
    // Запрос пишем в связку ТОЛЬКО как номенклатуру выбранного контрагента
    // («Источник») — в его столбец. Текст берём из снимка queryText (запрос на
    // момент первого добавления), а не из живой строки поиска. Без источника
    // запрос не сохраняем: иначе вышла бы односторонняя связка.
    // При пополнении существующей связки (picked) запрос заказчика не пишем.
    if (!picked && queryOwner && qtext) {
      include.push({ source: queryOwner, name: qtext, code: null, via: "manual" });
    }
    setSaving(true);
    priceFetch("/api/clusters/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "",
        include,
        cluster_id: targetClusterId,
      }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(() => {
        clearBasket();
        setRefreshTick((t) => t + 1); // перечитать выдачу — строки станут SAVED
      })
      .catch((e) => setError(e.message))
      .finally(() => setSaving(false));
  };

  return (
    <>
      <div className="search-wrap" ref={srcRef}>
        <input
          className="search"
          type="text"
          autoFocus
          placeholder="например: Creed Aventus 30"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query && (
          <button
            type="button"
            className="search-clear"
            onClick={() => setQuery("")}
            title="Очистить"
            aria-label="Очистить поиск"
          >
            ✕
          </button>
        )}
        {sources.length > 0 && (
          <button
            type="button"
            className={"search-gear" + (selSrc.size !== sources.length ? " active" : "")}
            onClick={() => setSrcOpen((o) => !o)}
            title="Источники поиска: CL + поставщики"
            aria-label="Фильтр источников"
          >
            ⚙
          </button>
        )}
        {srcOpen && (
          <div className="dropdown-panel search-src-panel">
            <div className="dd-actions dd-actions-top">
              <span className="dd-title muted small">Искать по источникам</span>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setSelSrc(new Set(sources.map((s) => s.email)))}
              >
                Все
              </button>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setSelSrc(new Set())}
              >
                Снять
              </button>
            </div>
            {sources.map((s) => (
              <label key={s.email} className="dd-item">
                <input
                  type="checkbox"
                  checked={selSrc.has(s.email)}
                  onChange={() => toggleSrc(s.email)}
                />
                <span>
                  {s.email}
                  <span className="muted"> · {s.date}{s.offers !== "" ? ` · ${s.offers}` : ""}</span>
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="status search-status">
        {loading && <span>Поиск…</span>}
        {error && <span className="error">Ошибка: {error}</span>}
      </div>

      {/* Корзина подбора связки — копится между запросами. */}
      {basket.length > 0 && (
        <div className="basket">
          <div className="basket-head">
            <strong>
              {picked ? "Пополняем выбранную связку" : "Отметь товары и сохрани в связку"}
            </strong>
            <span className="basket-actions">
              <button className="btn-ghost" onClick={clearBasket} disabled={saving}>
                Очистить
              </button>
              <button
                className="btn-primary"
                onClick={saveCluster}
                disabled={saving || !canSave}
                title={
                  canSave
                    ? ""
                    : "Нужно ≥2 колонок: укажи «Источник» запроса или отметь товар в другой колонке"
                }
              >
                {saving ? "Сохраняю…" : "Сохранить связку"}
              </button>
            </span>
          </div>
          {picked && (
            <div className="basket-target">
              <span className="muted">Целевая связка:</span>
              <span className="basket-target-name">{picked.name}</span>
              <button
                className="basket-x"
                onClick={() => setPicked(null)}
                title="не пополнять, создать как обычно"
              >
                ✕
              </button>
            </div>
          )}
          {/* Атрибуция запроса заказчика нужна только для НОВОЙ связки. При
              пополнении существующей (picked) поля скрываем — добавляем лишь офферы. */}
          {!picked && (
            <>
              {/* Что запишется в столбец источника: запрос на момент первой отметки,
                  можно поправить вручную. Над «Источником», всегда видим. */}
              <label className="query-owner query-owner-first">
                <span className="muted">Запрос:</span>
                <input
                  className="query-text"
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder="номенклатура заказчика"
                />
              </label>
              {/* Чей это запрос: копи-паст из номенклатуры контрагента → его столбец. */}
              <label className="query-owner query-owner-source">
                <span className="muted">Источник:</span>
                <SourceCombo parties={parties} value={queryOwner} onChange={setQueryOwner} />
              </label>
            </>
          )}
          <ul className="basket-list">
            {basket.map((it) => (
              <li key={it.key}>
                <span className="src-tag">{it.source === "CL" ? "CL" : it.source}</span>
                <span className="bname">{it.name}</span>
                {it.via === "auto" && <span className="tag">подсказка</span>}
                <button className="basket-x" onClick={() => removeFromBasket(it.key)} title="убрать из подбора">
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data && data.results.length > 0 && (
        <ul className="results">
          {data.results.map((r, i) => {
            const checked = inBasket(r);
            return (
              <li key={`${r.source}-${r.id}`} className="row-wrap">
                <div className={`${i === 0 ? "row best" : "row"} markable`}>
                  {r.saved ? (
                    <button
                      type="button"
                      className={
                        "mark-saved" +
                        (r.cluster_id && r.cluster_id === picked?.id ? " target" : "")
                      }
                      title={
                        r.cluster_id === picked?.id
                          ? "целевая связка — снять"
                          : "сделать целевой связкой (пополнить её)"
                      }
                      onClick={() =>
                        setPicked((p) =>
                          p?.id === r.cluster_id
                            ? null
                            : { id: r.cluster_id, name: r.name }
                        )
                      }
                    >
                      ✓
                    </button>
                  ) : (
                    <input
                      type="checkbox"
                      className="mark-chk"
                      checked={checked}
                      onChange={() => toggleRow(r)}
                      title="добавить в подбор связки"
                    />
                  )}
                  <div className="name">
                    {r.name}
                    <CopyBtn text={r.name} />
                  </div>
                  <div className="meta">
                    <span className="src-tag">{srcLabel(r)}</span>
                    {r.saved && r.cluster_id === picked?.id && (
                      <span className="tag ok">целевая</span>
                    )}
                    {r.saved && r.cluster_id !== picked?.id && (
                      <span className="tag ok">в связке</span>
                    )}
                    {!r.saved && r.suggested && (
                      <span className="tag" title="похоже совпадает — проверь">подсказка</span>
                    )}
                    {r.price_date && <span className="muted"> · {r.price_date}</span>}
                    <span className="score">
                      {r.volume_match !== 0 && (
                        <span className={r.volume_match > 0 ? "tag ok" : "tag bad"}>
                          объём {r.volume_match > 0 ? "✓" : "✗"}
                        </span>
                      )}
                      {r.type_match !== 0 && (
                        <span className={r.type_match > 0 ? "tag ok" : "tag bad"}>
                          тип {r.type_match > 0 ? "✓" : "✗"}
                        </span>
                      )}
                      <span className="muted">
                        {" · близость "}
                        {Math.round(r.similarity * 100)}%
                      </span>
                    </span>
                  </div>
                  <div className="price">{fmtPrice(r.price)}</div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {data && data.results.length === 0 && !loading && (
        <p className="muted">
          {selSrc.size === 0 ? "Отметьте хотя бы один источник." : "Ничего не найдено."}
        </p>
      )}
    </>
  );
}

// Комбобокс выбора источника: инпут, по клику — список снизу, по вводу — поиск.
function SourceCombo({ parties, value, onChange }) {
  const options = [
    { key: "", label: "— мой ввод / коррекция —" },
    ...parties.map((p) => ({ key: ownerKey(p), label: partyLabel(p) })),
  ];
  const selected = options.find((o) => o.key === value) || options[0];
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const ref = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("touchstart", onDown);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("touchstart", onDown);
    };
  }, [open]);

  const f = filter.trim().toLowerCase();
  const shown = f
    ? options.filter((o) => o.label.toLowerCase().includes(f))
    : options;

  const pick = (o) => {
    onChange(o.key);
    setFilter("");
    setOpen(false);
    inputRef.current?.blur(); // снять фокус с инпута после выбора
  };

  return (
    <div className="combo" ref={ref}>
      <input
        ref={inputRef}
        className={"combo-input" + (!value && !open ? " is-empty" : "")}
        value={open ? filter : selected.label}
        placeholder={open ? selected.label : ""}
        onChange={(e) => {
          setFilter(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          setFilter("");
        }}
      />
      {open && (
        <div className="dropdown-panel combo-panel">
          {shown.length === 0 && (
            <div className="combo-empty muted small">Ничего не найдено</div>
          )}
          {shown.map((o) => (
            <button
              type="button"
              key={o.key || "—"}
              className={"combo-opt" + (o.key === value ? " sel" : "")}
              // onMouseDown (а не onClick): срабатывает до blur инпута, поэтому
              // выбор надёжно регистрируется и закрывает список и на мобиле.
              onMouseDown={(e) => {
                e.preventDefault();
                pick(o);
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
