import { useState } from "react";

// Кнопка копирования текста (наименования) в буфер обмена.
// Гасим клик (preventDefault/stopPropagation), чтобы не задеть родительский
// обработчик: в сопоставлении кандидат обёрнут в <label> с радио, в поиске —
// строка кликабельна (раскрытие вариаций).
export default function CopyBtn({ text }) {
  const [done, setDone] = useState(false);
  const copy = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const flash = () => {
      setDone(true);
      setTimeout(() => setDone(false), 1200);
    };
    const fallback = () => {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
      } catch {
        /* пусто */
      }
      document.body.removeChild(ta);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(flash, () => {
        fallback();
        flash();
      });
    } else {
      fallback();
      flash();
    }
  };
  return (
    <button
      type="button"
      className="copy-btn"
      title="Скопировать наименование"
      onClick={copy}
    >
      {done ? "✓" : "⧉"}
    </button>
  );
}
