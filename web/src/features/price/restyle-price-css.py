#!/usr/bin/env python3
"""Генератор price.css из styles.css прайса (репо nn_vla/nn_search).

Зачем: вьюхи прайса перенесены как есть (структура/классы 1:1), а оформление
переведено на палитру и layout чата. Этот скрипт детерминированно собирает
price.css: (1) скоупит все правила под .price-root, (2) переопределяет переменные
и тёмные хардкоды на токены чата (см. index.css), (3) добавляет «встраивающий»
слой — секция скроллится внутри main (overflow:hidden), контент на всю ширину,
отступы/заголовок как у страниц чата (см. AppShell.module.css, ProductsPage).

Запуск (путь к исходнику можно переопределить аргументом):
    python3 restyle-price-css.py [/path/to/nn_vla/frontend/src/styles.css]
"""
import re
import pathlib
import sys

SRC = pathlib.Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else "/Users/vorobev/Documents/GitHub/nn_vla/frontend/src/styles.css"
)
OUT = pathlib.Path(__file__).with_name("price.css")

src = SRC.read_text()


def drop_block(css: str, selector: str) -> str:
    pat = re.compile(r"(^|\n)\s*" + re.escape(selector) + r"\s*\{[^{}]*\}", re.S)
    return pat.sub("", css, count=1)


body = src
for sel in (":root", "html", "body"):
    body = drop_block(body, sel)

COMMENT = re.compile(r"/\*.*?\*/", re.S)


def split_trivia(prelude: str):
    last = prelude.rfind("*/")
    if last != -1:
        return prelude[: last + 2], prelude[last + 2:]
    return "", prelude


def prefix_selectors(sel: str) -> str:
    parts = [p.strip() for p in sel.split(",")]
    return ",\n".join(".price-root " + p for p in parts if p)


out = []
i, n = 0, len(body)
while i < n:
    j = -1
    for k in range(i, n):
        if body[k] in "{}":
            j = k
            break
    if j == -1:
        out.append(body[i:])
        break
    if body[j] == "}":  # закрытие @media
        out.append(body[i:j + 1])
        i = j + 1
        continue
    prelude = body[i:j]
    trivia, rest = split_trivia(prelude)
    rest_clean = COMMENT.sub("", rest).strip()
    if rest_clean.startswith("@"):  # @media и т.п. — входим в блок как есть
        out.append(trivia)
        out.append("\n" + rest_clean + " {")
        i = j + 1
        continue
    e = body.find("}", j + 1)
    decl = body[j + 1:e + 1]
    out.append(trivia)
    out.append("\n" + prefix_selectors(rest) + " {")
    out.append(decl)
    i = e + 1

scoped = "".join(out)

# Тёмные хардкоды прайса -> светлая палитра чата.
repl = {
    "#07140b": "#ffffff",
    "#14361f": "rgba(22,163,74,0.14)",
    "#3a1717": "rgba(229,52,42,0.12)",
    "#1a2b3a": "rgba(59,130,246,0.12)",
    "#7fb3e0": "#2563eb",
    "#20242d": "rgba(0,0,0,0.05)",
    "#f87171": "#e5342a",
    "#b3261e": "#e5342a",
    "rgba(74, 222, 128, 0.25)": "rgba(59,130,246,0.30)",
    "rgba(0, 0, 0, 0.4)": "rgba(0,0,0,0.16)",
    "rgba(0, 0, 0, 0.55)": "rgba(0,0,0,0.38)",
}
for a, b in repl.items():
    scoped = scoped.replace(a, b)
scoped = scoped.replace(
    "color: #fff;\n  word-break: break-word;",
    "color: var(--text);\n  word-break: break-word;",
)

header = """/* Прайс-секция — рестайл под светлую палитру чата (см. index.css).
   СГЕНЕРИРОВАНО restyle-price-css.py из styles.css прайса. Не редактировать
   руками — правьте генератор/исходник и пересоберите. */
.price-root {
  --bg: #f4f5f7;          /* фон страницы — нейтральный серый (как у чата) */
  --card: #ffffff;
  --card-best: #eef2f7;   /* шапки карточек/выделение — бледно-голубой акцент */
  --text: #1b1c1f;
  --muted: rgba(0, 0, 0, 0.60);
  --accent: #1b1c1f;
  --border: rgba(0, 0, 0, 0.12);

  color: var(--text);
}
"""

# Встраивающий слой: layout как у Заказов/Аудита (см. AppShell, OrdersPage):
# закреплённая шапка + отдельная скролл-область, фильтр липнет сверху.
embed = """
/* --- Встраивание в оболочку чата: layout как у Заказов --- */
/* Фиксированная шапка + ОТДЕЛЬНАЯ скролл-область под контролами. Контент из БД
   живёт в своём блоке (.price-pane) и не заезжает под контролы при скролле. */
.price-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* Закреп: заголовок + вкладки прайса. */
.price-head {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 24px 32px 14px;
}
.price-root .price-title {
  /* +12px к gap шапки (12) = 24px от заголовка до вкладок — как .header у страниц чата. */
  margin: 0 0 12px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
}
/* Область активной вьюхи. */
.price-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* Скролл-область со списком из БД: единственное, что прокручивается. Начинается
   строго под контролами — контент не перекрывает фильтр и не «заезжает» под него. */
.price-pane {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 32px 48px;
}
/* Вьюхи настроек подбора: фиксированные контролы над списком + .price-pane снизу. */
.price-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* Контролы вьюхи — закреплены над скроллом (не sticky внутри него), на всю ширину,
   отделены нижней границей. */
.price-view > .conf-toolbar,
.price-view > .price-fixed {
  flex: 0 0 auto;
  position: static;
  margin: 0;
  padding: 16px 32px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.price-view > .conf-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.price-view > .price-fixed {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
/* Внутренние контролы price-fixed — без собственных вертикальных отступов. */
.price-view > .price-fixed .syn-form,
.price-view > .price-fixed .filter {
  margin: 0;
}
/* Инпуты прайса — белая заливка, как инпуты чата. */
.price-root input.cp-ctrl,
.price-root select.cp-ctrl,
.price-root .cell-input {
  background: var(--card);
}
@media (max-width: 700px) {
  .price-head {
    padding: 16px 16px 12px;
  }
  .price-pane {
    padding: 12px 16px 40px;
  }
  .price-view > .conf-toolbar,
  .price-view > .price-fixed {
    padding: 12px 16px;
  }
}
"""

OUT.write_text(header + "\n" + scoped.strip() + "\n" + embed)
print("wrote", OUT, "—", OUT.stat().st_size, "bytes")
