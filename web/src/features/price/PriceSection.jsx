import { useState } from "react";
import { ButtonGroup } from "../../ui/ButtonGroup";
import SearchView from "./SearchView.jsx";
import SynonymsView from "./SynonymsView.jsx";
import MatchView from "./MatchView.jsx";
import PriceView from "./PriceView.jsx";
import CounterpartiesView from "./CounterpartiesView.jsx";
import ClustersView from "./ClustersView.jsx";
import RejectionsView from "./RejectionsView.jsx";
import "./price.css";

// Прайс-секция внутри оболочки чата. Внутренние вкладки прайса сохранены, но
// оформлены компонентом чата (ButtonGroup, как в Аудите). Layout — как у страниц
// чата (Заказы/Аудит): шапка (заголовок + вкладки) закреплена, скроллится только
// контент (.price-scroll). Вход/логаут даёт сайдбар чата (единый вход).

// Верхнее меню. «tuning» — псевдо-пункт «Настройки подбора»: активен, пока выбрана
// любая из под-вкладок.
const TOP_TABS = [
  ["price", "Price update"],
  ["search", "Поиск"],
  ["match", "Сопоставление"],
  ["tuning", "Настройки подбора"],
  ["counterparties", "Контрагенты"],
];

// Под-вкладки «Настроек подбора». «Пользователи» убраны — при едином входе с
// чатом учётки прайса не нужны.
const SUB_TABS = [
  ["clusters", "Связки"],
  ["rejections", "Точно нет"],
  ["synonyms", "Словарь"],
];

const toOptions = (tabs) => tabs.map(([value, label]) => ({ value, label }));

export default function PriceSection() {
  const [view, setView] = useState("search");
  const inTuning = SUB_TABS.some(([key]) => key === view);
  const topValue = inTuning ? "tuning" : view;

  return (
    <div className="price-root">
      <div className="price-head">
        <h1 className="price-title">Прайс</h1>
        <ButtonGroup
          size="sm"
          value={topValue}
          onChange={(v) => v && setView(v === "tuning" ? SUB_TABS[0][0] : v)}
          options={toOptions(TOP_TABS)}
        />
        {inTuning && (
          <ButtonGroup
            size="sm"
            value={view}
            onChange={(v) => v && setView(v)}
            options={toOptions(SUB_TABS)}
          />
        )}
      </div>

      <div className="price-body">
        {/* Вьюхи без выделенных контролов — целиком в скролл-области. */}
        {view === "price" && (
          <div className="price-pane">
            <PriceView />
          </div>
        )}
        {view === "search" && (
          <div className="price-pane">
            <SearchView />
          </div>
        )}
        {view === "match" && (
          <div className="price-pane">
            <MatchView />
          </div>
        )}
        {view === "counterparties" && (
          <div className="price-pane">
            <CounterpartiesView />
          </div>
        )}
        {/* Настройки подбора — сами держат фикс-контролы + свою скролл-область. */}
        {view === "clusters" && <ClustersView />}
        {view === "rejections" && <RejectionsView />}
        {view === "synonyms" && <SynonymsView />}
      </div>
    </div>
  );
}
